import multiprocessing
import Queue
from functools import wraps
from .exceptionutils import store_any_exception


def monitoring_wrapper(queue, monitored_func, args, kwargs):
    exception_info = store_any_exception(monitored_func, args, kwargs)
    if exception_info:
        queue.put(exception_info)


def terminate_process(process):
    while process.is_alive():
        process.terminate()


class TimeoutError(AssertionError):
    pass


class TimeoutDecorator(object):
    """A Decorator that will timeout a method or function by running it in a
    separate process

    Usage is very simple::

        import time
        from testkit import timeout

        @timeout(0.1)
        def test_that_fails():
            # This test will fail
            time.sleep(0.2)

    """
    def __init__(self, limit):
        self._limit = limit

    def __call__(self, f):
        @wraps(f)
        def run_timed_test(*args, **kwargs):
            queue = multiprocessing.Queue()
            process = multiprocessing.Process(target=monitoring_wrapper,
                    args=(queue, f, args, kwargs))
            process.start()
            process.join(self._limit)
            if process.is_alive():
                terminate_process(process)
                raise TimeoutError('Test timed out')
            try:
                exception_info = queue.get(block=False)
            except Queue.Empty:
                # Everything is fine then
                pass
            else:
                # Raise the error inside the process
                raise exception_info.reraise()
        return run_timed_test

timeout = TimeoutDecorator
