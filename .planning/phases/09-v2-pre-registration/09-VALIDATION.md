---
phase: 9
slug: v2-pre-registration
status: draft
nyquist_compliant: true
wave_0_complete: true
created: 2026-11-11
---

# Phase 9 — Validation Strategy

> Per-phase validation contract. Docs-only phase: every check is a read-only shell command (see 09-RESEARCH.md "Validation Architecture"). Verification must NEVER edit pipeline/PREREGISTRATION_V2.md (a second commit voids it).

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (existing, pipeline/) + git/shasum/grep shell checks |
| **Config file** | pipeline/pyproject.toml |
| **Quick run command** | `git log --format=%H -- pipeline/PREREGISTRATION.md \| wc -l && shasum -a 256 pipeline/PREREGISTRATION.md` |
| **Full suite command** | `cd pipeline && uv run pytest -q` |
| **Estimated runtime** | ~140 seconds |

---

## Sampling Rate

- **Before writing:** checks 1, 2, 2b (baseline)
- **After the single prereg commit:** checks 1–8
- **Before verify-work:** full suite must be green
- **Max feedback latency:** 140 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 9-01-01 | 01 | 1 | INTEG-02, INTEG-03 | — | N/A | shell | content-coverage grep loop (check 6) + verdict grep (check 7) on the draft before commit | ✅ | ⬜ pending |
| 9-01-02 | 01 | 1 | INTEG-02 | — | N/A | shell | checks 1, 2, 2b, 3, 4, 5, 8 after the commit | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

Existing infrastructure covers all phase requirements.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Definitions precise enough for someone else to build | INTEG-02 | Judgment of prose precision | Read each MODEL-V2 section; confirm formula, data source, columns, as-of rule and drop rule are stated |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 140s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-11-11
