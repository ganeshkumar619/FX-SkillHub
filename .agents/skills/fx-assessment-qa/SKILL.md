---
name: fx-assessment-qa
description: Assessment timer, autosave, randomization, concurrency, proctoring event and result verification.
---

# FX Assessment QA Skill

## Purpose
Verify the correctness, resilience, and proctoring integrity of the assessment engine.

## Test Protocols
1. **Authoritative Timing**:
   - Ensure `end_time` is determined on the server at attempt creation.
   - Verify that altering local device clocks does not extend exam time.
   - Confirm server auto-submits upon timer expiry.
2. **Integrity & Randomization**:
   - Confirm questions and options are randomized per student attempt.
   - Confirm correct answers and explanations are stripped from client API payloads.
3. **Autosave & Concurrency**:
   - Confirm answers are committed immediately on option selection.
   - Attempting to open a second concurrent attempt returns HTTP 409 Conflict.
4. **Proctoring Signals**:
   - Simulate `visibilitychange` (tab switch) -> verify event logged with severity.
   - Simulate `fullscreenchange` exit -> verify warning counter and event logged.
   - Verify risk score recalculation and tier classification (`NORMAL`, `LOW`, `MEDIUM`, `HIGH`, `CRITICAL`).
