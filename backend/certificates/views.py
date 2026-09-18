import os
import uuid
from django.utils import timezone
from django.http import HttpResponse
from django.conf import settings
from rest_framework import views, status, permissions
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser

from .models import Certificate, CertificateVerification, BrandingAsset, CertificateConfig
from .pdf_service import CertificatePDFService
from notifications.email_service import EmailNotificationService
from learning.models import Enrollment
from catalogue.models import Course
from assessments.models import AssessmentAttempt
from audit.models import AuditLog


def get_certificate_branding_dict():
    """
    Returns the active institutional certificate configuration and branding asset URLs.
    """
    config = CertificateConfig.get_solo()
    horiz_asset = BrandingAsset.objects.filter(asset_type='HORIZONTAL_LOGO', status='ACTIVE').first()
    emblem_asset = BrandingAsset.objects.filter(asset_type='CIRCULAR_EMBLEM', status='ACTIVE').first()
    watermark_asset = BrandingAsset.objects.filter(asset_type='WATERMARK', status='ACTIVE').first()

    return {
        'institution_name': config.institution_name,
        'subtext': config.subtext,
        'accreditation_text': config.accreditation_text,
        'signatory_1_title': config.signatory_1_title,
        'signatory_1_name': config.signatory_1_name,
        'signatory_2_title': config.signatory_2_title,
        'signatory_2_name': config.signatory_2_name,
        'cert_id_prefix': config.cert_id_prefix,
        'watermark_enabled': config.watermark_enabled,
        'watermark_opacity': config.watermark_opacity,
        'horizontal_logo_url': horiz_asset.image.url if horiz_asset and horiz_asset.image else '/fxec_logo.png',
        'circular_emblem_url': emblem_asset.image.url if emblem_asset and emblem_asset.image else '/fxec_crest.png',
        'watermark_url': watermark_asset.image.url if watermark_asset and watermark_asset.image else '/fxec_crest.png',
    }


class PublicCertificateConfigView(views.APIView):
    """
    Public endpoint returning current active certificate configuration and branding asset URLs
    for student certificate rendering, public verification, and previews.
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        return Response(get_certificate_branding_dict())


class GenerateCertificateView(views.APIView):
    """
    Server-authoritative certificate generation endpoint.
    Verifies strict eligibility:
    1. Student enrolled in course
    2. Course status = COMPLETED (progress = 100%)
    3. All required syllabus modules completed
    4. Final assessment = PASSED
    5. Attempt not terminated for security violation or review invalidation
    Enforces idempotency — cannot generate duplicate certificates for the same enrollment.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        attempt_id = request.data.get('attempt_id')
        course_id = request.data.get('course_id')

        attempt = None
        course = None

        if attempt_id:
            try:
                attempt = AssessmentAttempt.objects.select_related('assessment', 'assessment__course').get(
                    id=attempt_id,
                    student=request.user
                )
                course = attempt.assessment.course
            except (AssessmentAttempt.DoesNotExist, ValueError):
                return Response({'error': 'Assessment attempt not found.'}, status=status.HTTP_404_NOT_FOUND)
        elif course_id:
            try:
                course = Course.objects.get(id=course_id)
                attempt = AssessmentAttempt.objects.filter(
                    assessment__course=course,
                    assessment__assessment_type='FINAL_ASSESSMENT',
                    student=request.user,
                    passed=True
                ).order_by('-submitted_at').first()
            except Course.DoesNotExist:
                return Response({'error': 'Course not found.'}, status=status.HTTP_404_NOT_FOUND)
        else:
            return Response({'error': 'attempt_id or course_id is required.'}, status=status.HTTP_400_BAD_REQUEST)

        # 1. Verify Enrollment
        try:
            enrollment = Enrollment.objects.get(student=request.user, course=course)
        except Enrollment.DoesNotExist:
            return Response({'error': 'Student is not enrolled in this course.'}, status=status.HTTP_400_BAD_REQUEST)

        # 2. Check Module Completion and 100% Progress
        enrollment.update_progress()
        eligible, progress, completed_req, total_req, reason = enrollment.is_assessment_eligible()
        if not eligible or progress < 100.0 or not enrollment.is_completed:
            return Response({
                'error': f"Course requirements not completed: All required modules must be 100% completed ({completed_req}/{total_req} modules completed, progress: {progress}%)."
            }, status=status.HTTP_400_BAD_REQUEST)

        # 3. Check Final Assessment Passed
        if not attempt or not attempt.passed:
            return Response({
                'error': 'Cannot issue certificate for an unpassed assessment: Final assessment must be passed.'
            }, status=status.HTTP_400_BAD_REQUEST)

        # 4. Check Security Violation / Invalidation Flags
        if attempt.status == 'TERMINATED_SECURITY_VIOLATION':
            return Response({
                'error': 'Certificate generation rejected: Assessment attempt was terminated due to critical security violation.'
            }, status=status.HTTP_403_FORBIDDEN)

        if attempt.review_status == 'INVALID':
            return Response({
                'error': 'Certificate generation rejected: Assessment attempt was invalidated during academic review.'
            }, status=status.HTTP_403_FORBIDDEN)

        # 5. Idempotency Check: return existing certificate if already issued
        existing_cert = Certificate.objects.filter(enrollment=enrollment).first()
        if existing_cert:
            return Response({
                'certificate_id': existing_cert.id,
                'certificate_number': existing_cert.certificate_number,
                'verification_url': existing_cert.qr_url,
                'issued_at': existing_cert.issued_at,
                'skill': existing_cert.skill,
                'assessment_score': existing_cert.assessment_score,
                'status': existing_cert.status,
                'is_revoked': existing_cert.is_revoked,
                'message': 'Certificate already exists for this completed enrollment.'
            })

        # 6. Generate Globally Unique Certificate Number
        config = CertificateConfig.get_solo()
        now = timezone.now()
        prefix = config.cert_id_prefix or "FXEC-SKILL"
        
        # Sequence counter per year
        seq_count = Certificate.objects.filter(issued_at__year=now.year).count() + 1
        cert_num = f"{prefix}-{now.year}-{seq_count:06d}"
        while Certificate.objects.filter(certificate_number=cert_num).exists():
            seq_count += 1
            cert_num = f"{prefix}-{now.year}-{seq_count:06d}"

        cert_id = uuid.uuid4()
        portal_base = getattr(settings, 'PUBLIC_PORTAL_URL', 'http://localhost:5173')
        qr_url = f"{portal_base}/verify/{cert_num}"

        integrity_hash = Certificate.generate_integrity_hash(
            cert_id=cert_id,
            student_username=request.user.username,
            course_title=course.title,
            issued_iso=now.isoformat()
        )

        skill_name = course.skill.name if getattr(course, 'skill', None) else course.title.split()[0]
        score_val = f"{int(attempt.percentage)} / 100"

        certificate = Certificate.objects.create(
            id=cert_id,
            enrollment=enrollment,
            student=request.user,
            course=course,
            certificate_number=cert_num,
            integrity_hash=integrity_hash,
            qr_url=qr_url,
            skill=skill_name,
            assessment_score=score_val,
            status='VALID',
            is_demo=getattr(request.user, 'is_demo', False)
        )

        # Trigger email with PDF attachment
        EmailNotificationService.send_certificate_notification(certificate)

        AuditLog.log_action(
            action='CERTIFICATE_ISSUED',
            resource_type='Certificate',
            resource_id=certificate.id,
            user=request.user,
            metadata={'certificate_number': cert_num, 'course': course.title, 'score': score_val}
        )

        return Response({
            'certificate_id': certificate.id,
            'certificate_number': certificate.certificate_number,
            'verification_url': certificate.qr_url,
            'integrity_hash': certificate.integrity_hash,
            'issued_at': certificate.issued_at,
            'skill': certificate.skill,
            'assessment_score': certificate.assessment_score,
            'status': certificate.status,
            'message': 'Certificate generated successfully.'
        }, status=status.HTTP_201_CREATED)


# Alias for backward compatibility with existing tests
IssueCertificateView = GenerateCertificateView


class DownloadCertificatePDFView(views.APIView):
    """
    Renders and streams the official PDF certificate.
    Supports lookup by UUID or certificate number.
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request, certificate_id):
        cert = None
        try:
            val_uuid = uuid.UUID(certificate_id)
            cert = Certificate.objects.select_related('student', 'course', 'course__department', 'course__skill').filter(id=val_uuid).first()
        except (ValueError, AttributeError):
            pass

        if not cert:
            cert = Certificate.objects.select_related('student', 'course', 'course__department', 'course__skill').filter(certificate_number__iexact=certificate_id).first()

        if not cert:
            return Response({'error': 'Certificate not found.'}, status=status.HTTP_404_NOT_FOUND)

        pdf_bytes = CertificatePDFService.render_pdf(cert)
        response = HttpResponse(pdf_bytes, content_type='application/pdf')
        filename = f"FXEC_Certificate_{cert.certificate_number}.pdf"
        response['Content-Disposition'] = f'inline; filename="{filename}"'
        return response


class CertificateQRCodeView(views.APIView):
    """
    Renders and streams the high-contrast QR code image for a certificate.
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request, certificate_id):
        cert = None
        try:
            val_uuid = uuid.UUID(certificate_id)
            cert = Certificate.objects.filter(id=val_uuid).first()
        except (ValueError, AttributeError):
            pass

        if not cert:
            cert = Certificate.objects.filter(certificate_number__iexact=certificate_id).first()

        if not cert:
            return Response({'error': 'Certificate not found.'}, status=status.HTTP_404_NOT_FOUND)

        qr_buf = CertificatePDFService.generate_qr_image(cert.qr_url)
        return HttpResponse(qr_buf.getvalue(), content_type='image/png')


class PublicVerifyCertificateView(views.APIView):
    """
    Public QR Verification Endpoint:
    Returns VALID, REVOKED, or NOT_FOUND.
    Records verification audit log.
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request, certificate_id):
        cert = None
        try:
            val_uuid = uuid.UUID(certificate_id)
            cert = Certificate.objects.select_related('student', 'course', 'course__department', 'course__skill').filter(id=val_uuid).first()
        except (ValueError, AttributeError):
            pass

        if not cert:
            cert = Certificate.objects.select_related('student', 'course', 'course__department', 'course__skill').filter(certificate_number__iexact=certificate_id).first()

        if not cert:
            return Response({
                'status': 'NOT_FOUND',
                'message': 'CERTIFICATE NOT FOUND: No certificate with this identifier exists in the institutional registry.'
            }, status=status.HTTP_404_NOT_FOUND)

        # Log verification request
        CertificateVerification.objects.create(
            certificate=cert,
            ip_address=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT', '')[:255]
        )

        dept_name = cert.course.department.name if cert.course.department else 'Institutional Skill Track'
        skill_name = cert.skill or (cert.course.skill.name if getattr(cert.course, 'skill', None) else cert.course.title.split()[0])

        if cert.is_revoked or cert.status == 'REVOKED':
            return Response({
                'status': 'REVOKED',
                'certificate_number': cert.certificate_number,
                'student_name': cert.student.get_full_name() or cert.student.username,
                'course_title': cert.course.title,
                'skill': skill_name,
                'revoked_at': cert.revoked_at,
                'revocation_reason': cert.revocation_reason or 'Administrative or academic council revocation',
                'institution': 'Francis Xavier Engineering College',
            })

        return Response({
            'status': 'VALID',
            'certificate_number': cert.certificate_number,
            'student_name': cert.student.get_full_name() or cert.student.username,
            'course_title': cert.course.title,
            'skill': skill_name,
            'score': cert.assessment_score or "Passed",
            'assessment_status': 'PASSED',
            'department': dept_name,
            'issued_at': cert.issued_at,
            'issue_date': cert.issued_at.strftime('%d %B %Y').upper(),
            'integrity_hash': cert.integrity_hash,
            'institution': 'Francis Xavier Engineering College',
            'is_demo': cert.is_demo,
        })


class UserCertificatesListView(views.APIView):
    """
    Returns list of certificates issued to the authenticated student.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        certs = Certificate.objects.filter(student=request.user).select_related('course', 'course__skill')
        data = [
            {
                'id': str(c.id),
                'certificate_number': c.certificate_number,
                'course_title': c.course.title,
                'course_slug': c.course.slug,
                'skill': c.skill or (c.course.skill.name if getattr(c.course, 'skill', None) else c.course.title.split()[0]),
                'score': c.assessment_score or "Passed",
                'issued_at': c.issued_at,
                'issue_date': c.issued_at.strftime('%d %B %Y').upper(),
                'status': c.status,
                'is_revoked': c.is_revoked,
                'integrity_hash': c.integrity_hash,
                'qr_url': c.qr_url,
            }
            for c in certs
        ]
        return Response(data)


# =====================================================================
# ADMIN CERTIFICATE & BRANDING ASSET MANAGEMENT ENDPOINTS
# =====================================================================

class AdminCertificateListView(views.APIView):
    """
    Admin: List and search all certificates across the institution.
    Search by certificate number, student name/username, course title, or status.
    """
    permission_classes = [permissions.IsAdminUser]

    def get(self, request):
        q = request.query_params.get('q', '').strip()
        certs = Certificate.objects.select_related('student', 'course', 'course__skill')
        if q:
            from django.db.models import Q
            certs = certs.filter(
                Q(certificate_number__icontains=q) |
                Q(student__username__icontains=q) |
                Q(student__first_name__icontains=q) |
                Q(student__last_name__icontains=q) |
                Q(course__title__icontains=q) |
                Q(status__iexact=q)
            )

        data = [
            {
                'id': str(c.id),
                'certificate_number': c.certificate_number,
                'student_name': c.student.get_full_name() or c.student.username,
                'student_username': c.student.username,
                'student_email': c.student.email,
                'course_title': c.course.title,
                'skill': c.skill or (c.course.skill.name if getattr(c.course, 'skill', None) else ''),
                'score': c.assessment_score,
                'status': c.status,
                'is_revoked': c.is_revoked,
                'revocation_reason': c.revocation_reason,
                'revoked_at': c.revoked_at,
                'issued_at': c.issued_at,
                'qr_url': c.qr_url,
            }
            for c in certs[:100]
        ]
        return Response(data)


class AdminRevokeCertificateView(views.APIView):
    """
    Admin: Invalidate / revoke an issued certificate. Immediately reflected on QR scan.
    """
    permission_classes = [permissions.IsAdminUser]

    def post(self, request, certificate_id):
        reason = request.data.get('reason', 'Administrative policy revocation by academic administration.')
        try:
            cert = Certificate.objects.get(id=certificate_id)
        except Certificate.DoesNotExist:
            return Response({'error': 'Certificate not found.'}, status=status.HTTP_404_NOT_FOUND)

        cert.is_revoked = True
        cert.status = 'REVOKED'
        cert.revocation_reason = reason
        cert.revoked_at = timezone.now()
        cert.revoked_by = request.user
        cert.save()

        AuditLog.log_action(
            action='CERTIFICATE_REVOKED',
            resource_type='Certificate',
            resource_id=cert.id,
            user=request.user,
            metadata={'certificate_number': cert.certificate_number, 'reason': reason}
        )

        return Response({
            'message': f"Certificate {cert.certificate_number} has been revoked.",
            'certificate_number': cert.certificate_number,
            'status': cert.status
        })


class AdminRestoreCertificateView(views.APIView):
    """
    Admin: Restore a previously revoked certificate.
    """
    permission_classes = [permissions.IsAdminUser]

    def post(self, request, certificate_id):
        try:
            cert = Certificate.objects.get(id=certificate_id)
        except Certificate.DoesNotExist:
            return Response({'error': 'Certificate not found.'}, status=status.HTTP_404_NOT_FOUND)

        cert.is_revoked = False
        cert.status = 'VALID'
        cert.revocation_reason = None
        cert.revoked_at = None
        cert.revoked_by = None
        cert.save()

        AuditLog.log_action(
            action='CERTIFICATE_RESTORED',
            resource_type='Certificate',
            resource_id=cert.id,
            user=request.user,
            metadata={'certificate_number': cert.certificate_number}
        )

        return Response({
            'message': f"Certificate {cert.certificate_number} restored to VALID.",
            'certificate_number': cert.certificate_number,
            'status': cert.status
        })


class AdminDeleteCertificateView(views.APIView):
    """
    Admin: Permanently delete a certificate record.
    """
    permission_classes = [permissions.IsAdminUser]

    def delete(self, request, certificate_id):
        try:
            cert = Certificate.objects.get(id=certificate_id)
        except Certificate.DoesNotExist:
            return Response({'error': 'Certificate not found.'}, status=status.HTTP_404_NOT_FOUND)

        cert_num = cert.certificate_number
        cert.delete()

        AuditLog.log_action(
            action='CERTIFICATE_DELETED',
            resource_type='Certificate',
            resource_id=str(certificate_id),
            user=request.user,
            metadata={'certificate_number': cert_num}
        )

        return Response({
            'message': f"Certificate {cert_num} has been permanently deleted.",
            'certificate_id': str(certificate_id)
        }, status=status.HTTP_200_OK)


class AdminRegenerateCertificateView(views.APIView):
    """
    Admin: Regenerate certificate PDF and refresh integrity hash.
    """
    permission_classes = [permissions.IsAdminUser]

    def post(self, request, certificate_id):
        try:
            cert = Certificate.objects.select_related('student', 'course').get(id=certificate_id)
        except Certificate.DoesNotExist:
            return Response({'error': 'Certificate not found.'}, status=status.HTTP_404_NOT_FOUND)

        # Refresh hash
        cert.integrity_hash = Certificate.generate_integrity_hash(
            cert_id=cert.id,
            student_username=cert.student.username,
            course_title=cert.course.title,
            issued_iso=cert.issued_at.isoformat()
        )
        cert.save(update_fields=['integrity_hash'])

        # Pre-render PDF
        CertificatePDFService.render_pdf(cert)

        AuditLog.log_action(
            action='CERTIFICATE_REGENERATED',
            resource_type='Certificate',
            resource_id=cert.id,
            user=request.user,
            metadata={'certificate_number': cert.certificate_number}
        )

        return Response({
            'message': f"Certificate {cert.certificate_number} successfully regenerated.",
            'integrity_hash': cert.integrity_hash
        })


class AdminBrandingView(views.APIView):
    """
    Admin: Retrieve branding assets and active versions.
    """
    permission_classes = [permissions.IsAdminUser]

    def get(self, request):
        assets = BrandingAsset.objects.all()
        data = [
            {
                'id': a.id,
                'asset_type': a.asset_type,
                'filename': a.filename or os.path.basename(a.image.name if a.image else ''),
                'version': a.version,
                'status': a.status,
                'image_url': a.image.url if a.image else None,
                'uploaded_by': a.uploaded_by.username if a.uploaded_by else 'System',
                'uploaded_at': a.uploaded_at,
            }
            for a in assets
        ]
        return Response(data)


class AdminBrandingUploadView(views.APIView):
    """
    Admin: Upload/replace an approved official branding asset.
    Asset types: HORIZONTAL_LOGO, CIRCULAR_EMBLEM, WATERMARK.
    Automatically archives previous version and marks new as ACTIVE.
    """
    permission_classes = [permissions.IsAdminUser]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        asset_type = request.data.get('asset_type')
        image_file = request.FILES.get('image')

        if not asset_type or asset_type not in ('HORIZONTAL_LOGO', 'CIRCULAR_EMBLEM', 'WATERMARK'):
            return Response({'error': 'Invalid asset_type. Must be HORIZONTAL_LOGO, CIRCULAR_EMBLEM, or WATERMARK.'}, status=status.HTTP_400_BAD_REQUEST)

        if not image_file:
            return Response({'error': 'image file is required.'}, status=status.HTTP_400_BAD_REQUEST)

        # Get latest version for this asset type
        latest = BrandingAsset.objects.filter(asset_type=asset_type).order_by('-version').first()
        next_version = (latest.version + 1) if latest else 1

        asset = BrandingAsset.objects.create(
            asset_type=asset_type,
            image=image_file,
            filename=image_file.name,
            version=next_version,
            status='ACTIVE',
            uploaded_by=request.user
        )

        AuditLog.log_action(
            action='BRANDING_ASSET_UPLOADED',
            resource_type='BrandingAsset',
            resource_id=asset.id,
            user=request.user,
            metadata={'asset_type': asset_type, 'version': next_version, 'filename': image_file.name}
        )

        return Response({
            'message': f"{asset.get_asset_type_display()} v{next_version} uploaded and activated.",
            'id': asset.id,
            'version': asset.version,
            'status': asset.status
        }, status=status.HTTP_201_CREATED)


class AdminCertificateConfigView(views.APIView):
    """
    Admin: View and update institutional certificate configuration fields.
    Allows configuring institution name, subtext, accreditation statements, and signatories without code changes.
    """
    permission_classes = [permissions.IsAdminUser]

    def get(self, request):
        config = CertificateConfig.get_solo()
        return Response({
            'institution_name': config.institution_name,
            'subtext': config.subtext,
            'accreditation_text': config.accreditation_text,
            'signatory_1_title': config.signatory_1_title,
            'signatory_1_name': config.signatory_1_name,
            'signatory_2_title': config.signatory_2_title,
            'signatory_2_name': config.signatory_2_name,
            'cert_id_prefix': config.cert_id_prefix,
            'watermark_enabled': config.watermark_enabled,
            'watermark_opacity': config.watermark_opacity,
            'updated_at': config.updated_at,
        })

    def post(self, request):
        config = CertificateConfig.get_solo()
        data = request.data

        if 'institution_name' in data:
            config.institution_name = data['institution_name']
        if 'subtext' in data:
            config.subtext = data['subtext']
        if 'accreditation_text' in data:
            config.accreditation_text = data['accreditation_text']
        if 'signatory_1_title' in data:
            config.signatory_1_title = data['signatory_1_title']
        if 'signatory_1_name' in data:
            config.signatory_1_name = data['signatory_1_name']
        if 'signatory_2_title' in data:
            config.signatory_2_title = data['signatory_2_title']
        if 'signatory_2_name' in data:
            config.signatory_2_name = data['signatory_2_name']
        if 'cert_id_prefix' in data:
            config.cert_id_prefix = data['cert_id_prefix']
        if 'watermark_enabled' in data:
            config.watermark_enabled = bool(data['watermark_enabled'])
        if 'watermark_opacity' in data:
            try:
                config.watermark_opacity = float(data['watermark_opacity'])
            except (ValueError, TypeError):
                pass

        config.save()

        AuditLog.log_action(
            action='CERTIFICATE_CONFIG_UPDATED',
            resource_type='CertificateConfig',
            resource_id=config.id,
            user=request.user,
            metadata={'institution_name': config.institution_name}
        )

        return Response({
            'message': 'Certificate configuration updated successfully.',
            'institution_name': config.institution_name
        })
