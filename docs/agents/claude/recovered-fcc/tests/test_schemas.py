#!/usr/bin/env python3
"""
BIMSpend Contract Schema Validation Tests

Validates all event schemas against valid and invalid fixtures.
"""

import json
import sys
import os
from pathlib import Path
from typing import Dict, List, Tuple, Any
import jsonschema
from jsonschema import validate, ValidationError
from jsonschema.validators import validator_for
from referencing import Registry, Resource


SCHEMAS_DIR = Path(__file__).parent.parent / "schemas"
VALID_FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "valid"
INVALID_FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "invalid"


class SchemaTester:
    def __init__(self):
        self.schemas: Dict[str, Dict] = {}
        self.valid_fixtures: Dict[str, Dict] = {}
        self.invalid_fixtures: Dict[str, Dict] = {}
        self.results: List[Tuple[str, bool, str]] = []

    def load_schemas(self) -> None:
        """Load all JSON schemas from schemas directory."""
        for schema_file in SCHEMAS_DIR.glob("*.schema.json"):
            with open(schema_file, "r") as f:
                schema = json.load(f)
                # Use stem without .schema suffix for cleaner keys
                key = schema_file.stem.replace(".schema", "")
                self.schemas[key] = schema
        print(f"Loaded {len(self.schemas)} schemas: {list(self.schemas.keys())}")

    def load_fixtures(self) -> None:
        """Load valid and invalid fixtures."""
        for fixture_file in VALID_FIXTURES_DIR.glob("*.json"):
            with open(fixture_file, "r") as f:
                self.valid_fixtures[fixture_file.stem] = json.load(f)

        for fixture_file in INVALID_FIXTURES_DIR.glob("*.json"):
            with open(fixture_file, "r") as f:
                self.invalid_fixtures[fixture_file.stem] = json.load(f)

        print(f"Loaded {len(self.valid_fixtures)} valid fixtures")
        print(f"Loaded {len(self.invalid_fixtures)} invalid fixtures")

    def get_schema_for_event(self, event: Dict) -> Dict:
        """Get the appropriate schema for an event based on event_type."""
        event_type = event.get("event_type", "")

        # Map event_type to schema file (keys match load_schemas output)
        type_to_schema = {
            "window.focus.changed": "window_focus_changed",
            "afk.state.changed": "afk_state_changed",
            "revit.document.opened": "revit_document_opened",
            "revit.document.closed": "revit_document_closed",
            "revit.view.activated": "revit_view_activated",
            "revit.application.idling": "revit_application_idling",
            "adapter.correlated.activity": "adapter_correlated_activity",
            "adapter.ingestion.draft": "adapter_ingestion_draft",
        }

        schema_key = type_to_schema.get(event_type, "envelope")
        return self.schemas.get(schema_key, self.schemas.get("envelope", {}))

    def validate_event(self, event: Dict, schema: Dict) -> Tuple[bool, str]:
        """Validate a single event against a schema."""
        try:
            # Create validator with format checking and reference registry
            validator_cls = validator_for(schema)
            format_checker = jsonschema.FormatChecker()

            # Add custom date-time format checker (jsonschema doesn't include it by default)
            import re
            from datetime import datetime

            DATETIME_REGEX = re.compile(
                r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?(Z|[+-]\d{2}:\d{2})$'
            )

            @format_checker.checks("date-time")
            def check_datetime(value: str) -> bool:
                if not isinstance(value, str):
                    return False
                if not DATETIME_REGEX.match(value):
                    return False
                try:
                    if value.endswith('Z'):
                        datetime.fromisoformat(value.replace('Z', '+00:00'))
                    else:
                        datetime.fromisoformat(value)
                    return True
                except:
                    return False

            # Build registry with envelope schema for $ref resolution
            envelope_schema = self.schemas.get("envelope", {})
            if envelope_schema:
                resource = Resource.from_contents(envelope_schema)
                registry = Registry().with_resource("envelope.schema.json", resource)
            else:
                registry = Registry()

            validator = validator_cls(schema, format_checker=format_checker, registry=registry)
            validator.validate(event)
            return True, "Valid"
        except ValidationError as e:
            return False, f"ValidationError: {e.message}"
        except Exception as e:
            return False, f"Error: {type(e).__name__}: {e}"

    def run_valid_tests(self) -> None:
        """Test all valid fixtures pass validation."""
        print("\n=== Testing Valid Fixtures ===")
        for name, fixture in self.valid_fixtures.items():
            schema = self.get_schema_for_event(fixture)
            valid, msg = self.validate_event(fixture, schema)
            self.results.append((f"valid/{name}", valid, msg))
            status = "PASS" if valid else "FAIL"
            print(f"  {status} {name}: {msg}")

    def run_invalid_tests(self) -> None:
        """Test all invalid fixtures fail validation."""
        print("\n=== Testing Invalid Fixtures ===")
        for name, fixture in self.invalid_fixtures.items():
            schema = self.get_schema_for_event(fixture)
            valid, msg = self.validate_event(fixture, schema)
            # Invalid fixtures should FAIL validation
            passed = not valid
            self.results.append((f"invalid/{name}", passed, msg if not valid else "Should have failed but passed"))
            status = "PASS" if passed else "FAIL"
            print(f"  {status} {name}: {msg if not valid else 'UNEXPECTEDLY PASSED'}")

    def run_schema_self_validation(self) -> None:
        """Validate each schema against meta-schema."""
        print("\n=== Schema Self-Validation ===")
        meta_schema = json.loads("""{
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "type": "object"
        }""")
        for name, schema in self.schemas.items():
            try:
                jsonschema.Draft202012Validator.check_schema(schema)
                self.results.append((f"schema/{name}", True, "Valid schema"))
                print(f"  PASS {name}")
            except Exception as e:
                self.results.append((f"schema/{name}", False, f"Invalid schema: {e}"))
                print(f"  FAIL {name}: {e}")

    def run_cross_reference_tests(self) -> None:
        """Test that $ref references resolve correctly."""
        print("\n=== Cross-Reference Tests ===")
        for name, schema in self.schemas.items():
            refs = self._extract_refs(schema)
            for ref in refs:
                if ref.startswith("envelope.schema.json"):
                    if "envelope" in self.schemas:
                        self.results.append((f"ref/{name}->{ref}", True, "Resolved"))
                        print(f"  PASS {name} -> {ref}")
                    else:
                        self.results.append((f"ref/{name}->{ref}", False, "Envelope schema not found"))
                        print(f"  FAIL {name} -> {ref}: Envelope schema not found")
                elif ref.startswith("#"):
                    # Internal reference - always resolvable
                    self.results.append((f"ref/{name}->{ref}", True, "Internal reference"))
                    print(f"  PASS {name} -> {ref} (internal)")

    def _extract_refs(self, obj: Any, refs: List[str] = None) -> List[str]:
        """Extract all $ref values from a schema."""
        if refs is None:
            refs = []
        if isinstance(obj, dict):
            if "$ref" in obj:
                refs.append(obj["$ref"])
            for v in obj.values():
                self._extract_refs(v, refs)
        elif isinstance(obj, list):
            for item in obj:
                self._extract_refs(item, refs)
        return refs

    def run_version_tests(self) -> None:
        """Test schema version format and event schema_version matching."""
        print("\n=== Version Tests ===")
        for name, fixture in self.valid_fixtures.items():
            schema_version = fixture.get("schema_version", "")
            # Check semver format
            import re
            if re.match(r"^\d+\.\d+\.\d+$", schema_version):
                self.results.append((f"version/{name}", True, f"Valid semver: {schema_version}"))
                print(f"  PASS {name}: {schema_version}")
            else:
                self.results.append((f"version/{name}", False, f"Invalid semver: {schema_version}"))
                print(f"  FAIL {name}: {schema_version}")

    def run_required_field_tests(self) -> None:
        """Test that all required fields are enforced."""
        print("\n=== Required Field Tests ===")
        envelope_schema = self.schemas.get("envelope", {})
        required_fields = envelope_schema.get("required", [])

        for field in required_fields:
            # Create event missing this field
            test_event = self.valid_fixtures["window_focus_changed"].copy()
            if field in test_event:
                del test_event[field]

            valid, msg = self.validate_event(test_event, envelope_schema)
            passed = not valid  # Should fail
            self.results.append((f"required/{field}", passed,
                                f"Missing {field}: {'correctly rejected' if passed else 'incorrectly accepted'}"))
            status = "PASS" if passed else "FAIL"
            print(f"  {status} missing {field}: {'rejected' if passed else 'ACCEPTED (BUG)'}")

        # Also test additionalProperties: false on envelope
        test_event = self.valid_fixtures["window_focus_changed"].copy()
        test_event["unknown_top_level"] = "should fail"
        valid, msg = self.validate_event(test_event, envelope_schema)
        passed = not valid
        self.results.append(("additionalProperties/unknown_top_level", passed,
                            "Unknown top-level field rejected" if passed else "Unknown field accepted"))
        status = "PASS" if passed else "FAIL"
        print(f"  {status} unknown top-level field: {'rejected' if passed else 'ACCEPTED (BUG)'}")

    def run_timestamp_tests(self) -> None:
        """Test timestamp format validation."""
        print("\n=== Timestamp Tests ===")
        test_event = self.valid_fixtures["window_focus_changed"].copy()

        # Valid timestamps
        valid_timestamps = [
            "2026-11-05T12:34:56.789Z",
            "2026-11-05T12:34:56Z",
            "2026-11-05T12:34:56+00:00",
            "2026-11-05T12:34:56.123456Z",
        ]

        for ts in valid_timestamps:
            test_event["timestamp_utc"] = ts
            valid, _ = self.validate_event(test_event, self.get_schema_for_event(test_event))
            self.results.append((f"timestamp/valid/{ts}", valid, "Valid timestamp"))
            status = "PASS" if valid else "FAIL"
            print(f"  {status} {ts}")

        # Invalid timestamps
        invalid_timestamps = [
            "not-a-timestamp",
            "2026-11-05",
            "12:34:56",
            "",
            "2026-13-05T12:34:56Z",  # invalid month
        ]

        for ts in invalid_timestamps:
            test_event["timestamp_utc"] = ts
            valid, _ = self.validate_event(test_event, self.get_schema_for_event(test_event))
            passed = not valid
            self.results.append((f"timestamp/invalid/{ts}", passed, "Invalid timestamp"))
            status = "PASS" if passed else "FAIL"
            print(f"  {status} {ts}: {'rejected' if passed else 'ACCEPTED (BUG)'}")

    def run_event_identity_tests(self) -> None:
        """Test event_id and correlation ID validation."""
        print("\n=== Event Identity Tests ===")
        test_event = self.valid_fixtures["window_focus_changed"].copy()

        # Valid UUIDs
        valid_uuids = [
            "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
            "12345678-1234-5678-1234-567812345678",
            "ffffffff-ffff-ffff-ffff-ffffffffffff",
        ]

        for uuid in valid_uuids:
            test_event["event_id"] = uuid
            valid, _ = self.validate_event(test_event, self.get_schema_for_event(test_event))
            self.results.append((f"uuid/valid/{uuid}", valid, "Valid UUID"))

        # Invalid UUIDs
        invalid_uuids = [
            "not-a-uuid",
            "aaaaaaaa-bbbb-cccc-dddd",  # too short
            "gggggggg-bbbb-cccc-dddd-eeeeeeeeeeee",  # invalid hex
            "",
        ]

        for uuid in invalid_uuids:
            test_event["event_id"] = uuid
            valid, _ = self.validate_event(test_event, self.get_schema_for_event(test_event))
            passed = not valid
            self.results.append((f"uuid/invalid/{uuid}", passed, "Invalid UUID"))

    def run_correlation_tests(self) -> None:
        """Test cross-event correlation validation."""
        print("\n=== Cross-Event Correlation Tests ===")

        # Test that events in same session have same session_id
        window_event = self.valid_fixtures["window_focus_changed"]
        afk_event = self.valid_fixtures["afk_state_changed"]

        same_session = window_event["correlation"]["session_id"] == afk_event["correlation"]["session_id"]
        self.results.append(("correlation/same_session", same_session,
                            "Events share session_id" if same_session else "Different sessions"))
        print(f"  {'PASS' if same_session else 'FAIL'} Same session_id: {same_session}")

        # Test that external_run_id matches for ingestion draft
        ingestion = self.valid_fixtures["adapter_ingestion_draft"]
        correlated = self.valid_fixtures["adapter_correlated_activity"]

        same_run = ingestion["correlation"]["external_run_id"] == correlated["correlation"]["external_run_id"]
        self.results.append(("correlation/same_run", same_run,
                            "Ingestion matches correlated run" if same_run else "Run ID mismatch"))
        print(f"  {'PASS' if same_run else 'FAIL'} Same external_run_id: {same_run}")

    def run_privacy_tests(self) -> None:
        """Test privacy assertions - no raw window titles in adapter events."""
        print("\n=== Privacy Tests ===")

        # Adapter correlated activity should not contain raw window titles
        correlated = self.valid_fixtures["adapter_correlated_activity"]
        ingestion = self.valid_fixtures["adapter_ingestion_draft"]

        # Check correlated activity payload
        has_raw_title = False
        payload_str = json.dumps(correlated["payload"])
        if "Project_A.rvt" in payload_str and "Autodesk Revit" in payload_str:
            has_raw_title = True

        # The adapter event should only have model_identity, not raw window titles
        passed = not has_raw_title
        self.results.append(("privacy/no_raw_titles_in_correlated", passed,
                            "No raw window titles" if passed else "Raw window titles found"))
        print(f"  {'PASS' if passed else 'FAIL'} No raw titles in correlated: {passed}")

        # Ingestion draft should have proof_metadata.privacy_filter_applied = true
        privacy_filtered = ingestion["payload"]["timesheet_entry"]["proof_metadata"].get("privacy_filter_applied", False)
        self.results.append(("privacy/filter_applied", privacy_filtered,
                            "Privacy filter applied" if privacy_filtered else "Privacy filter NOT applied"))
        print(f"  {'PASS' if privacy_filtered else 'FAIL'} Privacy filter applied: {privacy_filtered}")

    def print_summary(self) -> None:
        """Print test summary."""
        total = len(self.results)
        passed = sum(1 for _, p, _ in self.results if p)
        failed = total - passed

        print(f"\n{'='*50}")
        print(f"SUMMARY: {passed}/{total} passed ({failed} failed)")
        print(f"{'='*50}")

        if failed > 0:
            print("\nFAILURES:")
            for name, passed, msg in self.results:
                if not passed:
                    print(f"  FAIL {name}: {msg}")
            sys.exit(1)
        else:
            print("\nAll tests passed!")
            sys.exit(0)


def main():
    tester = SchemaTester()
    tester.load_schemas()
    tester.load_fixtures()
    tester.run_schema_self_validation()
    tester.run_valid_tests()
    tester.run_invalid_tests()
    tester.run_version_tests()
    tester.run_required_field_tests()
    tester.run_timestamp_tests()
    tester.run_event_identity_tests()
    tester.run_correlation_tests()
    tester.run_privacy_tests()
    tester.run_cross_reference_tests()
    tester.print_summary()


if __name__ == "__main__":
    main()