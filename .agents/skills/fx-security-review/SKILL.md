---
name: fx-security-review
description: OWASP/ASVS-focused review of authentication, authorization, input handling, logging, files, sessions, secrets and data protection.
---

# FX Security Review Skill

## Purpose
Execute systematic security assessments against OWASP Top 10:2025 and relevant ASVS controls across frontend and backend modules.

## Security Audit Checklist
1. **Broken Access Control**:
   - Verify every endpoint has strict server-side RBAC (`IsStudent`, `IsMentor`, `IsAdmin`).
   - Ensure students cannot access `/api/admin/*` or `/api/mentors/*`.
2. **Cryptographic Failures**:
   - Passwords hashed via PBKDF2 / Argon2.
   - Certificate SHA-256 integrity digests validated.
   - Sensitive tokens never logged.
3. **Injection Defense**:
   - All database queries parameterized via Django ORM.
   - User inputs sanitized and validated.
4. **Session & Cookie Security**:
   - HTTP-only, SameSite cookies or secure Authorization Bearer header.
5. **Data Protection & Privacy**:
   - Clear proctoring notice and consent preflight.
   - No continuous raw video stored without policy justification.
