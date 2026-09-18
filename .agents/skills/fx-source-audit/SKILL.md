---
name: fx-source-audit
description: Verify institutional facts and maintain provenance for FX SkillHub.
---

# FX Source Audit Skill

## Purpose
Ensure that every piece of institutional metadata (departments, programs, achievements, contacts, accreditation, training pillars) traces directly to an official FXEC source or an authorized administrator entry.

## Protocol
1. Check `docs/source-registry.md` before adding any new institution-specific information.
2. If the fact originates from FXEC:
   - Record `source_url`
   - Record `source_title`
   - Record `source_accessed_at`
   - Tag with `source_type = 'FXEC_OFFICIAL'`
3. If the fact originates from NPTEL or a recognized public syllabus:
   - Tag with `source_type = 'NPTEL_OFFICIAL'` or `'EXTERNAL_PUBLIC'`
4. If no authoritative source is available:
   - Mark field as `PENDING_ADMIN_INPUT`
   - Display a clean neutral empty state in UI ("Pending administrative verification")
   - Do NOT invent fake phone numbers, emails, faculty titles, or enrollment counts.
