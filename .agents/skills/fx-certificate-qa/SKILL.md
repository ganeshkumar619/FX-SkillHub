---
name: fx-certificate-qa
description: Certificate issuance, uniqueness, PDF rendering, QR verification, revocation and email idempotency.
---

# FX Certificate QA Skill

## Purpose
Ensure digital credentials issued by FX SkillHub are cryptographically verifiable, unique, tamper-evident, and deliverable.

## QA Checkpoints
1. **Uniqueness**:
   - Ensure a student cannot be issued two certificates for the same completed course enrollment.
2. **PDF Integrity**:
   - Server-side PDF rendered with student name, course title, date, unique UUID, and SHA-256 integrity hash.
   - Embedded QR code points directly to canonical verification URL (`/verify-certificate/:uuid`).
3. **Public Verification**:
   - Route `/verify-certificate/:uuid` returns live status:
     - `VALID`: Authentic certificate details displayed.
     - `REVOKED`: Displays revocation timestamp and verified reason.
     - `NOT_FOUND`: Clean error state for invalid hashes/IDs.
4. **Email Idempotency**:
   - Ensure certificate issuance triggers asynchronous notification.
   - Resending or re-evaluating does not trigger duplicate emails.
