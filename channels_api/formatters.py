
class BaseFormatter(object):

    def __init__(self, data=None, error=None, message=None):
        self.data = data
        self.error = error
        self.message = message

    def __call__(self):
        return self.format()

    def format(self):
        raise NotImplementedError("%s must implement format()" % self.__class__)


class SimpleFormatter(BaseFormatter):
    """Standard non-formatting."""

    def format(self):
        if self.error:
            return {"errors": self.error.detail}
        return self.data
