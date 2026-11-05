# BIMSpend — Gate B2-A Execution Plan (Preparation Only)

**Mode:** B2-A PREPARATION ONLY. No implementation, no dependency installation, no build execution, no application code modification.  
**Branch:** `agent/opencode-b2a` (created from `main` at `eb13fc9`)  
**Repository:** https://github.com/ueiider/BIMSpend  
**Related report:** `docs/technical-feasibility/PLAN_AUDIT_REPORT.md` (P1-01 through P1-07 complete, static audit only)  
**Parent task tracker:** `TASK_TRACKER.md` — B2-01 / Gate B2-A is BLOCKED pending explicit user approval

---

## 1. Purpose

Prepare a **reproducible execution plan** for Gate B2-A ("Reproducible baselines"), as defined in `PLAN_AUDIT_REPORT.md` §9 and `TASK_TRACKER.md` row B2-01.

This document is **planning only**. It does not install dependencies, run builds, execute tests, or modify any application code. It defines the exact commands, pinned SHAs, artifacts, acceptance criteria, and stop/go conditions that would be used if and when the user explicitly approves Gate B2-A.

---

## 2. Governing constraints (from MASTER_PLAN.md, TASK_TRACKER.md, AI_HANDOFF.md)

| Constraint | Source | Binding on B2-A |
|---|---|---|
| No product implementation until explicit user approval | MASTER_PLAN §10 | B2-A remains blocked until approval |
| Reuse-first; evaluate before custom code | MASTER_PLAN §11 | B2-A inventories reuse candidates only |
| GitHub is the single source of truth | MASTER_PLAN §18 | All durable evidence committed here |
| Do not modify main | B2-A task rule | All work on `agent/opencode-b2a` |
| Do not modify FBT Revit Academy | All governing docs | Not touched |
| No dependency installation | B2-A task rule | Commands listed but not executed |
| No build execution | B2-A task rule | Commands listed but not executed |
| No binaries or large build outputs | B2-A task rule | Only text/SHA/manifest artifacts |
| No secrets or personal data | B2-A task rule | Synthetic fixtures only |
| Do not start B2-B or B3 | B2-A task rule | Out of scope |

---

## 3. Pinned upstream revisions (verified)

Verified against local clones at `D:\BIMSpend\Research\Repos\`:

| Component | Pinned SHA | Branch | Local clone path | Verified match |
|---|---|---|---|---|
| Miru | `10e457e1d0cd2ac782be9d1edbcbd5a1a573486a` | `develop` | `D:\BIMSpend\Research\Repos\miru-web` | YES |
| ActivityWatch bundle | `9fee4702fea08dbe0149cc6e28f4ef66b49f54ec` | `master` | `D:\BIMSpend\Research\Repos\activitywatch` | YES |

ActivityWatch component gitlinks (from `.gitmodules`, submodule status, **not initialized / empty on disk**):

| Submodule | Gitlink SHA | URL |
|---|---|---|
| aw-client | `fe106969fcd413ffadbd5a9d3b75808cc636cd54` | https://github.com/ActivityWatch/aw-client.git |
| aw-core | `28c3acf047b225f90592e1c47c8ec2596612d70b` | https://github.com/ActivityWatch/aw-core.git |
| aw-notify | `87e83cca65276b2278e4361db74087764c3ecf2c` | https://github.com/ActivityWatch/aw-notify-rs.git |
| aw-qt | `bbccb715516c5c02f863f883680aee0e40c803b5` | https://github.com/ActivityWatch/aw-qt.git |
| aw-server | `67cfb479a9f8511ad3a9595224cb22c35b9dbe65` | https://github.com/ActivityWatch/aw-server.git |
| aw-server-rust | `fe558c4f106a70004a42bc30558c7438f8b66b4f` | https://github.com/ActivityWatch/aw-server-rust.git |
| aw-tauri | `44b92d45878504fc7b9d1d9e867e8967cccd9b17` | https://github.com/activitywatch/aw-tauri |
| aw-watcher-afk | `b4839261688eb7980d1730d46dd35a36b21cfc1d` | https://github.com/ActivityWatch/aw-watcher-afk.git |
| aw-watcher-input | `4e6461dbf55a1c1aa8f9ece4df5f109188f56f61` | https://github.com/ActivityWatch/aw-watcher-input.git |
| aw-watcher-window | `10638b2c94e46195f709abd8626cb15f911e99f8` | https://github.com/ActivityWatch/aw-watcher-window.git |
| awatcher | `c32ca62c66e6ff4f2949b841ec20d30c778d11ba` | https://github.com/2e3s/awatcher |

> NOTE: The PLAN_AUDIT_REPORT.md §2.1 lists component-level "head observed" SHAs that may differ from the bundle gitlinks above. The report itself marks this equality as **NÃO VALIDADO**. Gate B2-A must record `git submodule status --recursive` at checkout time to resolve the exact difference.

---

## 4. Prerequisite versions (from pinned sources)

### Miru (pinned `10e457e`)

| Prerequisite | Version | Source file |
|---|---|---|
| Ruby | 4.0.9 | `.ruby-version` |
| Node.js | 24.22.1 | `.node-version`, `.nvmrc` |
| Rails | ~8.1.4 | `Gemfile` |
| Database | PostgreSQL | `Gemfile` (`gem "pg"`) |
| Package manager (Ruby) | Bundler | `Gemfile.lock` |
| Package manager (JS) | pnpm | `pnpm-lock.yaml` |
| Build tool | Vite | `vite.config.mts` |
| Deployment | Kamal, Docker | `Gemfile`, `Dockerfile*`, `render.yaml` |

### ActivityWatch bundle (pinned `9fee4702`)

| Prerequisite | Version | Source file |
|---|---|---|
| Python | 3.9.13 | `.tool-versions` |
| Poetry | 1.5.1 | `.tool-versions` |
| Node.js | 16.20.2 | `.tool-versions` |
| Rust | nightly | `.tool-versions` |
| Build | PyInstaller | `pyproject.toml` dev deps |
| Windows deps | pywin32-ctypes, pefile | `pyproject.toml` (win32 platform) |
| Setuptools bound | >=78.1.1,<81 | `pyproject.toml` |

### Missing / NOT VALIDADO prerequisites

| Prerequisite | Status | Reason |
|---|---|---|
| Ruby 4.0.9 runtime | NOT INSTALLED | Not installed; do not install per B2-A rules |
| Node 24.22.1 / pnpm | NOT INSTALLED | Not installed; do not install per B2-A rules |
| PostgreSQL server | NOT INSTALLED | Not installed; do not install per B2-A rules |
| Python 3.9.13 / Poetry | NOT INSTALLED | Not installed; do not install per B2-A rules |
| Rust nightly toolchain | NOT INSTALLED | Not installed; do not install per B2-A rules |
| ActivityWatch submodule contents | EMPTY (not initialized) | Submodule directories exist but contain no files; `git submodule status` shows all `-` |
| Recursive submodule SHAs | NOT RECORDED | Cannot record without initializing submodules (out of scope for B2-A preparation) |
| Lockfile license/CVE inventory | NOT PERFORMED | Static inspection only; no scans executed |
| Docker base image digest | NOT VERIFIED | Observed in Dockerfile but not pulled/inspected at runtime |

---

## 5. Reproducible execution plan (Gate B2-A)

The following is the **exact sequence** that would be run under explicit user approval. Commands are documented for reproducibility; none are executed in this preparation step.

### Step 5.1 — Isolated workspaces at pinned SHAs

```
# Miru isolated checkout
git clone https://github.com/saeloun/miru-web.git b2a-miru
cd b2a-miru
git checkout 10e457e1d0cd2ac782be9d1edbcbd5a1a573486a

# ActivityWatch isolated checkout
git clone https://github.com/ActivityWatch/activitywatch.git b2a-activitywatch
cd b2a-activitywatch
git checkout 9fee4702fea08dbe0149cc6e28f4ef66b49f54ec
```

### Step 5.2 — Recursive submodule SHA capture

```
cd b2a-activitywatch
git submodule status --recursive > b2a-aw-submodules.txt
git submodule summary > b2a-aw-submodule-summary.txt
```

> NOTE: Submodules are currently empty/uninitialized. Initializing them (`git submodule update --init --recursive`) would clone 11 additional repositories. This is permitted as temporary build workspace but must not be committed to BIMSpend.

### Step 5.3 — SBOM / license inventory

```
# Miru
cd b2a-miru
bundle licenses > b2a-miru-licenses.txt 2>&1 || true
cat Gemfile.lock > b2a-miru-gemfile.lock.txt
cat package.json > b2a-miru-package.json.txt
cat pnpm-lock.yaml > b2a-miru-pnpm-lock.yaml.txt

# ActivityWatch
cd ../b2a-activitywatch
cat pyproject.toml > b2a-aw-pyproject.toml.txt
cat poetry.lock > b2a-aw-poetry.lock.txt 2>&1 || true
cat .tool-versions > b2a-aw-tool-versions.txt
cat .gitmodules > b2a-aw-gitmodules.txt
```

### Step 5.4 — Documented builds/tests (commands only, not executed)

```
# Miru build (documented, not run)
cd b2a-miru
mise exec -- bundle install
mise exec -- bundle exec rake i18n:config
mise exec -- bundle exec rails spec   # or rspec

# ActivityWatch build (documented, not run)
cd ../b2a-activitywatch
poetry install --no-interaction
make  # or equivalent documented build target
```

### Step 5.5 — Static dependency/security scans (commands only, not run)

```
# Miru
bundle audit check --update
brakeman

# ActivityWatch (Python/Rust)
# poetry check, safety, bandit, cargo audit (if Rust components built)
```

### Step 5.6 — Evidence capture and teardown

| Artifact | Description | Committed to BIMSpend? |
|---|---|---|
| `b2a-miru-head.txt` | `git rev-parse HEAD` output | YES |
| `b2a-aw-head.txt` | `git rev-parse HEAD` output | YES |
| `b2a-aw-submodules.txt` | `git submodule status --recursive` output | YES |
| `b2a-miru-gemfile.lock.txt` | Frozen Ruby lockfile | YES |
| `b2a-miru-package.json.txt` | Frozen Node manifest | YES |
| `b2a-aw-pyproject.toml.txt` | Frozen Python manifest | YES |
| `b2a-aw-tool-versions.txt` | Frozen toolchain versions | YES |
| `b2a-build-results.txt` | Build/test pass/fail per step | YES |
| `b2a-scan-results.txt` | Security scan output (failures included) | YES |
| `b2a-stop-go-evaluation.md` | Stop/go recommendation with evidence | YES |

**Clean teardown:** Remove isolated workspaces after evidence capture. No changes to user's machine. No production device changes.

---

## 6. Acceptance criteria (Gate B2-A)

From `PLAN_AUDIT_REPORT.md` §9:

- [ ] No user production device changes.
- [ ] All commands reproducible from a clean environment.
- [ ] Licenses/notices enumerated.
- [ ] Test and scan output attached **with failures**, not summarized away.
- [ ] Stop if build cannot be reproduced or license blockers appear.

---

## 7. Stop / go conditions

| Condition | Action |
|---|---|
| Clean build reproduces at pinned SHAs | GO to next gate (only after separate user approval) |
| Build fails or cannot be reproduced | STOP; document failure; do not proceed |
| License blocker (MPL/GPL/AGPL conflict with commercial distribution) | STOP; legal review required before proceeding |
| Any dependency vulnerability with available fix | Document; do not silently proceed |
| Submodule SHA mismatch vs PLAN_AUDIT_REPORT.md | Document as NÃO VALIDADO discrepancy; proceed with recorded gitlinks |

---

## 8. Artifacts to commit to BIMSpend (this branch)

The following text-only artifacts constitute the durable evidence for Gate B2-A preparation:

- `docs/agents/opencode/B2A_EXECUTION_PLAN.md` (this document)
- Pinned SHA references (verified in §3)
- Prerequisite version inventory (§4)
- Missing prerequisite inventory (§4)
- Reproducible command sequence (§5)
- Acceptance criteria (§6)
- Stop/go conditions (§7)

**Not committed:** isolated workspace clones, build outputs, binaries, lockfile scan results from actual execution (none executed), secrets, personal data.

---

## 9. Risk notes

| Risk | Severity | Mitigation in this plan |
|---|---|---|
| ActivityWatch submodules empty (not initialized) | Medium | Documented gitlinks; recursive capture deferred to actual B2-A execution |
| Component SHA mismatch vs audit report | Medium | Record actual gitlinks at checkout; flag as NÃO VALIDADO if different |
| Ruby 4.0.9 / Node 24.22.1 availability | Low | Documented version requirements; no installation in preparation |
| MPL-2.0 distribution obligations | High | Documented in PLAN_AUDIT_REPORT §2.2; legal review required before any distribution |
| Cross-tenant security | High | Out of scope for B2-A; deferred to B2-B/B3 |

---

## 10. Next step after this plan

This branch (`agent/opencode-b2a`) is pushed to GitHub for review. Gate B2-A remains **BLOCKED** pending explicit user approval. Upon approval, the executor would:

1. Check out this branch.
2. Run the commands in §5 in isolated temporary workspaces.
3. Capture evidence artifacts listed in §5.6.
4. Commit evidence to a follow-up branch (not `main`, not this branch unless approved).
5. Produce stop/go recommendation per §7.

No product integration, UI build, adapter code, Revit connector, or branded UI is created under B2-A.

---

**END OF PLAN — B2-A PREPARATION ONLY**
