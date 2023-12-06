import re


class Bill:
    def __init__(self, context):
        self.context = re.sub(r"^\s+|￥|¥|\n|\r|<br />", "", context)

    def extract(self, rules):
        data = []
        for rule in rules:
            objMatch = re.search(rule["regExp"], self.context)
            if objMatch:
                for key in objMatch.groupdict().keys():
                    val = objMatch.group(key)
                    data.append((key, val))
        return data

    def get_context(self):
        return self.context
