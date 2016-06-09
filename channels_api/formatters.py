
class BaseFormatter(object):

    def __init__(self, data=None, error=None):
        self.data = data
        self.error = error

    def __call__(self):
        return self.format()

    def format(self):
        raise NotImplementedError("%s must implement format()" % self.__class__)


class SimpleFormatter(BaseFormatter):

    def format(self):
        return self.data or self.error
