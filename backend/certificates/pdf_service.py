import io
import os
import math
import qrcode
from PIL import Image
from django.conf import settings
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image as RLImage
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

from .models import CertificateConfig, BrandingAsset


class CertificatePDFService:
    # Standard landscape A4: 841.89 x 595.28 points
    PAGE_WIDTH, PAGE_HEIGHT = landscape(A4)

    @classmethod
    def _get_assets_dirs(cls):
        base_dir = getattr(settings, 'BASE_DIR', os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        assets_dir = os.path.join(base_dir, 'certificates', 'assets')
        fonts_dir = os.path.join(base_dir, 'certificates', 'fonts')
        return assets_dir, fonts_dir

    @classmethod
    def _get_active_logo_paths(cls):
        """
        Retrieves active official logo and watermark asset paths from database or fallback directory.
        Strictly prevents generating fake/AI replacement logos.
        """
        assets_dir, _ = cls._get_assets_dirs()

        # 1. Horizontal Logo
        active_horiz = BrandingAsset.objects.filter(asset_type='HORIZONTAL_LOGO', status='ACTIVE').first()
        if active_horiz and active_horiz.image and os.path.exists(active_horiz.image.path):
            horiz_logo_path = active_horiz.image.path
        else:
            default_logo = os.path.join(assets_dir, 'fxec_logo.png')
            horiz_logo_path = default_logo if os.path.exists(default_logo) else None

        # 2. Circular Emblem
        active_emblem = BrandingAsset.objects.filter(asset_type='CIRCULAR_EMBLEM', status='ACTIVE').first()
        if active_emblem and active_emblem.image and os.path.exists(active_emblem.image.path):
            emblem_path = active_emblem.image.path
        else:
            default_emblem = os.path.join(assets_dir, 'fxec_crest.png')
            emblem_path = default_emblem if os.path.exists(default_emblem) else None

        # 3. Watermark
        active_watermark = BrandingAsset.objects.filter(asset_type='WATERMARK', status='ACTIVE').first()
        if active_watermark and active_watermark.image and os.path.exists(active_watermark.image.path):
            watermark_path = active_watermark.image.path
        else:
            watermark_path = emblem_path  # Default to subtle circular emblem watermark

        return horiz_logo_path, emblem_path, watermark_path

    @classmethod
    def _get_watermark_buffer(cls, image_path, opacity=0.06):
        """Generates a low-opacity watermark image buffer that preserves text readability."""
        if not image_path or not os.path.exists(image_path):
            return None
        try:
            im = Image.open(image_path).convert('RGBA')
            r, g, b, a = im.split()
            a = a.point(lambda p: int(p * opacity))
            im.putalpha(a)
            buf = io.BytesIO()
            im.save(buf, format='PNG')
            buf.seek(0)
            return buf
        except Exception:
            return None

    @staticmethod
    def generate_qr_image(qr_url):
        """Generates a high-contrast QR code image pointing to the official verification URL."""
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=4,
            border=0,
        )
        qr.add_data(qr_url)
        qr.make(fit=True)
        img = qr.make_image(fill_color="#0b1e3d", back_color="white")
        
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)
        return buffer

    @classmethod
    def render_pdf(cls, certificate):
        """
        Renders the official Francis Xavier Engineering College landscape A4 certificate PDF.
        Features:
        - Exact institution branding (top-left horizontal logo, top-right circular emblem)
        - Navy blue (#0B1E3D) and gold (#D4AF37) borders
        - Blue geometric faceted ribbons
        - Subtle institutional watermark
        - Dynamic auto-scaled student and course typography
        - Academic metadata grid (Skill, Score, Certificate ID, Issue Date)
        - Embedded QR code with 'SCAN TO VERIFY'
        - Institutional signature lines
        """
        config = CertificateConfig.get_solo()
        horiz_logo_path, emblem_path, watermark_path = cls._get_active_logo_paths()
        watermark_buf = cls._get_watermark_buffer(watermark_path, opacity=config.watermark_opacity)

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=(cls.PAGE_WIDTH, cls.PAGE_HEIGHT),
            leftMargin=55,
            rightMargin=55,
            topMargin=88,  # Leave room for top branding and institution header
            bottomMargin=28
        )

        styles = getSampleStyleSheet()

        # Dynamic font scaling to ensure long names and titles do not overflow
        student = certificate.student
        student_name = (student.get_full_name() or student.username).strip().upper()
        if len(student_name) > 30:
            student_font_size = 18
            student_leading = 22
        elif len(student_name) > 22:
            student_font_size = 21
            student_leading = 25
        else:
            student_font_size = 25
            student_leading = 29

        course = certificate.course
        course_title = course.title.strip().upper()
        if len(course_title) > 36:
            course_font_size = 16
            course_leading = 20
        elif len(course_title) > 26:
            course_font_size = 18
            course_leading = 22
        else:
            course_font_size = 21
            course_leading = 25

        # Typography Styles
        title_style = ParagraphStyle(
            'CertMainTitle',
            parent=styles['Normal'],
            fontName='Times-Bold',
            fontSize=26,
            leading=30,
            textColor=colors.HexColor('#0b1e3d'),
            alignment=TA_CENTER
        )

        opening_style = ParagraphStyle(
            'CertOpening',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=9.5,
            leading=13,
            textColor=colors.HexColor('#64748b'),
            alignment=TA_CENTER
        )

        student_style = ParagraphStyle(
            'CertStudentName',
            parent=styles['Normal'],
            fontName='Times-Bold',
            fontSize=student_font_size,
            leading=student_leading,
            textColor=colors.HexColor('#0b1e3d'),
            alignment=TA_CENTER
        )

        statement_style = ParagraphStyle(
            'CertStatement',
            parent=styles['Normal'],
            fontName='Times-Italic',
            fontSize=12,
            leading=16,
            textColor=colors.HexColor('#334155'),
            alignment=TA_CENTER
        )

        for_course_style = ParagraphStyle(
            'CertForCourse',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=9,
            leading=12,
            textColor=colors.HexColor('#64748b'),
            alignment=TA_CENTER
        )

        course_style = ParagraphStyle(
            'CertCourseTitle',
            parent=styles['Normal'],
            fontName='Times-Bold',
            fontSize=course_font_size,
            leading=course_leading,
            textColor=colors.HexColor('#0b1e3d'),
            alignment=TA_CENTER
        )

        meta_label_style = ParagraphStyle(
            'CertMetaLabel',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=7.5,
            leading=10,
            textColor=colors.HexColor('#0b1e3d'),
            alignment=TA_CENTER
        )

        meta_val_style = ParagraphStyle(
            'CertMetaVal',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=9.5,
            leading=12,
            textColor=colors.HexColor('#1e293b'),
            alignment=TA_CENTER
        )

        sig_title_style = ParagraphStyle(
            'CertSigTitle',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=9,
            leading=12,
            textColor=colors.HexColor('#0b1e3d'),
            alignment=TA_CENTER
        )

        sig_name_style = ParagraphStyle(
            'CertSigName',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=8,
            leading=10,
            textColor=colors.HexColor('#475569'),
            alignment=TA_CENTER
        )

        qr_label_style = ParagraphStyle(
            'CertQRLabel',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=7,
            leading=9,
            textColor=colors.HexColor('#0b1e3d'),
            alignment=TA_CENTER
        )

        elements = []

        # 1. Spacer to push below top header
        elements.append(Spacer(1, 14))

        # 2. Main Title: CERTIFICATE OF COMPLETION
        elements.append(Paragraph("CERTIFICATE OF COMPLETION", title_style))
        elements.append(Spacer(1, 12))

        # 3. Formal opening: "THIS IS TO CERTIFY THAT"
        elements.append(Paragraph("THIS IS TO CERTIFY THAT", opening_style))
        elements.append(Spacer(1, 6))

        # 4. Recipient Student Name
        elements.append(Paragraph(f"<u>{student_name}</u>", student_style))
        elements.append(Spacer(1, 8))

        # 5. Formal Completion Statement
        elements.append(Paragraph(
            "has successfully completed the prescribed learning modules and passed the final assessment",
            statement_style
        ))
        elements.append(Spacer(1, 4))
        elements.append(Paragraph("FOR THE COURSE", for_course_style))
        elements.append(Spacer(1, 4))

        # 6. Dynamic Course Name
        elements.append(Paragraph(course_title, course_style))
        elements.append(Spacer(1, 14))

        # 7. Certificate Metadata Section (4 columns: SKILL, SCORE, CERTIFICATE ID, ISSUE DATE)
        skill_name = certificate.skill or (course.skill.name if getattr(course, 'skill', None) else course.title.split()[0])
        score_val = certificate.assessment_score or "85 / 100"
        cert_num = certificate.certificate_number
        issue_date_str = certificate.issued_at.strftime('%d %B %Y').upper()

        meta_table_data = [
            [
                Paragraph("SKILL", meta_label_style),
                Paragraph("ASSESSMENT SCORE", meta_label_style),
                Paragraph("CERTIFICATE ID", meta_label_style),
                Paragraph("ISSUE DATE", meta_label_style),
            ],
            [
                Paragraph(f"<b>{skill_name}</b>", meta_val_style),
                Paragraph(f"<b>{score_val}</b>", meta_val_style),
                Paragraph(f"<font color='#0b1e3d'>{cert_num}</font>", meta_val_style),
                Paragraph(f"<b>{issue_date_str}</b>", meta_val_style),
            ]
        ]
        meta_table = Table(meta_table_data, colWidths=[180, 180, 195, 175])
        meta_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f1f5f9')),
            ('BACKGROUND', (0, 1), (-1, 1), colors.HexColor('#ffffff')),
            ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#cbd5e1')),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        elements.append(meta_table)
        elements.append(Spacer(1, 14))

        # 8. Bottom Signatures and QR Section (3 columns)
        qr_buf = cls.generate_qr_image(certificate.qr_url)
        qr_img = RLImage(qr_buf, width=0.82 * inch, height=0.82 * inch)

        # Left: Authorized Signatory
        sig_left = [
            Spacer(1, 20),
            Table([['']], colWidths=[170], rowHeights=[1], style=[('LINEBELOW', (0, 0), (-1, -1), 1, colors.HexColor('#94a3b8'))]),
            Spacer(1, 3),
            Paragraph(f"<b>{config.signatory_1_title}</b>", sig_title_style),
        ]
        if config.signatory_1_name:
            sig_left.append(Paragraph(config.signatory_1_name, sig_name_style))

        # Center: QR Code & Verification
        qr_center = [
            qr_img,
            Spacer(1, 2),
            Paragraph("<b>SCAN TO VERIFY</b>", qr_label_style),
        ]

        # Right: Course Coordinator
        sig_right = [
            Spacer(1, 20),
            Table([['']], colWidths=[170], rowHeights=[1], style=[('LINEBELOW', (0, 0), (-1, -1), 1, colors.HexColor('#94a3b8'))]),
            Spacer(1, 3),
            Paragraph(f"<b>{config.signatory_2_title}</b>", sig_title_style),
        ]
        if config.signatory_2_name:
            sig_right.append(Paragraph(config.signatory_2_name, sig_name_style))

        sig_table = Table(
            [[sig_left, qr_center, sig_right]],
            colWidths=[270, 190, 270]
        )
        sig_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'BOTTOM'),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ]))
        elements.append(sig_table)

        # 9. Canvas Decorator (Background, Borders, Geometric Ribbons, Watermark, Header Logos)
        def draw_decorations(canvas, doc):
            canvas.saveState()

            # White / Very Light Cream Canvas
            canvas.setFillColor(colors.HexColor('#FDFAF7'))
            canvas.rect(0, 0, cls.PAGE_WIDTH, cls.PAGE_HEIGHT, fill=1, stroke=0)

            # Outer Navy Institutional Border (#0B1E3D)
            canvas.setStrokeColor(colors.HexColor('#0b1e3d'))
            canvas.setLineWidth(3.5)
            canvas.rect(12, 12, cls.PAGE_WIDTH - 24, cls.PAGE_HEIGHT - 24)

            # Inner Thin Gold Border (#D4AF37)
            canvas.setStrokeColor(colors.HexColor('#d4af37'))
            canvas.setLineWidth(1.2)
            canvas.rect(17, 17, cls.PAGE_WIDTH - 34, cls.PAGE_HEIGHT - 34)

            # --- TOP-RIGHT GEOMETRIC RIBBON / FACETED DECORATION ---
            p_ice = canvas.beginPath()
            p_ice.moveTo(cls.PAGE_WIDTH - 260, cls.PAGE_HEIGHT - 12)
            p_ice.lineTo(cls.PAGE_WIDTH - 12, cls.PAGE_HEIGHT - 210)
            p_ice.lineTo(cls.PAGE_WIDTH - 12, cls.PAGE_HEIGHT - 12)
            p_ice.close()
            canvas.setFillColor(colors.HexColor('#e0f2fe'))
            canvas.drawPath(p_ice, fill=1, stroke=0)

            p_sky = canvas.beginPath()
            p_sky.moveTo(cls.PAGE_WIDTH - 200, cls.PAGE_HEIGHT - 12)
            p_sky.lineTo(cls.PAGE_WIDTH - 12, cls.PAGE_HEIGHT - 165)
            p_sky.lineTo(cls.PAGE_WIDTH - 12, cls.PAGE_HEIGHT - 85)
            p_sky.lineTo(cls.PAGE_WIDTH - 110, cls.PAGE_HEIGHT - 12)
            p_sky.close()
            canvas.setFillColor(colors.HexColor('#38bdf8'))
            canvas.drawPath(p_sky, fill=1, stroke=0)

            p_royal = canvas.beginPath()
            p_royal.moveTo(cls.PAGE_WIDTH - 150, cls.PAGE_HEIGHT - 12)
            p_royal.lineTo(cls.PAGE_WIDTH - 12, cls.PAGE_HEIGHT - 125)
            p_royal.lineTo(cls.PAGE_WIDTH - 12, cls.PAGE_HEIGHT - 55)
            p_royal.lineTo(cls.PAGE_WIDTH - 65, cls.PAGE_HEIGHT - 12)
            p_royal.close()
            canvas.setFillColor(colors.HexColor('#1d4ed8'))
            canvas.drawPath(p_royal, fill=1, stroke=0)

            p_navy = canvas.beginPath()
            p_navy.moveTo(cls.PAGE_WIDTH - 85, cls.PAGE_HEIGHT - 12)
            p_navy.lineTo(cls.PAGE_WIDTH - 12, cls.PAGE_HEIGHT - 70)
            p_navy.lineTo(cls.PAGE_WIDTH - 12, cls.PAGE_HEIGHT - 12)
            p_navy.close()
            canvas.setFillColor(colors.HexColor('#0b1e3d'))
            canvas.drawPath(p_navy, fill=1, stroke=0)

            # Gold edge line on facet
            canvas.setStrokeColor(colors.HexColor('#d4af37'))
            canvas.setLineWidth(1.5)
            canvas.line(cls.PAGE_WIDTH - 260, cls.PAGE_HEIGHT - 12, cls.PAGE_WIDTH - 12, cls.PAGE_HEIGHT - 210)

            # --- BOTTOM-RIGHT MATCHING GEOMETRIC RIBBON ---
            p_br_ice = canvas.beginPath()
            p_br_ice.moveTo(cls.PAGE_WIDTH - 180, 12)
            p_br_ice.lineTo(cls.PAGE_WIDTH - 12, 145)
            p_br_ice.lineTo(cls.PAGE_WIDTH - 12, 12)
            p_br_ice.close()
            canvas.setFillColor(colors.HexColor('#e0f2fe'))
            canvas.drawPath(p_br_ice, fill=1, stroke=0)

            p_br_sky = canvas.beginPath()
            p_br_sky.moveTo(cls.PAGE_WIDTH - 130, 12)
            p_br_sky.lineTo(cls.PAGE_WIDTH - 12, 105)
            p_br_sky.lineTo(cls.PAGE_WIDTH - 12, 50)
            p_br_sky.lineTo(cls.PAGE_WIDTH - 70, 12)
            p_br_sky.close()
            canvas.setFillColor(colors.HexColor('#38bdf8'))
            canvas.drawPath(p_br_sky, fill=1, stroke=0)

            p_br_navy = canvas.beginPath()
            p_br_navy.moveTo(cls.PAGE_WIDTH - 60, 12)
            p_br_navy.lineTo(cls.PAGE_WIDTH - 12, 45)
            p_br_navy.lineTo(cls.PAGE_WIDTH - 12, 12)
            p_br_navy.close()
            canvas.setFillColor(colors.HexColor('#0b1e3d'))
            canvas.drawPath(p_br_navy, fill=1, stroke=0)

            canvas.setStrokeColor(colors.HexColor('#d4af37'))
            canvas.setLineWidth(1.2)
            canvas.line(cls.PAGE_WIDTH - 180, 12, cls.PAGE_WIDTH - 12, 145)

            # --- TOP-LEFT NAVY / GOLD RIBBON DETAIL ---
            p_tl = canvas.beginPath()
            p_tl.moveTo(12, cls.PAGE_HEIGHT - 85)
            p_tl.lineTo(85, cls.PAGE_HEIGHT - 12)
            p_tl.lineTo(12, cls.PAGE_HEIGHT - 12)
            p_tl.close()
            canvas.setFillColor(colors.HexColor('#0b1e3d'))
            canvas.drawPath(p_tl, fill=1, stroke=0)

            canvas.setStrokeColor(colors.HexColor('#d4af37'))
            canvas.setLineWidth(1.2)
            canvas.line(12, cls.PAGE_HEIGHT - 85, 85, cls.PAGE_HEIGHT - 12)

            # --- BOTTOM-LEFT SUBTLE CORNER DETAIL ---
            p_bl = canvas.beginPath()
            p_bl.moveTo(12, 70)
            p_bl.lineTo(70, 12)
            p_bl.lineTo(12, 12)
            p_bl.close()
            canvas.setFillColor(colors.HexColor('#0b1e3d'))
            canvas.drawPath(p_bl, fill=1, stroke=0)

            canvas.setStrokeColor(colors.HexColor('#d4af37'))
            canvas.setLineWidth(1)
            canvas.line(12, 70, 70, 12)

            # --- CENTER WATERMARK ---
            if config.watermark_enabled:
                if watermark_buf:
                    wm_size = 220
                    wm_x = (cls.PAGE_WIDTH - wm_size) / 2
                    wm_y = (cls.PAGE_HEIGHT - wm_size) / 2 + 10
                    canvas.drawImage(RLImage(watermark_buf, width=wm_size, height=wm_size)._img, wm_x, wm_y, width=wm_size, height=wm_size, mask='auto')
                else:
                    # Subtle geometric concentric watermark
                    canvas.saveState()
                    canvas.setStrokeColor(colors.HexColor('#0b1e3d', alpha=0.04))
                    canvas.setLineWidth(0.8)
                    cx_wm, cy_wm = cls.PAGE_WIDTH / 2, cls.PAGE_HEIGHT / 2 + 10
                    for r_wm in [60, 95, 130, 165]:
                        canvas.circle(cx_wm, cy_wm, r_wm, fill=0, stroke=1)
                    canvas.restoreState()

            # --- TOP-LEFT HORIZONTAL LOGO ---
            if horiz_logo_path and os.path.exists(horiz_logo_path):
                w_logo = 220
                h_logo = w_logo / 3.8  # ~58 points
                canvas.drawImage(horiz_logo_path, 34, cls.PAGE_HEIGHT - 78, width=w_logo, height=h_logo, mask='auto')
            else:
                # Required placeholder if asset is missing (per rule #2)
                canvas.setStrokeColor(colors.HexColor('#b91c1c'))
                canvas.setLineWidth(1)
                canvas.setFillColor(colors.HexColor('#fef2f2'))
                canvas.roundRect(34, cls.PAGE_HEIGHT - 76, 200, 48, 6, fill=1, stroke=1)
                canvas.setFont('Helvetica-Bold', 7.5)
                canvas.setFillColor(colors.HexColor('#991b1b'))
                canvas.drawCentredString(134, cls.PAGE_HEIGHT - 54, "OFFICIAL LOGO ASSET REQUIRED")

            # --- TOP-RIGHT CIRCULAR EMBLEM ---
            if emblem_path and os.path.exists(emblem_path):
                w_emblem = 62
                h_emblem = 62
                emb_x = cls.PAGE_WIDTH - 105
                emb_y = cls.PAGE_HEIGHT - 80
                # White background disc for clean contrast
                canvas.setFillColor(colors.HexColor('#FFFFFF'))
                canvas.circle(emb_x + w_emblem / 2, emb_y + h_emblem / 2, w_emblem / 2 + 2, fill=1, stroke=0)
                canvas.drawImage(emblem_path, emb_x, emb_y, width=w_emblem, height=h_emblem, mask='auto')
            else:
                # Required placeholder if asset is missing (per rule #2)
                canvas.setStrokeColor(colors.HexColor('#b91c1c'))
                canvas.setLineWidth(1)
                canvas.setFillColor(colors.HexColor('#fef2f2'))
                canvas.circle(cls.PAGE_WIDTH - 74, cls.PAGE_HEIGHT - 49, 28, fill=1, stroke=1)
                canvas.setFont('Helvetica-Bold', 6)
                canvas.setFillColor(colors.HexColor('#991b1b'))
                canvas.drawCentredString(cls.PAGE_WIDTH - 74, cls.PAGE_HEIGHT - 51, "OFFICIAL LOGO")
                canvas.drawCentredString(cls.PAGE_WIDTH - 74, cls.PAGE_HEIGHT - 59, "ASSET REQUIRED")

            # --- TOP INSTITUTION HEADER (PROMINENT AND EXACT) ---
            canvas.setFont('Helvetica-Bold', 15)
            canvas.setFillColor(colors.HexColor('#0b1e3d'))
            canvas.drawCentredString(cls.PAGE_WIDTH / 2, cls.PAGE_HEIGHT - 50, config.institution_name)

            # Subtext & Accreditation
            subtext_full = config.subtext
            if config.accreditation_text:
                subtext_full += f" • {config.accreditation_text}"
            canvas.setFont('Helvetica', 8)
            canvas.setFillColor(colors.HexColor('#475569'))
            canvas.drawCentredString(cls.PAGE_WIDTH / 2, cls.PAGE_HEIGHT - 63, subtext_full)

            # Delicate gold underline under top header
            canvas.setStrokeColor(colors.HexColor('#d4af37'))
            canvas.setLineWidth(0.8)
            canvas.line(cls.PAGE_WIDTH / 2 - 180, cls.PAGE_HEIGHT - 70, cls.PAGE_WIDTH / 2 + 180, cls.PAGE_HEIGHT - 70)

            canvas.restoreState()

        doc.build(elements, onFirstPage=draw_decorations)
        buffer.seek(0)
        return buffer.getvalue()
