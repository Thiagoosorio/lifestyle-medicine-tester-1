# Codex Subagent Starter Pack

This project includes a focused subagent pack for:

- scientific score correctness
- evidence and citation verification
- migration safety
- test and release reliability
- Streamlit UX fixes

## Installed Agents

- `reviewer` (read-only): PR-style correctness and regression review
- `security-auditor` (read-only): input handling, auth, secrets, data exposure
- `test-automator` (workspace-write): add/repair tests with edge coverage
- `schema-migration-guard` (workspace-write): SQLite-safe migrations and backfills
- `clinical-score-auditor` (read-only): score formula, units, thresholds, edge-case audit
- `evidence-verifier` (read-only): source-backed evidence checks with uncertainty tags
- `streamlit-ui-fixer` (workspace-write): smallest safe UI bug fix and state handling
- `release-checker` (read-only): final launch checklist with blockers and risks
- `ui-designer` (read-only): implementation-ready visual and interaction guidance
- `frontend-developer` (workspace-write): scoped frontend implementation and UX bug fixes
- `accessibility-tester` (read-only): a11y audits for keyboard, focus, semantics, contrast
- `ux-researcher` (read-only): translate user friction into prioritized product changes

## How To Use

Delegate explicitly in prompts. Examples:

1. `Use reviewer + test-automator in parallel for this branch, then summarize top risks with file references.`
2. `Use clinical-score-auditor to audit organ and wearable score math for boundary and unit errors.`
3. `Use evidence-verifier to validate citations in reports/evidence_audit and flag unsupported claims.`
4. `Use schema-migration-guard to make this DB change backward-compatible with existing SQLite files.`
5. `Run release-checker before push and list only blocking issues first.`
6. `Use ui-designer + ux-researcher to improve patient flow clarity on the wearable and organ score pages.`
7. `Use frontend-developer to implement the approved UX changes; use accessibility-tester for final pass.`

## Scientific Evidence Rules

The `evidence-verifier` and `clinical-score-auditor` agents are configured to:

- never invent citations, DOI, PMID, or URLs
- mark unsupported claims with:
  - `uncertain - single source`
  - `uncertain - no direct evidence`
  - `unknown - not found in sources`
- require two independent high-quality sources for high-impact clinical claims
- prefer guidelines, systematic reviews, meta-analyses, and large RCTs
