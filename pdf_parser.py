import xml.etree.ElementTree as ET
import zipfile

import pdfplumber


WORD_NAMESPACE = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}


def _reset_file(file):
    if hasattr(file, "seek"):
        file.seek(0)


def extract_text_from_pdf(file):
    _reset_file(file)
    text = ""

    with pdfplumber.open(file) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()

            if page_text:
                text += page_text + "\n"

    return text.strip()


def extract_text_from_docx(file):
    _reset_file(file)

    with zipfile.ZipFile(file) as docx_file:
        document_xml = docx_file.read("word/document.xml")

    root = ET.fromstring(document_xml)
    paragraphs = []

    for paragraph in root.findall(".//w:p", WORD_NAMESPACE):
        texts = [node.text for node in paragraph.findall(".//w:t", WORD_NAMESPACE) if node.text]

        if texts:
            paragraphs.append("".join(texts))

    return "\n".join(paragraphs).strip()


def extract_text_from_resume(file):
    file_name = getattr(file, "name", "").lower()

    if file_name.endswith(".pdf"):
        return extract_text_from_pdf(file)

    if file_name.endswith(".docx"):
        return extract_text_from_docx(file)

    raise ValueError("Unsupported resume file format. Please upload a PDF or DOCX file.")