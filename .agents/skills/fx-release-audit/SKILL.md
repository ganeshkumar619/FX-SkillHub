---
name: fx-release-audit
description: Full release gate, test suite, dependency audit, build audit and demo-readiness report.
---

# FX Release Audit Skill

## Purpose
Execute final pre-expo quality and compliance audits before tagging the September 15 release candidate.

## Release Audit Protocols
1. Verify that no mock/fabricated institutional data exists in the production seed.
2. Confirm `.env` is omitted from version control and `.env.example` is complete.
3. Execute backend unit and integration test suite.
4. Execute frontend production build (`npm run build`) and confirm zero bundle warnings/errors.
5. Verify that certificate QR URLs dynamically resolve to the active host domain.
6. Verify clear empty states and error boundaries on all routes.
7. Validate that all demo accounts are explicitly flagged with `environment = 'DEMO'`.
