
class PartFactory(type):
    """
    Metaclass to hold the registration dictionary of the part constructor
    functions
    """
    register = {}

    def __init__(cls, name, bases, d):
        cls.register[cls.__name__.lower()] = cls.create

    @classmethod
    def make(mcs, concrete, kwargs):
        return mcs.register[concrete.lower()](kwargs)


class Part(object, metaclass=PartFactory):
    """
    Base class for factory creatable parts, implementing create()
    """
    @classmethod
    def create(cls, kwargs):
        return cls(**kwargs)


class TestPart(Part):
    """
    Test Part that shows the creation of new parts
    """
    def __init__(self, value):
        self.value = value
        print('Created TestPart with value', self.value)


if __name__ == '__main__':
    # we allow any case for the part in the dictionary, as python classes are
    # expected to be camel case
    data = [{'testpart': {'value': 4}}, {'TestPart': {'value': 'hello part!'}}]

    for d in data:
        for obj, ctor in d.items():
            PartFactory.make(obj, ctor)
