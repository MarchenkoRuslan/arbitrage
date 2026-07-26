# Documentation Maintenance Guide

## Purpose

Keep project documentation, development plans, and repository instructions aligned
with the actual codebase and runtime behavior.

## Source of Truth

Priority order for technical truth:
1. Runtime code in `src/`
2. Tests in `tests/`
3. Configuration defaults in `src/core/config.py`
4. Public docs in `README.md` and `docs/`

If docs conflict with code, update docs in the same change set.

## Required Updates per Change Type

### Behavior change (user-visible)

Update all that apply:
- `README.md` (Overview / Status / Usage)
- Relevant page under `docs/`
- `docs/04-development-roadmap.md` (phase/status)
- `docs/11-release-notes-template.md` (fill and attach to PR notes)

### Exchange connector change

Update all that apply:
- `docs/05-exchanges-api.md`
- Dedicated venue page under `docs/api/`
- Any formula notes (for example Lighter funding approximation)

### New configuration variable

Update all that apply:
- `src/core/config.py`
- `README.md` (Main Environment Variables)
- Any impacted strategy/risk doc

### Architecture changes

Update all that apply:
- `docs/02-system-architecture.md`
- `README.md` structure/status section

## Update Checklist (PR Ready)

- [ ] README reflects current runtime and limits
- [ ] Roadmap status reflects delivered scope
- [ ] API references match connector behavior
- [ ] Strategy formulas match implementation
- [ ] Risk and ops notes reflect current features (not future features)
- [ ] No duplicated sections in docs
- [ ] No references to removed venues/components
- [ ] Release note prepared for behavior-changing updates
- [ ] Documentation links and heading anchors validated

## Writing Rules

- Keep all user-facing docs in English.
- Prefer short, concrete statements over speculative roadmap prose.
- Mark planned features explicitly as planned.
- Include formulas exactly as implemented when practical.

## Review Cadence

- On every behavior-changing PR: mandatory docs review.
- Weekly: quick audit of `README.md`, roadmap, and active API pages.
- Before release/tag: full docs consistency pass.

## CI Behavior

- `CI` workflow runs lint/tests for non-doc changes.
- `Docs CI` workflow runs on docs/template updates and validates markdown links and heading anchors.
