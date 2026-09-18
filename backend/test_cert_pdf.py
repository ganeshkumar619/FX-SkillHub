import os
import io
import math
import qrcode
from PIL import Image
import pymupdf

from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image as RLImage
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# Base directories
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FONT_DIR = os.path.join(BASE_DIR, 'certificates', 'fonts')
ASSETS_DIR = os.path.join(BASE_DIR, 'certificates', 'assets')

# Register OldEnglish font
font_oldengl = os.path.join(FONT_DIR, 'OLDENGL.TTF')
if os.path.exists(font_oldengl):
    try:
        pdfmetrics.registerFont(TTFont('OldEnglish', font_oldengl))
        CERT_FONT = 'OldEnglish'
    except Exception:
        CERT_FONT = 'Times-BoldItalic'
else:
    CERT_FONT = 'Times-BoldItalic'

def generate_sample_pdf(output_pdf_path):
    PAGE_WIDTH, PAGE_HEIGHT = landscape(letter) # 792 x 612

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=(PAGE_WIDTH, PAGE_HEIGHT),
        leftMargin=60,
        rightMargin=60,
        topMargin=35,
        bottomMargin=25
    )

    styles = getSampleStyleSheet()

    dept_style = ParagraphStyle(
        'DeptTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=15,
        leading=18,
        textColor=colors.HexColor('#1e293b'),
        alignment=TA_CENTER
    )

    body_style = ParagraphStyle(
        'CertBody',
        parent=styles['Normal'],
        fontName='Times-Italic',
        fontSize=13,
        leading=24,
        textColor=colors.HexColor('#334155'),
        alignment=TA_CENTER
    )

    sig_title_style = ParagraphStyle(
        'SigTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=9.5,
        leading=12,
        textColor=colors.HexColor('#0f172a'),
        alignment=TA_CENTER
    )

    sig_dept_style = ParagraphStyle(
        'SigDept',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor('#64748b'),
        alignment=TA_CENTER
    )

    meta_code_style = ParagraphStyle(
        'MetaCode',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=6.5,
        leading=8.5,
        textColor=colors.HexColor('#64748b'),
        alignment=TA_CENTER
    )

    elements = []

    # 1. Spacer to push below top header logos & department name
    elements.append(Spacer(1, 98))

    # 2. Department Title
    dept_name = "Department of Electrical and Electronics Engineering"
    elements.append(Paragraph(dept_name, dept_style))
    
    # 3. Spacer for the "Certificate" capsule ornament (drawn on canvas)
    elements.append(Spacer(1, 62))

    # 4. Body text with authentic dotted/underlined dynamic fields
    student_name = "GANESH KUMAR"
    year_str = "I YEAR"
    branch_str = "CSE"
    event_str = "ELITE - PROJECT EXPO"
    date_str = "06.03.2026"

    body_html = (
        f"<i>This is to certify that Mr. / Ms. </i> "
        f"<b><u>&nbsp; {student_name} &nbsp;</u></b> , "
        f"<b><u>&nbsp; {year_str} &nbsp;</u></b> ,<br/>"
        f"<b><u>&nbsp; {branch_str} &nbsp;</u></b> , <b><u>&nbsp; FXEC (Team: CODE SINS) &nbsp;</u></b> "
        f"<i>has participated / won </i> <b><u>&nbsp; 1st &nbsp;</u></b> <i>place in the event </i> "
        f"<b><u>&nbsp; {event_str} &nbsp;</u></b><br/>"
        f"<i>organised by {dept_name}, Francis Xavier Engineering College on </i> "
        f"<b><u>&nbsp; {date_str} &nbsp;</u></b>."
    )
    elements.append(Paragraph(body_html, body_style))
    elements.append(Spacer(1, 35))

    # 5. Bottom Signatures and QR Code
    qr = qrcode.QRCode(version=1, box_size=3, border=0)
    qr.add_data("http://localhost:5173/verify-certificate/008c6b48-76f7-4b4c-a94b-4afaeddb2a50")
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color="#0f2347", back_color="white")
    qr_buf = io.BytesIO()
    qr_img.save(qr_buf, format='PNG')
    qr_buf.seek(0)
    qr_reportlab = RLImage(qr_buf, width=0.8*inch, height=0.8*inch)

    # Signature blocks
    sig1_content = [
        Paragraph("<b>Co-ordinator - <font size=8.5>For ELITE</font></b>", sig_title_style),
        Paragraph("Dept. of EEE", sig_dept_style),
    ]

    center_verify = [
        qr_reportlab,
        Spacer(1, 2),
        Paragraph("<b>ID:</b> FXEC-SKILL-202603-A8F19C20", meta_code_style),
        Paragraph("<b>SHA-256:</b> e3b0c44298fc1c149afb96431702... [Valid]", meta_code_style),
    ]

    sig2_content = [
        Paragraph("<b>HOD</b>", sig_title_style),
        Paragraph("Dept. of EEE", sig_dept_style),
    ]

    sig_table = Table(
        [[sig1_content, center_verify, sig2_content]],
        colWidths=[2.5*inch, 2.8*inch, 2.5*inch]
    )
    sig_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'BOTTOM'),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
    ]))
    elements.append(sig_table)

    def draw_decorations(canvas, doc):
        canvas.saveState()

        # 1. Clean Crisp White Canvas Background
        canvas.setFillColor(colors.HexColor('#FFFFFF'))
        canvas.rect(0, 0, PAGE_WIDTH, PAGE_HEIGHT, fill=1, stroke=0)

        # ---------------------------------------------------------------------
        # 2. TOP-RIGHT GEOMETRIC SHAPES
        # ---------------------------------------------------------------------
        # Top-right Pale Ice Blue Facet
        p_ice = canvas.beginPath()
        p_ice.moveTo(PAGE_WIDTH - 260, PAGE_HEIGHT)
        p_ice.lineTo(PAGE_WIDTH, PAGE_HEIGHT - 220)
        p_ice.lineTo(PAGE_WIDTH, PAGE_HEIGHT)
        p_ice.close()
        canvas.setFillColor(colors.HexColor('#e0f2fe'))
        canvas.drawPath(p_ice, fill=1, stroke=0)

        # Top-right Sky Blue Facet
        p_sky = canvas.beginPath()
        p_sky.moveTo(PAGE_WIDTH - 200, PAGE_HEIGHT)
        p_sky.lineTo(PAGE_WIDTH, PAGE_HEIGHT - 175)
        p_sky.lineTo(PAGE_WIDTH, PAGE_HEIGHT - 90)
        p_sky.lineTo(PAGE_WIDTH - 120, PAGE_HEIGHT)
        p_sky.close()
        canvas.setFillColor(colors.HexColor('#38bdf8'))
        canvas.drawPath(p_sky, fill=1, stroke=0)

        # Top-right Royal Blue Facet
        p_royal = canvas.beginPath()
        p_royal.moveTo(PAGE_WIDTH - 150, PAGE_HEIGHT)
        p_royal.lineTo(PAGE_WIDTH, PAGE_HEIGHT - 135)
        p_royal.lineTo(PAGE_WIDTH, PAGE_HEIGHT - 60)
        p_royal.lineTo(PAGE_WIDTH - 70, PAGE_HEIGHT)
        p_royal.close()
        canvas.setFillColor(colors.HexColor('#1d4ed8'))
        canvas.drawPath(p_royal, fill=1, stroke=0)

        # Top-right Dark Navy Corner
        p_navy = canvas.beginPath()
        p_navy.moveTo(PAGE_WIDTH - 90, PAGE_HEIGHT)
        p_navy.lineTo(PAGE_WIDTH, PAGE_HEIGHT - 80)
        p_navy.lineTo(PAGE_WIDTH, PAGE_HEIGHT)
        p_navy.close()
        canvas.setFillColor(colors.HexColor('#0b2247'))
        canvas.drawPath(p_navy, fill=1, stroke=0)

        # Right Edge Vibrant Orange Accent Curved Shape
        p_orange_r = canvas.beginPath()
        p_orange_r.moveTo(PAGE_WIDTH, PAGE_HEIGHT * 0.58)
        p_orange_r.curveTo(
            PAGE_WIDTH - 30, PAGE_HEIGHT * 0.54,
            PAGE_WIDTH - 30, PAGE_HEIGHT * 0.44,
            PAGE_WIDTH, PAGE_HEIGHT * 0.40
        )
        p_orange_r.close()
        canvas.setFillColor(colors.HexColor('#ea580c'))
        canvas.drawPath(p_orange_r, fill=1, stroke=0)

        # ---------------------------------------------------------------------
        # 3. TOP-LEFT SUBTLE ACCENT
        # ---------------------------------------------------------------------
        p_tl = canvas.beginPath()
        p_tl.moveTo(0, PAGE_HEIGHT)
        p_tl.lineTo(150, PAGE_HEIGHT)
        p_tl.lineTo(0, PAGE_HEIGHT - 110)
        p_tl.close()
        canvas.setFillColor(colors.HexColor('#f0f9ff'))
        canvas.drawPath(p_tl, fill=1, stroke=0)

        # ---------------------------------------------------------------------
        # 4. BOTTOM-LEFT GEOMETRIC DIAMONDS & ACCENTS
        # ---------------------------------------------------------------------
        # Left Orange Edge Accent
        p_orange_l = canvas.beginPath()
        p_orange_l.moveTo(0, 270)
        p_orange_l.curveTo(
            25, 240,
            25, 195,
            0, 165
        )
        p_orange_l.close()
        canvas.setFillColor(colors.HexColor('#ea580c'))
        canvas.drawPath(p_orange_l, fill=1, stroke=0)

        # Tilted rounded diamond helper
        def draw_tilted_rounded_diamond(cx, cy, size, corner_r, color_hex):
            canvas.saveState()
            canvas.translate(cx, cy)
            canvas.rotate(45)
            canvas.setFillColor(colors.HexColor(color_hex))
            canvas.roundRect(-size/2, -size/2, size, size, corner_r, fill=1, stroke=0)
            canvas.restoreState()

        # Stacked diamonds (matching photo)
        # 1. Sky Blue Diamond (low-right)
        draw_tilted_rounded_diamond(125, 95, 95, 16, '#38bdf8')
        # 2. Medium Slate/Navy Diamond (mid)
        draw_tilted_rounded_diamond(95, 125, 115, 20, '#334155')
        # 3. Dark Charcoal / Deep Navy Diamond (front)
        draw_tilted_rounded_diamond(65, 155, 130, 22, '#1e293b')

        # ---------------------------------------------------------------------
        # 5. SILVER ACHIEVEMENT SEAL (Bottom-Left)
        # ---------------------------------------------------------------------
        seal_path = os.path.join(ASSETS_DIR, 'achievement_seal.png')
        if os.path.exists(seal_path):
            canvas.drawImage(seal_path, 28, 28, width=105, height=105, mask='auto')

        # ---------------------------------------------------------------------
        # 6. LOGOS
        # ---------------------------------------------------------------------
        # Top-Left: Francis Xavier Engineering College Banner Logo
        logo_path = os.path.join(ASSETS_DIR, 'fxec_logo.png')
        if os.path.exists(logo_path):
            w_logo = 240
            h_logo = w_logo / 3.8016
            canvas.drawImage(logo_path, 32, PAGE_HEIGHT - 84, width=w_logo, height=h_logo, mask='auto')

        # Top-Right: FXEC Crest / Circular Seal
        crest_path = os.path.join(ASSETS_DIR, 'fxec_crest.png')
        if os.path.exists(crest_path):
            w_crest = 68
            h_crest = 68
            canvas.saveState()
            canvas.setFillColor(colors.HexColor('#FFFFFF'))
            canvas.circle(PAGE_WIDTH - 142 + w_crest/2, PAGE_HEIGHT - 92 + h_crest/2, w_crest/2 + 2, fill=1, stroke=0)
            canvas.restoreState()
            canvas.drawImage(crest_path, PAGE_WIDTH - 142, PAGE_HEIGHT - 92, width=w_crest, height=h_crest, mask='auto')

        # ---------------------------------------------------------------------
        # 7. CERTIFICATE TITLE PILL / CAPSULE ORNAMENT & TEXT
        # ---------------------------------------------------------------------
        pill_cx = PAGE_WIDTH / 2
        pill_cy = PAGE_HEIGHT - 170
        pill_w = 230
        pill_h = 36

        # Pill background (soft lavender/blue tint)
        canvas.setFillColor(colors.HexColor('#e0e7ff'))
        canvas.roundRect(pill_cx - pill_w/2, pill_cy - pill_h/2, pill_w, pill_h, 18, fill=1, stroke=0)

        # Lateral accent lines with circular beads on left and right (pinkish/mauve tint)
        canvas.setStrokeColor(colors.HexColor('#cbd5e1'))
        canvas.setLineWidth(1.5)
        # Left line & bead
        canvas.line(pill_cx - pill_w/2 - 4, pill_cy, pill_cx - pill_w/2 - 40, pill_cy)
        canvas.setFillColor(colors.HexColor('#f43f5e')) # subtle berry/rose accent dot
        canvas.circle(pill_cx - pill_w/2 - 40, pill_cy, 3.5, fill=1, stroke=0)

        # Right line & bead
        canvas.line(pill_cx + pill_w/2 + 4, pill_cy, pill_cx + pill_w/2 + 40, pill_cy)
        canvas.setFillColor(colors.HexColor('#f43f5e'))
        canvas.circle(pill_cx + pill_w/2 + 40, pill_cy, 3.5, fill=1, stroke=0)

        # "Certificate" text drawn directly inside pill for perfect centering!
        canvas.setFont(CERT_FONT, 30)
        canvas.setFillColor(colors.HexColor('#0f172a'))
        canvas.drawCentredString(pill_cx, pill_cy - 10, "Certificate")

        # ---------------------------------------------------------------------
        # 8. SIGNATURE ACCENT LINES & AUTOGRAPHS
        # ---------------------------------------------------------------------
        # Sig 1: Co-ordinator (Left)
        canvas.setStrokeColor(colors.HexColor('#94a3b8'))
        canvas.setLineWidth(1)
        canvas.line(125, 76, 265, 76)
        # Autograph simulation
        canvas.setFont('Times-BoldItalic', 13)
        canvas.setFillColor(colors.HexColor('#1e293b'))
        canvas.drawString(135, 84, "M. E.")
        canvas.setFont('Helvetica', 8)
        canvas.setFillColor(colors.HexColor('#64748b'))
        canvas.drawString(175, 85, "6/3/26")

        # Sig 2: HOD (Right)
        canvas.setStrokeColor(colors.HexColor('#94a3b8'))
        canvas.setLineWidth(1)
        canvas.line(PAGE_WIDTH - 265, 76, PAGE_WIDTH - 125, 76)
        # Autograph simulation
        canvas.setFont('Times-BoldItalic', 13)
        canvas.setFillColor(colors.HexColor('#1e293b'))
        canvas.drawString(PAGE_WIDTH - 255, 84, "J. Paul")
        canvas.setFont('Helvetica', 8)
        canvas.setFillColor(colors.HexColor('#64748b'))
        canvas.drawString(PAGE_WIDTH - 200, 85, "6/3/26")

        canvas.restoreState()

    doc.build(elements, onFirstPage=draw_decorations)
    buffer.seek(0)
    pdf_data = buffer.getvalue()

    with open(output_pdf_path, 'wb') as f:
        f.write(pdf_data)

    print(f"PDF successfully written to {output_pdf_path}")

    # Convert to PNG for inspection using pymupdf
    doc_fitz = pymupdf.open(stream=pdf_data, filetype="pdf")
    page = doc_fitz[0]
    pix = page.get_pixmap(dpi=150)
    png_path = output_pdf_path.replace('.pdf', '.png')
    pix.save(png_path)
    print(f"Rendered PNG preview written to {png_path}")

if __name__ == '__main__':
    generate_sample_pdf('sample_certificate.pdf')
