import fitz


class PDFService:
    @staticmethod
    def extract_text(pdf_path):
        text = ""

        with fitz.open(pdf_path) as document:
            for page in document:
                text += page.get_text()

        text = text.strip()

        if not text:
            raise ValueError("No readable text found in this PDF. This may be a scanned PDF and needs OCR.")

        return text
