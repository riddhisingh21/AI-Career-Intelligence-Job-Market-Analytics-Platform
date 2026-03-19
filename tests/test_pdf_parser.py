import io
import unittest
import zipfile

from pdf_parser import extract_text_from_docx, extract_text_from_resume


def build_docx_bytes(paragraphs):
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
    body = "".join(
        f"<w:p><w:r><w:t>{paragraph}</w:t></w:r></w:p>" for paragraph in paragraphs
    )
    document = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:body>{body}</w:body>
</w:document>"""

    file_obj = io.BytesIO()
    with zipfile.ZipFile(file_obj, "w") as docx_file:
        docx_file.writestr("[Content_Types].xml", content_types)
        docx_file.writestr("_rels/.rels", rels)
        docx_file.writestr("word/document.xml", document)

    file_obj.name = "resume.docx"
    file_obj.seek(0)
    return file_obj


class ResumeParserTests(unittest.TestCase):
    def test_extract_text_from_docx_reads_paragraphs(self):
        file_obj = build_docx_bytes(["Python Developer", "Streamlit Projects"])

        text = extract_text_from_docx(file_obj)

        self.assertEqual(text, "Python Developer\nStreamlit Projects")

    def test_extract_text_from_resume_routes_docx_files(self):
        file_obj = build_docx_bytes(["Machine Learning", "Data Analysis"])

        text = extract_text_from_resume(file_obj)

        self.assertIn("Machine Learning", text)
        self.assertIn("Data Analysis", text)


if __name__ == "__main__":
    unittest.main()