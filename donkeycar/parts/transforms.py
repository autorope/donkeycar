# -*- coding: utf-8 -*-


class Lambda:
    """
    Wraps a function into a donkey part.
    """
    def __init__(self, f):
        """
        Accepts the function to use.
        """
        self.f = f
        
    def run(self, *args, **kwargs):
        return self.f(*args, **kwargs)