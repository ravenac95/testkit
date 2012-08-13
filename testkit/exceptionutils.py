import sys


# on pypy we can take advantage of transparent proxies
try:
    from __pypy__ import tproxy
except ImportError:
    tproxy = None


# how does the raise helper look like?
try:
    exec "raise TypeError, 'foo'"
except SyntaxError:
    raise_helper = 'raise __internal_exception__[1]'
except TypeError:
    raise_helper = 'raise __internal_exception__[0], __internal_exception__[1]'


def store_any_exception(func, args=None, kwargs=None):
    args = args or tuple()
    kwargs = kwargs or {}
    exc = None
    try:
        func(*args, **kwargs)
    except:
        exc = PicklableExceptionInfo.exc_info()
    return exc


class PicklableExceptionInfo(object):
    @classmethod
    def exc_info(cls):
        exc_info = sys.exc_info()
        info = cls(*exc_info[:2])
        info.save_traceback(exc_info[2])
        return info

    def __init__(self, exc_type, exc_value):
        self._exc_type = exc_type
        self._exc_value = exc_value
        self._traceback_list = []

    def save_traceback(self, tb):
        """Save the original traceback"""
        traceback_list = self._traceback_list
        current_tb = tb
        while current_tb:
            traceback_data = PicklableTracebackData.from_traceback(current_tb)
            traceback_list.append(traceback_data)
            current_tb = current_tb.tb_next

    def reraise(self):
        generated_tb = self.generated_traceback()
        raise self._exc_type, self._exc_value, generated_tb.tb

    def generated_traceback(self):
        prev_tb = None
        initial_tb = None
        for traceback_data in self._traceback_list:
            exc_info = traceback_data.create_exc_info(self._exc_type,
                    self._exc_value)
            exc_type, exc_value, tb = exc_info
            frame = TracebackFrameProxy(tb)
            if prev_tb is None:
                initial_tb = frame
            else:
                prev_tb.set_next(frame)
            prev_tb = frame
        return initial_tb


class PicklableTracebackData(object):
    @classmethod
    def from_traceback(cls, tb):
        frame = tb.tb_frame
        code = frame.f_code
        code_filename = code.co_filename
        lineno = tb.tb_lineno
        return cls(code_filename, lineno)

    def __init__(self, code_filename, lineno):
        self._code_filename = code_filename
        self._lineno = lineno

    def create_exc_info(self, exc_type, exc_value):
        code_filename = self._code_filename
        fake_code = compile('\n' * (self._lineno - 1) + raise_helper,
                code_filename, 'exec')
        tb_globals = {
            '__name__': code_filename,
            '__file__': code_filename,
            '__internal_exception__': (exc_type, exc_value),
        }
        tb_locals = {}
        try:
            exec fake_code in tb_globals, tb_locals
        except:
            exc_info = sys.exc_info()
            new_tb = exc_info[2].tb_next

        return exc_info[:2] + (new_tb,)


class TracebackFrameProxy(object):
    """Proxies a traceback frame."""

    def __init__(self, tb):
        self.tb = tb
        self._tb_next = None

    @property
    def tb_next(self):
        return self._tb_next

    def set_next(self, next):
        if tb_set_next is not None:
            try:
                tb_set_next(self.tb, next and next.tb or None)
            except Exception:
                # this function can fail due to all the hackery it does
                # on various python implementations.  We just catch errors
                # down and ignore them if necessary.
                pass
        self._tb_next = next

    @property
    def is_jinja_frame(self):
        return '__jinja_template__' in self.tb.tb_frame.f_globals

    def __getattr__(self, name):
        return getattr(self.tb, name)


def _init_ugly_crap():
    """This function implements a few ugly things so that we can patch the
    traceback objects.  The function returned allows resetting `tb_next` on
    any python traceback object.  Do not attempt to use this on non cpython
    interpreters
    """
    import ctypes
    from types import TracebackType

    # figure out side of _Py_ssize_t
    if hasattr(ctypes.pythonapi, 'Py_InitModule4_64'):
        _Py_ssize_t = ctypes.c_int64
    else:
        _Py_ssize_t = ctypes.c_int

    # regular python
    class _PyObject(ctypes.Structure):
        pass
    _PyObject._fields_ = [
        ('ob_refcnt', _Py_ssize_t),
        ('ob_type', ctypes.POINTER(_PyObject))
    ]

    # python with trace
    if hasattr(sys, 'getobjects'):
        class _PyObject(ctypes.Structure):
            pass
        _PyObject._fields_ = [
            ('_ob_next', ctypes.POINTER(_PyObject)),
            ('_ob_prev', ctypes.POINTER(_PyObject)),
            ('ob_refcnt', _Py_ssize_t),
            ('ob_type', ctypes.POINTER(_PyObject))
        ]

    class _Traceback(_PyObject):
        pass
    _Traceback._fields_ = [
        ('tb_next', ctypes.POINTER(_Traceback)),
        ('tb_frame', ctypes.POINTER(_PyObject)),
        ('tb_lasti', ctypes.c_int),
        ('tb_lineno', ctypes.c_int)
    ]

    def tb_set_next(tb, next):
        """Set the tb_next attribute of a traceback object."""
        if not (isinstance(tb, TracebackType) and
                (next is None or isinstance(next, TracebackType))):
            raise TypeError('tb_set_next arguments must be traceback objects')
        obj = _Traceback.from_address(id(tb))
        if tb.tb_next is not None:
            old = _Traceback.from_address(id(tb.tb_next))
            old.ob_refcnt -= 1
        if next is None:
            obj.tb_next = ctypes.POINTER(_Traceback)()
        else:
            next = _Traceback.from_address(id(next))
            next.ob_refcnt += 1
            obj.tb_next = ctypes.pointer(next)

    return tb_set_next


# try to get a tb_set_next implementation if we don't have transparent
# proxies.
tb_set_next = None
if tproxy is None:
    try:
        tb_set_next = _init_ugly_crap()
    except:
        pass
    del _init_ugly_crap
