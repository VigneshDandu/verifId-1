import os
import tempfile
import unittest
from unittest.mock import patch

import fitz

from utils.pdf_parser import (
    MAX_PAGES,
    extract_text_from_pdf,
    process_uploaded_pdf,
    save_uploaded_pdf,
)


class Upload:
    def __init__(self, content):
        self.content = content

    def save(self, destination):
        destination.write(self.content)


class PDFUploadTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)

    def make_pdf(self, pages=1):
        with fitz.open() as document:
            for _ in range(pages):
                page = document.new_page()
                page.insert_text((72, 72), 'Software engineer job responsibilities and requirements. ' * 4)
            return document.tobytes()

    def test_uploads_have_distinct_paths_and_preserve_contents(self):
        first = save_uploaded_pdf(Upload(b'first'), self.directory.name)
        second = save_uploaded_pdf(Upload(b'second'), self.directory.name)
        self.assertNotEqual(first, second)
        for path, expected in ((first, b'first'), (second, b'second')):
            with open(path, 'rb') as saved:
                self.assertEqual(saved.read(), expected)

    def test_successful_extraction_deletes_upload(self):
        result = process_uploaded_pdf(Upload(self.make_pdf()), self.directory.name)
        self.assertTrue(result['success'])
        self.assertEqual(result['pages'], 1)
        self.assertIn('Software engineer', result['text'])
        self.assertEqual(os.listdir(self.directory.name), [])

    def test_invalid_pdf_deletes_upload(self):
        result = process_uploaded_pdf(Upload(b'not a PDF'), self.directory.name)
        self.assertFalse(result['success'])
        self.assertEqual(os.listdir(self.directory.name), [])

    def test_extraction_exception_deletes_upload(self):
        with patch('utils.pdf_parser.extract_text_from_pdf', side_effect=RuntimeError('failed')):
            with self.assertRaises(RuntimeError):
                process_uploaded_pdf(Upload(b'content'), self.directory.name)
        self.assertEqual(os.listdir(self.directory.name), [])

    def test_failed_save_deletes_partial_upload(self):
        class BrokenUpload:
            def save(self, destination):
                destination.write(b'partial')
                raise OSError('upload interrupted')

        with self.assertRaises(OSError):
            save_uploaded_pdf(BrokenUpload(), self.directory.name)
        self.assertEqual(os.listdir(self.directory.name), [])

    def test_page_limit_closes_document(self):
        document = fitz.open(stream=self.make_pdf(MAX_PAGES + 1), filetype='pdf')
        with patch('utils.pdf_parser.fitz.open', return_value=document):
            result = extract_text_from_pdf(__file__)
        self.assertFalse(result['success'])
        self.assertIn('max 10 pages', result['error'])
        self.assertTrue(document.is_closed)

    def test_page_read_error_closes_document(self):
        document = fitz.open(stream=self.make_pdf(), filetype='pdf')
        with patch('utils.pdf_parser.fitz.open', return_value=document):
            with patch.object(fitz.Page, 'get_text', side_effect=RuntimeError('broken page')):
                result = extract_text_from_pdf(__file__)
        self.assertFalse(result['success'])
        self.assertTrue(document.is_closed)


if __name__ == '__main__':
    unittest.main()
