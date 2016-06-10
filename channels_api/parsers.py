import json


class BaseParser(object):

    def __init__(self, message):
        self.message = message

    def __call__(self):
        return self.parse()

    def parse(self):
        raise NotImplementedError("%s must implement parse()" % self.__class__)


class SimpleParser(BaseParser):

    def parse(self):
        json_content = json.loads(self.message.content['text'])
        json_content.pop('method') if 'method' in json_content else None
        return json_content
