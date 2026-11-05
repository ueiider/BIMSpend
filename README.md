# BIMSpend — Product Discovery & Brainstorm

> **Status: EXPLORATION ONLY.** No product architecture, feature, brand rights, pricing, or implementation is approved.
> Last consolidated: 2026-11-05. Working language: Portuguese for discussion, English for technical terms.
> Repository: `ueiider/BIMSpend` (PRIVATE). Local workspace: `D:\BIMSpend`.

## Product hypothesis

A low-friction, subscription-based system for architecture/engineering/BIM companies that observes work sessions across Autodesk applications, aggregates time by project and employee, and may connect **actual time → internal cost → invoiced hours → future estimates**.

**Core user requirement:** Designers install once and do not need to log in daily, start a timer, choose a project, or enter timesheets. A manager on another computer reviews organization-wide project information. Admin onboarding, employee notice, permissions, and ambiguous project mapping still require design.

## Start here

- [Complete conversation-based concept and chronology](docs/brainstorming/conversation-record.md)
- [Requirements, hypotheses, unresolved questions](docs/product-vision/problem-statements-and-personas.md)
- [Product vision and conceptual roadmap](docs/product-vision/product-roadmap.md)
- [Technical feasibility and historical Revit Journals](docs/technical-feasibility/technical-research.md)
- [Revit Journal historical-data research](docs/research/historical-data-research.md)
- [Competitors, naming, verification gaps](docs/competitors/market-and-brand.md)
- [Financial model, sample data, privacy](docs/financial-model/commercial-data-and-pricing.md)
- [Synthetic example calculations](docs/financial-model/synthetic-examples.md)
- [Visual concept gallery](visuals/README.md)
- [Decision log and next action](docs/decisions/decision-log.md)
- [Mobile/AI handoff prompt](CONTEXT_FOR_AI.md)
- [AI agent operating instructions](AGENTS.md)

## How to resume on mobile

Open this repository in GitHub and ask your assistant to read `CONTEXT_FOR_AI.md`, `README.md`, and `docs/decisions/decision-log.md` first. Ask it to append new ideas and mark whether they are **idea**, **hypothesis**, **tested**, or **approved**. Use GitHub Issues for discrete investigations; do not turn brainstorm notes into requirements without explicit approval.

## Confidentiality

Never commit client/project names, employee-identifiable records, actual rate cards, invoices, journal files, company data, or the original uploaded spreadsheets to a public repository. Financial figures in this repository are synthetic illustrations or explicitly labelled, non-verifiable discussion summaries. Use a private repository for ongoing development and store raw company data outside git with permission. See `.gitignore` for blocked file patterns.

## What this repository is NOT

No working Autodesk add-in, desktop agent, backend, production database, trained AI, or proven historical time recovery exists here. This repository is for documentation, research organization, and brainstorming only.
