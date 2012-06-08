"""
testkit.context
~~~~~~~~~~~~~~~

Tools for dealing with context managers
"""
from functools import wraps

class ContextUser(object):
    """Uses context objects without the with statement"""
    def __init__(self, context_manager):
        self._context_manager = context_manager

    def enter(self):
        """Enters the context"""
        return self._context_manager.__enter__()
    
    def exit(self, ex_type=None, ex_value=None, traceback=None):
        """Exits the context"""
        return self._context_manager.__exit__(ex_type, ex_value, traceback)

# Inspired by Michael Foord
# http://code.activestate.com/recipes/577273-decorator-and-context-manager-from-a-single-api/
class ContextDecorator(object):
    def __call__(self, f):
        @wraps(f)
        def decorating_function(*args, **kwargs):
            args = list(args)
            args.append(self)
            self.before()
            try:
                result = f(*args, **kwargs)
            finally:
                self.after()
            return result
        return decorating_function

    def __enter__(self):
        return_value = self.before() or self
        return return_value

    def __exit__(self, ex_type=None, ex_value=None, traceback=None):
        self.after()

    def before(self):
        pass

    def after(self):
        pass
