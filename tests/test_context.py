from testkit.context import *

def test_context_user():
    from contextlib import contextmanager
    test_dict = dict(value='before')
    @contextmanager
    def test_context(test_dict):
        test_dict['value'] = 'during'
        yield 'test'
        test_dict['value'] = 'after'
    ctx = ContextUser(test_context(test_dict))
    assert test_dict['value'] == 'before'
    ctx.enter()
    assert test_dict['value'] == 'during'
    ctx.exit()
    assert test_dict['value'] == 'after'
    
class my_context(ContextDecorator):
    def before(self):
        self.hello = 'hello'
        self.done = False
    
    def after(self):
        self.done = True

def test_context_decorator_as_decorator():
    as_decorator = my_context()
    @as_decorator
    def hello(context):
        assert context.hello == 'hello'
    hello()
    assert as_decorator.done == True

def test_context_decorator_as_decorator_exception():
    as_decorator = my_context()
    fake_message = 'A fake error!'
    @as_decorator
    def hello(context):
        raise Exception(fake_message)
    try:
        hello()
    except Exception, e:
        assert e.message == fake_message
    assert as_decorator.done == True

def test_context_decorator_as_context():
    as_context = my_context()
    with as_context as context:
        assert context.hello == 'hello'
        assert context.done == False
    assert context.done == True

def test_context_decorator_as_context_exception():
    as_context = my_context()
    fake_message = 'error!'
    try:
        with as_context as context:
            raise Exception(fake_message)
    except Exception, e:
        assert e.message == fake_message
    assert context.done == True

class my_other_context(ContextDecorator):
    def before(self):
        self.hello = 'hello'
        self.done = False
        return self.hello
    
    def after(self):
        self.done = True

def test_context_decorator_before_returns_custom_context():
    as_context = my_other_context()
    with as_context as hello:
        assert hello == 'hello'
