#!/usr/bin/env python3
"""
Time & Financial Semantics Enforcer

Enforces the four-tier metric separation:
- Observed → Attributed → Approved → Billed

This module validates that transformations between tiers follow contract rules.
"""

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger("metrics_enforcer")


@dataclass
class MetricValidationResult:
    valid: bool
    errors: List[str]
    warnings: List[str]


class MetricsEnforcer:
    """
    Enforces metric separation rules at each transformation boundary.
    """

    # Minimum threshold for attributed time (minutes)
    MIN_ATTRIBUTED_MINUTES = 5

    # Confidence floor for submission
    CONFIDENCE_FLOOR = 0.5

    def __init__(self, config: Dict):
        self.config = config
        correlation_config = config.get("correlation", {})
        self.min_attributed_minutes = correlation_config.get("min_attributed_minutes", self.MIN_ATTRIBUTED_MINUTES)
        self.confidence_floor = correlation_config.get("confidence_floor", self.CONFIDENCE_FLOOR)
        self.confidence_thresholds = correlation_config.get("confidence_thresholds", {
            "high": 0.80,
            "medium": 0.50,
            "low": 0.00,
        })

    # =========================================================================
    # OBSERVED → ATTRIBUTED Transformation Rules
    # =========================================================================

    def validate_observed_to_attributed(
        self,
        observed_seconds: int,
        afk_seconds: int,
        idle_seconds: int,
        confidence: float,
        confidence_factors: Dict[str, bool],
    ) -> MetricValidationResult:
        """
        Validate Observed → Attributed transformation.

        Rules:
        1. AFK seconds must be subtracted from observed
        2. Idle seconds must be subtracted (configurable threshold)
        3. Attributed minutes = round(active_seconds / 60 * confidence)
        4. Minimum threshold: intervals < 5 min attributed → discarded
        5. Confidence floor: confidence < 0.5 → not submitted, queued locally only
        """
        errors = []
        warnings = []

        # Rule 1: AFK exclusion
        if afk_seconds < 0:
            errors.append("AFK seconds cannot be negative")

        # Rule 2: Idle exclusion
        if idle_seconds < 0:
            errors.append("Idle seconds cannot be negative")

        # Rule 3: Active seconds calculation
        active_seconds = observed_seconds - afk_seconds - idle_seconds
        if active_seconds < 0:
            errors.append(f"Active seconds negative ({active_seconds}): observed={observed_seconds}, afk={afk_seconds}, idle={idle_seconds}")

        # Rule 4: Attributed minutes calculation
        attributed_minutes = round(active_seconds / 60 * confidence) if active_seconds > 0 else 0

        # Rule 5: Minimum threshold
        if attributed_minutes < self.min_attributed_minutes:
            warnings.append(f"Attributed minutes ({attributed_minutes}) below minimum threshold ({self.min_attributed_minutes}) - will be discarded")

        # Rule 6: Confidence floor
        if confidence < self.confidence_floor:
            warnings.append(f"Confidence ({confidence:.2f}) below floor ({self.confidence_floor}) - will be queued locally only, not submitted")

        # Rule 7: Confidence factors validation
        required_factors = ["revit_foreground", "document_match", "view_active", "afk_excluded", "single_revit_process"]
        for factor in required_factors:
            if factor not in confidence_factors:
                warnings.append(f"Missing confidence factor: {factor}")

        # Rule 8: Confidence must match factors (roughly)
        expected_confidence = sum(
            self.config.get("correlation", {}).get("confidence_weights", {}).get(k, 0) * (1.0 if v else 0.0)
            for k, v in confidence_factors.items()
        )
        if abs(confidence - expected_confidence) > 0.1:
            warnings.append(f"Confidence ({confidence:.2f}) doesn't match weighted factors ({expected_confidence:.2f})")

        return MetricValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
        )

    # =========================================================================
    # ATTRIBUTED → APPROVED Transformation Rules
    # =========================================================================

    def validate_attributed_to_approved(
        self,
        draft_entry: Dict,
        approved_entry: Dict,
    ) -> MetricValidationResult:
        """
        Validate Attributed → Approved transformation.

        Rules:
        1. Designer review: Designer sees draft, can edit duration, project, note
        2. Manager approval: Manager approves/rejects; audit trail recorded
        3. No auto-approval: Automated entries NEVER auto-approve
        4. Edit preserves metadata: Edits keep source_metadata for audit
        """
        errors = []
        warnings = []

        # Rule 1: Source must be 'automation' for attributed entries
        if draft_entry.get("source") != "automation":
            errors.append(f"Draft entry source must be 'automation', got '{draft_entry.get('source')}'")

        # Rule 2: Draft must have review_status = 'pending_review'
        if draft_entry.get("review_status") != "pending_review":
            errors.append(f"Draft entry review_status must be 'pending_review', got '{draft_entry.get('review_status')}'")

        # Rule 3: Approved must have review_status = 'approved'
        if approved_entry.get("review_status") != "approved":
            errors.append(f"Approved entry review_status must be 'approved', got '{approved_entry.get('review_status')}'")

        # Rule 4: Approved must have approved_by and approved_utc
        if not approved_entry.get("approved_by"):
            errors.append("Approved entry missing approved_by")
        if not approved_entry.get("approved_utc"):
            errors.append("Approved entry missing approved_utc")

        # Rule 5: Source metadata must be preserved
        draft_meta = draft_entry.get("source_metadata", {})
        approved_meta = approved_entry.get("source_metadata", {})
        for key in ["correlation_confidence", "observed_seconds", "active_seconds", "afk_seconds", "model_identity", "attribution_factors"]:
            if key in draft_meta and key not in approved_meta:
                warnings.append(f"Source metadata '{key}' not preserved in approval")

        # Rule 6: Proof metadata must be preserved
        draft_proof = draft_entry.get("proof_metadata", {})
        approved_proof = approved_entry.get("proof_metadata", {})
        for key in ["correlation_algorithm", "privacy_filter_applied"]:
            if key in draft_proof and key not in approved_proof:
                warnings.append(f"Proof metadata '{key}' not preserved in approval")

        # Rule 7: Duration can be edited but must be reasonable
        draft_duration = draft_entry.get("duration_minutes", 0)
        approved_duration = approved_entry.get("duration_minutes", 0)
        if approved_duration > draft_duration * 2:
            warnings.append(f"Approved duration ({approved_duration}min) more than 2x draft ({draft_duration}min) - review required")
        if approved_duration < draft_duration * 0.5:
            warnings.append(f"Approved duration ({approved_duration}min) less than 50% of draft ({draft_duration}min) - review required")

        return MetricValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
        )

    # =========================================================================
    # APPROVED → BILLED Transformation Rules
    # =========================================================================

    def validate_approved_to_billed(
        self,
        approved_entries: List[Dict],
        invoice_line_item: Dict,
    ) -> MetricValidationResult:
        """
        Validate Approved → Billed transformation.

        Rules:
        1. Explicit invoicing: Billed quantity set at invoice creation
        2. May be less: billed_hours ≤ approved_hours (discounts, scope limits)
        3. Never more: billed_hours > approved_hours → validation error
        4. Traceability: Every billed hour links to approved timesheet entries
        """
        errors = []
        warnings = []

        # Rule 1: Invoice line item must have quantity_hours
        billed_hours = invoice_line_item.get("quantity_hours", 0)
        if billed_hours <= 0:
            errors.append("Invoice line item quantity_hours must be positive")

        # Rule 2: Sum approved hours from linked entries
        linked_entry_ids = invoice_line_item.get("timesheet_entries", [])
        total_approved_minutes = 0
        for entry in approved_entries:
            if entry.get("id") in linked_entry_ids:
                if entry.get("review_status") != "approved":
                    errors.append(f"Linked entry {entry.get('id')} is not approved (status: {entry.get('review_status')})")
                total_approved_minutes += entry.get("duration_minutes", 0)

        total_approved_hours = total_approved_minutes / 60.0

        # Rule 3: Billed cannot exceed approved
        if billed_hours > total_approved_hours + 0.01:  # Small tolerance for rounding
            errors.append(f"Billed hours ({billed_hours:.2f}) exceeds approved hours ({total_approved_hours:.2f})")

        # Rule 4: Warning if significantly less (discount > 20%)
        if total_approved_hours > 0 and billed_hours < total_approved_hours * 0.8:
            warnings.append(f"Billed hours ({billed_hours:.2f}) is less than 80% of approved ({total_approved_hours:.2f}) - large discount/write-off")

        # Rule 5: Traceability - all billed hours must link to entries
        if not linked_entry_ids:
            errors.append("Invoice line item has no linked timesheet entries")

        return MetricValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
        )

    # =========================================================================
    # Realization Metrics Validation
    # =========================================================================

    def validate_realization_metrics(self, metrics: Dict) -> MetricValidationResult:
        """
        Validate realization metrics calculations.

        Rules:
        1. attribution_rate = attributed / observed
        2. approval_rate = approved / attributed
        3. billing_rate = billed / approved
        4. overall_realization = billed / observed
        5. All rates must be 0.0–1.0
        6. Loaded cost rate must be separate from billing rate
        """
        errors = []
        warnings = []

        observed = metrics.get("observed_hours", 0)
        attributed = metrics.get("attributed_hours", 0)
        approved = metrics.get("approved_hours", 0)
        billed = metrics.get("billed_hours", 0)

        # Rate calculations
        if observed > 0:
            expected_attribution = attributed / observed
            actual_attribution = metrics.get("attribution_rate", 0)
            if abs(expected_attribution - actual_attribution) > 0.01:
                errors.append(f"Attribution rate mismatch: expected {expected_attribution:.4f}, got {actual_attribution:.4f}")

        if attributed > 0:
            expected_approval = approved / attributed
            actual_approval = metrics.get("approval_rate", 0)
            if abs(expected_approval - actual_approval) > 0.01:
                errors.append(f"Approval rate mismatch: expected {expected_approval:.4f}, got {actual_approval:.4f}")

        if approved > 0:
            expected_billing = billed / approved
            actual_billing = metrics.get("billing_rate", 0)
            if abs(expected_billing - actual_billing) > 0.01:
                errors.append(f"Billing rate mismatch: expected {expected_billing:.4f}, got {actual_billing:.4f}")

        if observed > 0:
            expected_overall = billed / observed
            actual_overall = metrics.get("overall_realization", 0)
            if abs(expected_overall - actual_overall) > 0.01:
                errors.append(f"Overall realization mismatch: expected {expected_overall:.4f}, got {actual_overall:.4f}")

        # Rate bounds
        for rate_name in ["attribution_rate", "approval_rate", "billing_rate", "overall_realization"]:
            rate = metrics.get(rate_name, 0)
            if rate < 0 or rate > 1:
                errors.append(f"{rate_name} must be in [0, 1], got {rate}")

        # Financial: loaded cost vs charge rate separation
        financial = metrics.get("financial", {})
        standard_charge = financial.get("standard_charge_rate", 0)
        loaded_cost = financial.get("internal_loaded_cost_rate", 0)

        if standard_charge > 0 and loaded_cost > 0:
            if abs(standard_charge - loaded_cost) < 0.01:
                warnings.append("Standard charge rate equals loaded cost rate - verify these are separate models")
            if loaded_cost > standard_charge:
                warnings.append("Loaded cost rate exceeds charge rate - project may be unprofitable")

        return MetricValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
        )

    # =========================================================================
    # Adapter-Level Enforcement
    # =========================================================================

    def validate_adapter_submission(self, event: Dict) -> MetricValidationResult:
        """
        Validate event before it leaves the adapter.

        Rules:
        1. Never send raw 'observed' metrics to Miru
        2. Always include source_metadata with confidence, observed_seconds, attribution_factors
        3. Never submit 'attributed' with confidence < 0.5
        4. Privacy filter must be applied (proof_metadata.privacy_filter_applied = true)
        """
        errors = []
        warnings = []

        event_type = event.get("event_type", "")

        if event_type == "adapter.ingestion.draft":
            payload = event.get("payload", {}).get("timesheet_entry", {})

            # Rule 1: Check no raw observed metrics in submission
            # (This is enforced by schema - only attributed fields in timesheet_entry)

            # Rule 2: Source metadata required
            source_meta = payload.get("source_metadata", {})
            required_meta = ["correlation_confidence", "observed_seconds", "active_seconds", "afk_seconds", "model_identity", "attribution_factors"]
            for field in required_meta:
                if field not in source_meta:
                    errors.append(f"Missing required source_metadata field: {field}")

            # Rule 3: Confidence floor
            confidence = source_meta.get("correlation_confidence", 0)
            if confidence < self.confidence_floor:
                errors.append(f"Confidence ({confidence:.2f}) below floor ({self.confidence_floor}) - cannot submit")

            # Rule 4: Privacy filter
            proof_meta = payload.get("proof_metadata", {})
            if not proof_meta.get("privacy_filter_applied", False):
                errors.append("Privacy filter not applied (proof_metadata.privacy_filter_applied must be true)")

            # Rule 5: Proof metadata completeness
            required_proof = ["window_events", "afk_events", "revit_idling_events", "correlation_algorithm", "privacy_filter_applied"]
            for field in required_proof:
                if field not in proof_meta:
                    warnings.append(f"Missing proof_metadata field: {field}")

        elif event_type == "adapter.correlated.activity":
            payload = event.get("payload", {})

            # Correlated activity should have attribution with confidence
            attribution = payload.get("attribution", {})
            confidence = attribution.get("confidence", 0)
            if confidence < 0:
                errors.append("Confidence cannot be negative")
            if confidence > 1:
                errors.append("Confidence cannot exceed 1.0")

            # Activity breakdown
            activity = payload.get("activity", {})
            observed = activity.get("observed_seconds", 0)
            active = activity.get("active_seconds", 0)
            afk = activity.get("afk_seconds", 0)
            if observed < active + afk:
                warnings.append(f"Observed ({observed}) < active ({active}) + afk ({afk}) - check calculations")

        return MetricValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
        )


# Convenience function for quick validation
def validate_metric_transformation(
    transformation: str,  # "observed_to_attributed", "attributed_to_approved", "approved_to_billed"
    **kwargs
) -> MetricValidationResult:
    """Quick validation helper."""
    enforcer = MetricsEnforcer({})

    if transformation == "observed_to_attributed":
        return enforcer.validate_observed_to_attributed(
            kwargs.get("observed_seconds", 0),
            kwargs.get("afk_seconds", 0),
            kwargs.get("idle_seconds", 0),
            kwargs.get("confidence", 0),
            kwargs.get("confidence_factors", {}),
        )
    elif transformation == "attributed_to_approved":
        return enforcer.validate_attributed_to_approved(
            kwargs.get("draft_entry", {}),
            kwargs.get("approved_entry", {}),
        )
    elif transformation == "approved_to_billed":
        return enforcer.validate_approved_to_billed(
            kwargs.get("approved_entries", []),
            kwargs.get("invoice_line_item", {}),
        )
    else:
        return MetricValidationResult(
            valid=False,
            errors=[f"Unknown transformation: {transformation}"],
            warnings=[],
        )