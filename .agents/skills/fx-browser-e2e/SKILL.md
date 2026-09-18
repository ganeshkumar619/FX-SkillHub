---
name: fx-browser-e2e
description: Execute the golden path in the browser, capture failures, and produce a reproducible QA report.
---

# FX Browser E2E Skill

## Purpose
Execute end-to-end browser verification of the complete student and faculty golden path using the Antigravity Browser Agent.

## Golden Path Scenario
1. Authenticate as student.
2. Explore skill catalogue and select an active course.
3. Complete module progression.
4. Pass preflight checks (camera, screen, fullscreen).
5. Complete assessment questions and trigger a test proctoring event (tab switch / fullscreen exit).
6. Submit exam and verify immediate scoring.
7. Confirm certificate issuance, view PDF, and open QR verification link.
8. Verify public verification page displays `VALID`.
9. Verify email log shows notification dispatched.
