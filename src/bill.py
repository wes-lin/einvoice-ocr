import re
import pdfplumber


class Bill:
    def __init__(self, context):
        self.context = re.sub(r"^\s+|￥|¥|\n|\r|<br />", "", context)

    def extract(self, rules):
        data = {}
        for rule in rules:
            objMatch = re.search(rule, self.context)
            if objMatch:
                for key in objMatch.groupdict().keys():
                    val = objMatch.group(key)
                    data[key] = val
        return data

    def get_context(self):
        return self.context


class PDFBill(Bill):
    def __init__(self, pdf):
        self.pdf = pdfplumber.open(pdf)
        context = ""
        for page in self.pdf.pages:
            context += page.extract_text()
        super().__init__(context)

    def __del__(self):
        self.pdf.close()
