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
        "下单时间.*(?P<orderDate>[0-9]{4}-[0-9]{1,2}-[0-9]{1,2} [0-9]{2}:[0-9]{2}:[0-9]{2})",
        "总计\\s+(?P<orderMoney>([0-9]+|[0-9]{0,})(.[0-9]{1,2}))",
        "合计\\s+(?P<orderMoney>([0-9]+|[0-9]{0,})(.[0-9]{1,2}))",
        "实付款\\s+(?P<orderMoney>([0-9]+|[0-9]{0,})(.[0-9]{1,2}))",
        "开票日期:(?P<invoiceDate>[0-9]{4}年[0-9]{1,2}月[0-9]{1,2}日)",
        "（小写）(?P<invoiceMoney>([0-9]+|[0-9]{0,})(.[0-9]{1,2}))",
        "行程起止日期[^0-9]+(?P<tripDate>[0-9]{4}-[0-9]{1,2}-[0-9]{1,2})",
        "合计(?P<tripMoney>([0-9]+|[0-9]{0,})(.[0-9]{1,2}))",
        "申请日期[^0-9]+(?P<filedDate>[0-9]{4}-[0-9]{1,2}-[0-9]{1,2})",
    ]

    def __init__(self) -> None:
        logging.basicConfig(
            encoding="utf-8", format="%(threadName)s %(asctime)s %(message)s"
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
        return {
            "file_name": file_name,
            "content_type": content_type,
            # "payload": base64.b64decode(message.get_payload()),
            "data": bill.extract(self.RULE_MAP),
        }

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
    test = GeneralTask()
    test.execute(message)
