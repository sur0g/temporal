
class Singleton:
    def __init__(self ,klass):
        self.klass = klass
        self.instance = None

    def __call__(self, *args, **kwargs):
        if self.instance is None:
            self.instance = self.klass(*args ,**kwargs)
        return self.instance


def lazy_property(fn):
    attr_name = '_lazy_' + fn.__name__

    @property
    def _lazy_property(self):
        if not hasattr(self, attr_name):
            setattr(self, attr_name, fn(self))
        return getattr(self, attr_name)
    return _lazy_property
