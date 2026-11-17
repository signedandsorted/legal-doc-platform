import io
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

NAVY = colors.HexColor("#1c2333")


def render_pdf(document: dict) -> bytes:
    base = getSampleStyleSheet()
    title = ParagraphStyle("t", parent=base["Title"], textColor=NAVY, fontSize=20)
    notice = ParagraphStyle("n", parent=base["BodyText"], textColor=colors.HexColor("#b42318"), fontName="Helvetica-Bold", fontSize=9)
    h = ParagraphStyle("h", parent=base["Heading2"], textColor=NAVY)
    body = ParagraphStyle("b", parent=base["BodyText"], fontSize=10.5, leading=15)
    small = ParagraphStyle("s", parent=body, fontSize=8.5, leading=11, textColor=colors.HexColor("#475467"))
    story = [Paragraph(escape(document["title"]), title), Paragraph(escape(document["notice"]), notice), Spacer(1, 6 * mm)]
    for section in document["sections"]:
        story.append(Paragraph(escape(section["heading"]), h))
        story += [Paragraph(escape(p), body) for p in section["paragraphs"]]
        if section.get("notes"):
            story.append(Paragraph("What each clause means (not part of the document)", ParagraphStyle("hn", parent=h, fontSize=11)))
            story += [Paragraph(escape(n), small) for n in section["notes"]]
    story += [Spacer(1, 4 * mm), Paragraph("Next steps", h)]
    story += [Paragraph(escape(f"{i}. {step}"), body) for i, step in enumerate(document["next_steps"], 1)]
    if document.get("sources"):
        story += [Spacer(1, 4 * mm), Paragraph("Official sources", h)]
        story += [Paragraph(escape(f"{x['title']}: {x['url']}"), small) for x in document["sources"]]
    buffer = io.BytesIO()
    SimpleDocTemplate(buffer, pagesize=A4, title=document["title"], leftMargin=20 * mm, rightMargin=20 * mm, topMargin=18 * mm, bottomMargin=18 * mm).build(story)
    return buffer.getvalue()
