import re
from datetime import datetime


def get_datetime_format(datetime_str: str):
    if datetime_str == None:
        return None
    if re.search(
        r"[0-9]{4}-[0-9]{1,2}-[0-9]{1,2} [0-9]{2}:[0-9]{2}:[0-9]{2}", datetime_str
    ):
        return "%Y-%m-%d %H:%M:%S"
    if re.search(r"[0-9]{4}-[0-9]{1,2}-[0-9]{1,2}", datetime_str):
        return "%Y-%m-%d"
    if re.search(r"[0-9]{4}年[0-9]{1,2}月[0-9]{1,2}日", datetime_str):
        return "%Y年%m月%d日"


def str_to_date(datetime_str: str) -> datetime:
    format = get_datetime_format(datetime_str)
    if format == None:
        return None
    return datetime.strptime(datetime_str, format)


def date_convert(datetime_str: str, format_str: str) -> str:
    return str_to_date(datetime_str).strftime(format_str)
