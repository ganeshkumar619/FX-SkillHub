# FX SkillHub — Product Requirements Document (PRD)

## 1. Product Identity & Purpose
- **System Name**: `FX SkillHub`
- **Expanded Title**: `FX SkillHub — AI-Powered Skill Learning, Secure Assessment and Digital Certification Platform`
- **Institution**: Francis Xavier Engineering College (Autonomous), Tirunelveli-627003, Tamil Nadu, India.
- **Objective**: Deliver an institutional learning and skill certification platform integrating source-provenance learning paths, transparent AI skill-gap diagnosis, secure multi-signal proctoring controls, tamper-evident digital certificate generation with live QR verification, and automated email delivery.

---

## 2. User Roles & Personas

### 2.1 Student
- **Identity**: Enrolled undergraduate/postgraduate student of FXEC.
- **Key Capabilities**:
  - Authenticate securely via college credentials / email session.
  - Browse public and department-specific skill catalogue with traceable institutional provenance.
  - Complete pre-assessments for transparent skill gap analysis.
  - View personalized, grounded learning recommendations (weak topic → mapped module).
  - Enroll in courses and navigate sequential learning modules (videos, reading material, practice questions).
  - Track real-time course completion and module mastery.
  - Undertake secure final assessments with layered browser proctoring checks (camera, screen, fullscreen, visibility).
  - Review assessment outcomes (score, pass/fail status, topic mastery).
  - Download official FXEC digital completion certificates with cryptographic verification hash and QR code.
  - Inspect public credential verification link.

### 2.2 Mentor
- **Identity**: Faculty member or department skill coordinator.
- **Key Capabilities**:
  - Manage owned skill courses, modules, and learning resources with mandatory provenance tags.
  - Maintain versioned question banks (multiple-choice, multi-select, difficulty, marks, explanations).
  - Author and publish assessments with configurable duration, pass percentage, attempt limits, and randomized pools.
  - Preview assessments in safe mentor simulation mode before publishing.
  - Monitor cohort progress and real-time learner completion metrics.
  - Access the **Proctoring Review Queue** to inspect flagged assessment attempts with event timelines and risk score breakdowns.
  - Render human verdicts on flagged attempts: `VALID`, `WARNING`, `INVALID`, `NEEDS_MORE_REVIEW` with auditable remarks.

### 2.3 Administrator
- **Identity**: Institutional administrator (Dean of Academics / Head of Training & Skills Development).
- **Key Capabilities**:
  - Manage departments, academic tracks, faculty roles, and student records.
  - Audit content provenance across all skills and courses.
  - Configure proctoring sensitivity weights and policy thresholds (e.g. fullscreen exit tolerance, tab switch penalty).
  - Manage digital certificate lifecycle, including search by certificate ID, issuance audit, and cryptographically recorded revocations.
  - Inspect near-real-time email dispatch logs, delivery failures, and retry queues.
  - Access institutional analytics (real completion rates, department engagement, skill distribution) without synthetic padding.
  - Review immutable system audit logs.

---

## 3. Core Functional Requirements

### 3.1 Course & Skill Catalogue Management
- Hierarchical structure: Department → Skill Category (Foundation, Mandatory, Value Added, Placement Fit) → Skill Course → Modules → Learning Resources.
- Every resource must record: `source_url`, `source_title`, `source_type`, `source_accessed_at`, `content_status`.
- Filter and search by department, skill level (Beginner, Intermediate, Advanced), and category.

### 3.2 AI Skill-Gap Analysis & Recommendation Engine
- **Pre-assessment**: Diagnostic quiz assessing topic-level competency.
- **Deterministic Topic Mastery**: Calculate percentage score per topic based strictly on correct answers.
- **Weakness Identification**: Flag topics scoring below threshold (< 70%).
- **Module Mapping**: Query database for published modules mapped to weak topics.
- **Transparent Recommendation**: Provide clear explanation with mapped module citations.
- **Deterministic Fallback**: If AI service is offline or unconfigured, the system continues to produce accurate rule-based recommendations without interruption.

### 3.3 Secure Assessment Runtime & Proctoring Engine
- **Preflight Checks**:
  1. Security notice and privacy disclosure acceptance.
  2. Camera permission and video stream capability verification.
  3. Screen-share permission check (`getDisplayMedia`).
  4. Fullscreen lock request.
  5. System compatibility & connection latency check.
- **Runtime Integrity Controls**:
  - Server-authoritative timer (client cannot tamper with exam duration).
  - Question and option randomization per attempt.
  - Autosave of answer choices upon selection.
  - Prevention of concurrent sessions for the same student attempt.
  - Continuous event tracking:
    - `TAB_SWITCH` (Page Visibility API)
    - `FULLSCREEN_EXIT` (Fullscreen API)
    - `CAMERA_DISCONNECTED` (MediaStream track ended)
    - `SCREEN_SHARE_STOPPED` (DisplayMedia track ended)
  - Configurable risk score computation based on event weights.
  - Auto-submission upon server timer expiration.
  - Non-accusatory labeling: `NORMAL`, `LOW`, `MEDIUM`, `HIGH`, `CRITICAL`.
  - Human review required for high-risk determinations.

### 3.4 Certificate Generation & QR Verification
- Server-side PDF generation styled with institutional typography and FXEC official identity.
- Contents:
  - College Name: Francis Xavier Engineering College (Autonomous)
  - Student Display Name
  - Course Title & Skill Track
  - Completion Date & Unique Certificate UUID
  - Verification QR Code containing direct public URL
  - Verification Hash (SHA-256 integrity digest)
- Public Verification Endpoint:
  - Route: `/verify-certificate/:certificate_id`
  - Returns live status: `VALID`, `REVOKED`, or `NOT_FOUND`.
  - Displays student name, course, completion date, and issuing authority.
- Revocation workflow: Authorized admin revocation stores reason, revoked timestamp, and admin ID.

### 3.5 Automated Notification & Email Delivery
- Asynchronous notification dispatch upon passing score evaluation.
- HTML email template featuring institutional styling, achievement summary, unique credential ID, and verification link.
- Delivery status tracking (`SENT`, `FAILED`, `PENDING_RETRY`) with retry-safe idempotency.

---

## 4. Non-Functional & Security Requirements
- **Role-Based Access Control (RBAC)**: Server-side route and API authorization guards on every endpoint.
- **OWASP Top 10 Compliance**: Parameterized queries, CSRF protection, secure cookie handling, CORS whitelist, strict input validation.
- **Privacy First**: Assessment media streams are analyzed locally in the browser runtime; no unnecessary continuous video recording is stored unless explicitly required by institutional policy.
- **Browser Compatibility**: Fully tested and responsive on modern desktop browsers (Chrome, Edge, Firefox).
