from functools import partial


class ObjPartial(partial):
    """
    This is used to access methods of the `observer` from the attached
    `consumer` without passing the consumer as and argument.

    The `__get__` method of the observer is used to inject the (parent) into
    as an argument into the methods you call.
    """

    def __getattribute__(self, name: str):
        try:
            item = super().__getattribute__(name)
        except AttributeError:
            return partial(getattr(self.func, name), *self.args, **self.keywords)
        return item
