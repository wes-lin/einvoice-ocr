import logging
import requests
import re
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logging.basicConfig(encoding="utf-8", format="%(threadName)s %(asctime)s %(message)s")


class OCR:
    OCR_HOST = "https://www.imagetotext.info"
    TOKEN = r'<meta name="_token" content="(?P<token>.*?)" />'
    headers = {
        "Referer": "https://www.imagetotext.info/",
        "Origin": "https://www.imagetotext.info",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        "X-Requested-With": "XMLHttpRequest",
    }

    _instance = None

    def __init__(self):
        session = requests.Session()
        session.verify = False
        self.session = session
        self.token = self.get_token()

    def extract_text(self, file_name, file_base64, file_type):
        logging.warning("开始识别图片:" + file_name)
        data = {
            "imgname": file_name,
            "tool": "",
            "count": 0,
            "_token": self.token,
            "base64": "data:image/{ext};base64,{data}".format(
                ext=file_type, data=file_base64
            ),
        }
        response = self.session.post(
            self.OCR_HOST + "/image-to-text", headers=self.headers, data=data
        )
        logging.warning(response)
        logging.warning("识别成功")
        json = response.json()
        text = json["text"]
        return text

    def get_token(self):
        res = self.session.get(self.OCR_HOST)
        result = re.finditer(self.TOKEN, res.text)
        for item in result:
            if item.group("token"):
                return item.group("token")

        return None


ocr = OCR()
