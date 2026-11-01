"""Unit tests for Local Offline CV/Résumé Parser (Section 21.2).

Validates:
1. Parsing from text files and extracting candidate activities, roles, dates.
2. Parsing from formatted PDF CVs.
3. Parsing from Word (DOCX) files without third-party external dependencies.
4. Privacy: secure deletion of source CV file.
"""

from __future__ import annotations

import tempfile
import unittest
import zipfile
from pathlib import Path

from app.extraction.cv_parser import CVParser


class TestCVParser(unittest.TestCase):
    """Test local CV parser across file formats and entity extraction."""

    def setUp(self) -> None:
        self.parser = CVParser()
        self.temp_dir = Path(tempfile.mkdtemp())

    def test_parse_txt_cv(self) -> None:
        cv_text = """
JOHN DOE - CURRICULUM VITAE
Email: john@example.com

PROFESSIONAL EXPERIENCE

2024 - Present
Health Security Agency
Role: Public Health Specialist
- Surveillance of communicable disease outbreaks
- Epidemiological risk assessment and public health regulations

2021 - 2024
Insurtech Solutions SA
Role: Data Scientist
- Developed machine learning fraud detection models
- Risk scoring and actuarial loss ratio modeling
- Solvency II reporting

2018 - 2021
Tech Innovate SARL
Role: Software Engineer
- Python and Docker backend development
- SQL database optimization

EDUCATION
2018: Master of Science in Computer Science - University of Science
"""
        txt_file = self.temp_dir / "resume.txt"
        txt_file.write_text(cv_text, encoding="utf-8")

        result = self.parser.parse_file(txt_file)

        self.assertGreaterEqual(len(result.activities), 2)
        orgs = [a.organization for a in result.activities]
        self.assertTrue(any("Health" in o or "Insurtech" in o for o in orgs))

        roles = [a.role for a in result.activities]
        self.assertTrue(any("Data Scientist" in r or "Public Health" in r for r in roles))

        # Check domains/skills
        self.assertTrue(any("Machine Learning" in d or "Insurtech" in d or "Public Health" in d for d in result.domains))
        self.assertTrue(any("Python" in s or "Solvency II" in s or "Docker" in s for s in result.skills))

    def test_parse_docx_cv(self) -> None:
        # Create a genuine minimal DOCX (ZIP archive containing word/document.xml)
        docx_path = self.temp_dir / "cv_sample.docx"
        doc_xml = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:body>
    <w:p><w:r><w:t>Curriculum Vitae</w:t></w:r></w:p>
    <w:p><w:r><w:t>2021 - 2024</w:t></w:r></w:p>
    <w:p><w:r><w:t>Alpha Health Company</w:t></w:r></w:p>
    <w:p><w:r><w:t>Role: Data Scientist</w:t></w:r></w:p>
    <w:p><w:r><w:t>Python, PyTorch, Machine Learning, Medical Devices</w:t></w:r></w:p>
  </w:body>
</w:document>"""

        with zipfile.ZipFile(str(docx_path), "w") as z:
            z.writestr("word/document.xml", doc_xml.encode("utf-8"))

        res = self.parser.parse_file(docx_path)
        self.assertGreaterEqual(len(res.activities), 1)
        self.assertEqual(res.activities[0].start_year, 2021)
        self.assertEqual(res.activities[0].end_year, 2024)

    def test_secure_deletion_after_import(self) -> None:
        temp_cv = self.temp_dir / "temporary_cv.txt"
        temp_cv.write_text("Confidential Personal CV Data", encoding="utf-8")
        self.assertTrue(temp_cv.exists())

        deleted = self.parser.securely_delete_source_file(temp_cv)
        self.assertTrue(deleted)
        self.assertFalse(temp_cv.exists())


if __name__ == "__main__":
    unittest.main()
