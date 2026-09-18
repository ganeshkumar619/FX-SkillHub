# FX SkillHub — Data Provenance & Real-Data Policy

## 1. Fundamental Principle
**Never fabricate institutional facts, departments, courses, achievements, faculty names, statistics, logos, addresses, placement numbers, course hours, certificates, or student records.**

FX SkillHub is an institutional enterprise platform designed for Francis Xavier Engineering College (FXEC). Every record in the database must possess verifiable origin and provenance.

---

## 2. Provenance Taxonomy & Metadata Schema

Every published skill, course, module, learning resource, assessment, and institution record in the database must track provenance attributes:

```sql
source_type VARCHAR(32) NOT NULL, 
-- Valid values:
-- 'FXEC_OFFICIAL'     : Direct fact extracted from official FXEC public portals / documents
-- 'NPTEL_OFFICIAL'    : MHRD/IIT Madras NPTEL public academic resources
-- 'EXTERNAL_PUBLIC'   : Publicly accessible educational reference (lawfully linked)
-- 'ADMIN_CREATED'     : Authorized mentor/administrator institutional submission

source_url TEXT NULL,                 -- Canonical URL where fact was retrieved
source_title VARCHAR(255) NULL,       -- Title of authoritative webpage or document
source_accessed_at TIMESTAMPTZ NULL,  -- Timestamp when source was inspected
last_verified_at TIMESTAMPTZ NULL,    -- Timestamp of latest verification check
content_status VARCHAR(32) NOT NULL DEFAULT 'DRAFT'
-- 'DRAFT'                : Work in progress
-- 'PENDING_ADMIN_INPUT'  : Awaiting verified institutional details
-- 'PUBLISHED'            : Verified and available for learners
```

---

## 3. Handling Unverified or Missing Data

1. **Strict Non-Fabrication**: If a detail is missing (such as custom faculty bios, specific contact extensions, or signature scans), do NOT invent placeholders like "John Doe" or dummy contact numbers.
2. **Neutral UI States**: Display honest, neutral empty states:
   - *"Not yet published by college administration"*
   - *"Pending verified syllabus update"*
3. **Admin Input Gateways**: Provide clear administrative controls allowing verified FXEC mentors and administrators to upload official documentation, syllabus outlines, and institutional credentials.

---

## 4. Demo Data vs. Production Data Policy

1. **Synthetic Demo Tagging**: Any test account or test assessment created during development or for expo demonstration must be explicitly flagged with `is_demo=True` or `environment='DEMO'`.
2. **Exclusion from Analytics**: Real institutional dashboards, pass rates, and completion statistics strictly filter out `is_demo=True` records.
3. **Golden Demo Constraints**: The demonstration setup shall feature:
   - 1 Demo Student (`demo.student@fxec.ac.in`)
   - 1 Demo Mentor (`demo.mentor@fxec.ac.in`)
   - 1 Demo Administrator (`demo.admin@fxec.ac.in`)
   - Verified FXEC departments (CSE, AI&DS, ECE, EEE, MECH, IT, etc.)
   - Real, demonstrable skill courses backed by official NPTEL/open curriculum links.

---

## 5. Copyright & Public Content Embedding

- External instructional videos or PDFs (e.g. from NPTEL or open educational repositories) are linked or embedded using standard, lawful web standards (`<iframe>` embed, canonical link).
- No copyrighted third-party learning materials are copied into the database or claimed as FXEC intellectual property.
