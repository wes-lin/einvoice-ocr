from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
import imaplib
import smtplib
import logging
import email
from email.message import EmailMessage, Message
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.header import Header, decode_header
from email.mime.text import MIMEText
from email.utils import parseaddr
from typing import List
import json
import os
import base64
from io import BytesIO
import functools
from string import Template
from pymongo import MongoClient
from bills import Bill, PDFBill
from util import date_convert, ocr, extract_message, build_MIME


def decode_str(s):
    value, charset = decode_header(s)[0]
    if charset:
        value = value.decode(charset)
    return value


def base64_byte(s: str):
    byte_data = base64.b64decode(s)
    data = BytesIO(byte_data)
    return data


def get_bill(message: Message):
    if message.get_filename() == None:
        return None
    file_name = decode_str(message.get_filename())
    content_type = message.get_content_type()
    bill: Bill = None
    if file_name.endswith(".pdf"):
        bill = PDFBill(base64_byte(message.get_payload()))
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
        "bill": bill,
        "payload": base64.b64decode(message.get_payload()),
    }


def get_attachments(message: EmailMessage):
    tasks = []
    executor = ThreadPoolExecutor(max_workers=5, thread_name_prefix="Bill_Thread")
    for result in executor.map(get_bill, message.iter_attachments(), timeout=100):
        if result != None:
            tasks.append(result)
    return tasks


def load_config(path):
    with open(path, mode="r", encoding="utf-8") as configFile:
        config = json.load(configFile)
    return config


def get_user_template(userId, subject):
    t = get_template(userId, subject)
    if t == None:
        t = get_template(userId, "默认")
    return t


@functools.cache
def get_template(userId, subject):
    return db["user_file"].find_one({"userId": userId, "name": subject})


@functools.cache
def get_user_file_config(user_id, group, type):
    return db["user_file_configs"].find_one(
        {"userId": user_id, "group": group, "type": type}
    )


@functools.cache
def get_user_by_email(email: str):
    return db["uses"].find_one({"email": {"$regex": email, "$options": "i"}})


def send_result_messag(_from: str, attachments: List, content: MIMEBase):
    mm = MIMEMultipart()
    mm["From"] = os.getenv("SMTP_USER")
    mm["To"] = _from
    mm["Subject"] = Header(
        "Invoice Report {}".format(datetime.now().strftime("%Y%m%d%H%M%S")), "utf-8"
    )
    mm.attach(content)

    for attachment in attachments:
        mm.attach(
            build_MIME(
                attachment["payload"],
                attachment["new_file_name"],
            )
        )
    obj = smtplib.SMTP(os.getenv("SMTP_URL"), 465)
    obj.starttls()
    obj.login(os.getenv("EMAIL_USER"), os.getenv("EMAIL_PASS"))
    obj.send_message(mm)
    obj.quit()
    logging.warning("发送成功")


def extract_bill(message: EmailMessage, user):
    messages = extract_message(message)
    _bills = []
    for _message in messages:
        attachments = get_attachments(_message)
        subject = decode_str(_message.get("subject"))
        template = get_user_template(subject)
        _file_vars = {}
        for attachment in attachments:
            bill: Bill = attachment["bill"]
            for file in template["files"]:
                if file["keyword"] in bill.get_context():
                    file_vars = bill.extract(file["dataMapping"])
                    dic = {key: value for (key, value) in file_vars}
                    attachment["file_vars"] = dic
                    attachment["type"] = file["type"]
                    if template["multipart"]:
                        _file_vars = {**_file_vars, **dic}

        for attachment in attachments:
            if template["multipart"]:
                attachment["file_vars"] = _file_vars
            file_config = get_user_file_config(
                user["_id"], template["group"], attachment["type"]
            )
            temp = {
                "userName": user["userName"],
                "fileExt": attachment["file_name"].split(".")[1],
            }
            logging.warning(attachment["file_vars"])
            for var in file_config["vars"]:
                file_vars = attachment["file_vars"]
                _val: str = file_vars[var["code"]]
                if _val != None:
                    date_type = var["dataType"]
                    if date_type == "date":
                        _val = date_convert(_val, var["format"])
                    temp[var["code"]] = _val
                    attachment["new_file_name"] = Template(
                        file_config["fileName"]
                    ).safe_substitute(temp)
            _bills.append(attachment)
    return _bills


def handle_email(message: EmailMessage):
    _from = parseaddr(message.get("From"))
    user = get_user_by_email(_from[1])
    bills = extract_bill(message, user)
    content = MIMEText("这是报销单据", "plain", "utf-8")
    send_result_messag(_from[1], bills, content)


logging.basicConfig(encoding="utf-8", format="%(threadName)s %(asctime)s %(message)s")

if __name__ == "__main__":
    client = MongoClient(os.getenv("DB_URL"))
    db = client["invoice"]
    # email_file = open("test\\test.eml")
    # message: EmailMessage = email.message_from_file(email_file, _class=EmailMessage)
    # handle_email(message)
    logging.warning("开始读取邮件")
    mail = imaplib.IMAP4_SSL(os.getenv("IMAP_URL"), 993)
    mail.login(os.getenv("EMAIL_USER"), os.getenv("EMAIL_PASS"))
    mail.select("inbox")
    status, uids = mail.search(None, "UNSEEN")
    if status != "OK":
        raise Exception("读取异常")
    for uid in uids[0].split():
        status, data = mail.fetch(uid, "(RFC822)")
        if status == "OK":
            email_message = email.message_from_bytes(data[0][1], _class=EmailMessage)
            handle_email(email_message)
    logging.warning("执行结束")
    client.close()
