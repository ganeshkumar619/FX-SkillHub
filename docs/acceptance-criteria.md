# FX SkillHub — Acceptance Criteria & Verification Matrix

This document defines the strict, testable acceptance criteria for each phase of FX SkillHub.

---

## Module 1: Authentication & Role-Based Access Control (RBAC)
- [ ] **AC-1.1**: Student, Mentor, and Admin user accounts can authenticate and obtain a valid session token.
- [ ] **AC-1.2**: Unauthenticated requests to protected endpoints return HTTP 401 Unauthorized.
- [ ] **AC-1.3**: Student attempting to access Mentor or Admin endpoints (`/api/admin/*`, `/api/assessments/create`) receives HTTP 403 Forbidden.
- [ ] **AC-1.4**: Passwords are securely hashed with PBKDF2/Argon2; secrets are never exposed in logs or API responses.

## Module 2: Institutional Skill & Course Catalogue
- [ ] **AC-2.1**: All loaded departments match verified FXEC departments (CSE, AI&DS, ECE, EEE, MECH, IT, CIVIL, CSBS, MBA, MCA).
- [ ] **AC-2.2**: Skill categories match FXEC Training Centre tracks (Foundation, Mandatory, Value Added, Placement Fit).
- [ ] **AC-2.3**: Every published course/resource contains non-empty provenance fields (`source_type`, `source_url`, `source_title`, `source_accessed_at`).
- [ ] **AC-2.4**: Missing institutional statistics/logos render neutral pending states (`PENDING_ADMIN_INPUT`), never fake numbers or placeholder names.
- [ ] **AC-2.5**: Admin can add, update, and publish course content with full provenance tracking.

## Module 3: Student Learning Experience & Progress Tracking
- [ ] **AC-3.1**: Enrolled students can access sequential course modules.
- [ ] **AC-3.2**: External instructional videos and reading materials load via lawful embeds or direct resource links without console errors.
- [ ] **AC-3.3**: Clicking "Complete Module" updates the student's progress and calculates total percentage completion.
- [ ] **AC-3.4**: Resuming a course restores the learner's last completed position.
- [ ] **AC-3.5**: Final assessment is locked until required modules reach 100% completion.

## Module 4: AI Skill-Gap Analysis & Recommendation Engine
- [ ] **AC-4.1**: Pre-assessment computes topic-level mastery strictly from correct answers.
- [ ] **AC-4.2**: Topics scoring below passing threshold (< 70%) are flagged as weak topics.
- [ ] **AC-4.3**: Weak topics map directly to existing, published course modules in the database.
- [ ] **AC-4.4**: Recommendation output clearly cites module IDs and reasons.
- [ ] **AC-4.5**: Deterministic fallback produces consistent, identical recommendations when AI service is offline.

## Module 5: Assessment Authoring & Runtime
- [ ] **AC-5.1**: Mentor can create question banks with multiple-choice questions, explanations, difficulty, and marks.
- [ ] **AC-5.2**: Questions and options are shuffled per student attempt; correct answer keys are stripped from student responses.
- [ ] **AC-5.3**: Assessment timer is server-authoritative (`end_time` calculated on server).
- [ ] **AC-5.4**: Autosave records answer selections in real-time.
- [ ] **AC-5.5**: Expired timer triggers automatic server-side submission.
- [ ] **AC-5.6**: Published assessments are versioned; modifications do not mutate historical attempt data.

## Module 6: Browser Proctoring & Security Controls
- [ ] **AC-6.1**: Preflight requires acceptance of privacy notice and verifies camera, screen-share, and fullscreen access.
- [ ] **AC-6.2**: Switching tabs or hiding page fires a `TAB_SWITCH` event recorded in `ProctoringEvent` table with timestamp and severity.
- [ ] **AC-6.3**: Exiting fullscreen fires a `FULLSCREEN_EXIT` event recorded with timestamp.
- [ ] **AC-6.4**: Camera or screen disconnection fires corresponding disconnect events.
- [ ] **AC-6.5**: Risk score is computed transparently from weighted events and classified into non-accusatory tiers (`NORMAL`, `LOW`, `MEDIUM`, `HIGH`, `CRITICAL`).
- [ ] **AC-6.6**: No claim of 100% OS-level lockdown is made; browser permission limits are clearly messaged.

## Module 7: Mentor Proctoring Review Queue
- [ ] **AC-7.1**: Attempts with `HIGH` or `CRITICAL` risk scores appear in the Mentor Review Queue.
- [ ] **AC-7.2**: Mentor can inspect detailed chronological event logs with exact timestamps.
- [ ] **AC-7.3**: Mentor decision (`VALID`, `WARNING`, `INVALID`, `NEEDS_MORE_REVIEW`) is recorded with reviewer identity in immutable audit logs.
- [ ] **AC-7.4**: Automated AI signals cannot unilaterally disqualify an attempt without mentor review.

## Module 8: Digital Certificate Generation & QR Verification
- [ ] **AC-8.1**: Successful completion and passing score triggers automatic PDF certificate generation.
- [ ] **AC-8.2**: Duplicate certificate issuance for the same enrollment is prevented by database uniqueness constraints.
- [ ] **AC-8.3**: Certificate PDF includes student name, course title, completion date, unique UUID, SHA-256 integrity hash, and QR code.
- [ ] **AC-8.4**: Scanning or opening QR URL `/verify-certificate/:uuid` displays live validation status (`VALID`).
- [ ] **AC-8.5**: Revoked certificate returns status `REVOKED` with audit trail; non-existent UUID returns `NOT_FOUND`.

## Module 9: Email Notification Delivery
- [ ] **AC-9.1**: Successful certificate issuance triggers an asynchronous notification job.
- [ ] **AC-9.2**: Email contains branded institutional layout, course name, credential ID, and direct verification link.
- [ ] **AC-9.3**: Email log table records delivery status (`SENT`, `FAILED`, `PENDING_RETRY`).
- [ ] **AC-9.4**: Email dispatch is idempotent; re-triggering does not send duplicate emails for the same certificate.
- [ ] **AC-9.5**: Provider failure does not roll back certificate generation.

## Module 10: Institutional Admin & Audit
- [ ] **AC-10.1**: Admin dashboard displays real, un-fabricated completion counts, department breakdowns, and proctoring metrics.
- [ ] **AC-10.2**: Content provenance audit table displays all published resources with their source URLs.
- [ ] **AC-10.3**: All security-critical actions (revocation, grade override, role change) are logged in the `AuditLog` table.
