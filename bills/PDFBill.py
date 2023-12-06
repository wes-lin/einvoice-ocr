import pdfplumber

from .Bill import Bill


class PDFBill(Bill):
    def __init__(self, pdf):
        self.pdf = pdfplumber.open(pdf)
        context = ""
        for page in self.pdf.pages:
            context += page.extract_text()
        super().__init__(context)

    def __del__(self):
        self.pdf.close()
