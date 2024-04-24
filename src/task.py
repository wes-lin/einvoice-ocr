import ast
from concurrent.futures import ThreadPoolExecutor
from email.message import EmailMessage, Message
from email.header import Header, decode_header
import base64
from io import BytesIO
from bill import Bill, PDFBill
import logging

from util import date_convert, ocr, extract_message, build_MIME
import re
import email


class GeneralTask:

    RULE_MAP = [
        "下单时间.*(?P<order_date>[0-9]{4}-[0-9]{1,2}-[0-9]{1,2} [0-9]{2}:[0-9]{2}:[0-9]{2})",
        "总计\\s+(?P<order_money>([0-9]+|[0-9]{0,})(.[0-9]{1,2}))",
        "合计\\s+(?P<order_money>([0-9]+|[0-9]{0,})(.[0-9]{1,2}))",
        "实付款\\s+(?P<order_money>([0-9]+|[0-9]{0,})(.[0-9]{1,2}))",
        "开票日期:(?P<invoice_date>[0-9]{4}年[0-9]{1,2}月[0-9]{1,2}日)",
        "（小写）(?P<invoice_money>([0-9]+|[0-9]{0,})(.[0-9]{1,2}))",
        "行程起止日期[^0-9]+(?P<trip_date>[0-9]{4}-[0-9]{1,2}-[0-9]{1,2})",
        "合计\\s+(?P<trip_money>([0-9]+|[0-9]{0,})(.[0-9]{1,2}))",
        "申请日期[^0-9]+(?P<filed_date>[0-9]{4}-[0-9]{1,2}-[0-9]{1,2})",
    ]

    def __init__(self, data_format) -> None:
        logging.basicConfig(
            encoding="utf-8", format="%(threadName)s %(asctime)s %(message)s"
        )
        self.data_format = data_format

    @classmethod
    def initsec(self):
        return self(
            {
                "order_date": {"data_type": "date", "format": "%m%d"},
                "order_money": {"data_type": "num", "format": "%.2f"},
            }
        )

    def decode_str(self, s):
        value, charset = decode_header(s)[0]
        if charset:
            value = value.decode(charset)
        return value

    def base64_byte(self, s: str):
        byte_data = base64.b64decode(s)
        data = BytesIO(byte_data)
        return data

    def get_bill(self, message: Message):
        if message.get_filename() == None:
            return None
        file_name = self.decode_str(message.get_filename())
        content_type = message.get_content_type()
        bill: Bill = None
        if file_name.endswith(".pdf"):
            bill = PDFBill(self.base64_byte(message.get_payload()))
        elif file_name.endswith(".jpg") or file_name.endswith(".png"):
            text = ocr.extract_text(
                file_name, message.get_payload(), file_name.split(".")[1]
            )
            bill = Bill(text)
        else:
            logging.error("unsupport file:{}".format(file_name))
            return None
        vars = self.format_vars(bill.extract(self.RULE_MAP))
        return {
            "file_name": file_name,
            "content_type": content_type,
            # "payload": base64.b64decode(message.get_payload()),
            "vars": vars,
        }

    def format_vars(self, vars):
        for k, v in vars.items():
            if k in self.data_format:
                format = self.data_format[k]
                newv = v
                match format["data_type"]:
                    case "date":
                        newv = date_convert(v, format["format"])
                    case "num":
                        newv = format["format"] % ast.literal_eval(v)
                vars[k] = newv
        return vars

    def get_attachments(self, message: EmailMessage):
        tasks = []
        executor = ThreadPoolExecutor(
            max_workers=5, thread_name_prefix="GeneralTask_Thread"
        )
        for result in executor.map(
            self.get_bill, message.iter_attachments(), timeout=100
        ):
            if result != None:
                tasks.append(result)
        return tasks

    def execute(self, message: EmailMessage):
        data = self.get_attachments(message)
        logging.warning(data)


if __name__ == "__main__":
    email_file = open("..\\test\\test.eml")
    message: EmailMessage = email.message_from_file(email_file, _class=EmailMessage)
    test = GeneralTask.initsec()
    test.execute(message)
