"""A Word file the client or the firm can open and edit. It is the same text as the PDF."""
import io
import zipfile
from xml.sax.saxutils import escape


def _p(text: str, bold: bool = False) -> str:
    run = f"<w:r><w:rPr><w:b/></w:rPr><w:t xml:space=\"preserve\">{escape(text)}</w:t></w:r>" if bold else f"<w:r><w:t xml:space=\"preserve\">{escape(text)}</w:t></w:r>"
    return f"<w:p>{run}</w:p>"


def render_docx(document: dict) -> bytes:
    body = [_p(document.get("title") or "Draft", True), _p(document.get("notice") or "")]
    for section in document.get("sections") or []:
        body.append(_p(section.get("heading") or "", True))
        body += [_p(p) for p in section.get("paragraphs") or []]
        for note in section.get("notes") or []:
            body.append(_p("Note: " + note))
    body.append(_p("Next steps", True))
    body += [_p(f"{i}. {step}") for i, step in enumerate(document.get("next_steps") or [], 1)]
    document_xml = (
        "<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>"
        "<w:document xmlns:w=\"http://schemas.openxmlformats.org/wordprocessingml/2006/main\"><w:body>"
        + "".join(body) + "<w:sectPr/></w:body></w:document>"
    )
    content_types = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
<Default Extension="xml" ContentType="application/xml"/>
<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
</Types>"""
    rels = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
</Relationships>"""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("[Content_Types].xml", content_types)
        z.writestr("_rels/.rels", rels)
        z.writestr("word/document.xml", document_xml)
    return buf.getvalue()
