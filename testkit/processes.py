"""
testkit.processes
~~~~~~~~~~~~~~~~~

Create and manage multiple processes for a test. This can also communicate
errors between the processees. A test has four stages:

    1. Shared setup options stage (compile options from all processes)
    2. Process setup (using the shared options setup all processes)
    3. Run Test
    4. Teardown
"""
import multiprocessing
import Queue
import time
import inspect
from functools import wraps, partial
from .exceptionutils import PicklableExceptionInfo
from .timeouts import TimeoutError


class ProcessTimedOut(Exception):
    pass


class ProcessWrapper(object):
    def __init__(self, initial_options, options_queue, exception_queue,
            shared_options_queue, process_ready_event, run_event):
        self.initial_options = initial_options
        self._options_queue = options_queue
        self._exception_queue = exception_queue
        self._shared_options_queue = shared_options_queue
        self._process_ready_event = process_ready_event
        self._run_event = run_event

    def shared_options(self):
        """Override and return a dictionary containing data that you'd like to
        share among other wrappers

        """
        return {}

    def setup(self, shared_options):
        """Setup method"""
        pass

    def run_process(self):
        """Run the processes three stages"""
        try:
            options = self.shared_options()
            self._options_queue.put(options)
            shared_options = self._shared_options_queue.get()
            self.setup(shared_options)
            self._process_ready_event.set()
            self._run_event.wait()
            self.run()
        except:
            exc_info = PicklableExceptionInfo.exc_info()
            self._exception_queue.put(exc_info)
        finally:
            self.teardown()

    def run(self):
        """The only required method to define in a subclass"""
        raise NotImplementedError()

    def teardown(self):
        """Teardown method"""
        pass


def start_process(wrapper_cls, *args, **kwargs):
    wrapper = wrapper_cls(*args, **kwargs)
    wrapper.run_process()


class ProcessMonitor(object):
    @classmethod
    def new_process(cls, wrapper_cls, initial_options, timeout=5):
        options_queue = multiprocessing.Queue()
        exception_queue = multiprocessing.Queue()
        shared_options_queue = multiprocessing.Queue()
        process_ready_event = multiprocessing.Event()
        run_event = multiprocessing.Event()
        process = multiprocessing.Process(target=start_process,
            args=(wrapper_cls, initial_options, options_queue,
                exception_queue, shared_options_queue, process_ready_event,
                run_event))
        process.start()
        name = wrapper_cls.__name__
        return cls(name, process, options_queue, exception_queue,
                shared_options_queue, process_ready_event, run_event,
                timeout)

    def __init__(self, name, process, options_queue, exception_queue,
            shared_options_queue, process_ready_event, run_event,
            timeout):
        self._name = name
        self._process = process
        self._options_queue = options_queue
        self._exception_queue = exception_queue
        self._shared_options_queue = shared_options_queue
        self._process_ready_event = process_ready_event
        self._run_event = run_event
        self._timeout = timeout

    @property
    def name(self):
        return self._name

    def _send_to_queue(self, queue, data, error=None):
        error = 'Timed out waiting for process "%s"' % self._name
        try:
            queue.put(data, timeout=self._timeout)
        except Queue.Full:
            raise ProcessTimedOut(error)

    def _receive_from_queue(self, queue):
        error = 'Timed out waiting for process "%s"' % self._name
        try:
            data = queue.get(timeout=self._timeout)
        except Queue.Empty:
            raise ProcessTimedOut(error)
        return data

    def get_process_options(self):
        return self._receive_from_queue(self._options_queue)

    def send_shared_options(self, shared_options):
        self._send_to_queue(self._shared_options_queue, shared_options)

    def is_process_ready(self):
        return self._process_ready_event.wait(0.5)

    def run(self):
        self._run_event.set()

    def join(self, timeout):
        process = self._process
        process.join(timeout)
        if not process.is_alive():
            # Check for any exceptions if the process is no longer alive
            self.check_for_exceptions()

    def check_for_exceptions(self):
        try:
            exception_info = self._exception_queue.get(block=False)
        except Queue.Empty:
            pass
        else:
            exception_info.reraise()

    def is_alive(self):
        return self._process.is_alive()

    def terminate(self):
        while self._process.is_alive():
            self._process.terminate()


class ProcessManagerError(Exception):
    pass


class ProcessManager(object):
    @classmethod
    def from_wrappers(cls, wrappers, initial_options, timeout=5,
            wait_timeout=0.1, runtime_timeout=0):
        return cls(wrappers, initial_options, timeout, wait_timeout,
                runtime_timeout)

    def __init__(self, wrappers, initial_options, timeout, wait_timeout,
            runtime_timeout):
        self._wrappers = wrappers
        self._initial_options = initial_options
        self._timeout = timeout
        self._wait_timeout = wait_timeout
        self._runtime_timeout = runtime_timeout
        self._monitors = None

    @property
    def monitors(self):
        monitors = self._monitors
        if monitors is None:
            monitors = []
            for wrapper_cls in self._wrappers:
                monitor = ProcessMonitor.new_process(wrapper_cls,
                    self._initial_options, timeout=self._timeout)
                monitors.append(monitor)
            self._monitors = monitors
        return monitors

    def run(self):
        # Combine processes options into shared options
        try:
            shared_options = self._get_shared_options()
            self._check_processes_ok()
            # Send shared options to all processes
            self._send_shared_options(shared_options)
            self._check_processes_ok()
            # Wait till all processes are ready
            self._wait_till_ready()
            self._check_processes_ok()
            # Start all processes
            self._start_processes()
            self._check_processes_ok()
            # Wait for all processes
            self._wait()
        finally:
            self._stop_processes()

    def _check_processes_ok(self):
        monitors = self.monitors
        for monitor in monitors:
            if not monitor.is_alive():
                monitor.check_for_exceptions()
                raise ProcessManagerError('Process "%s" has died prematurely' %
                        monitor.name)

    def _get_shared_options(self):
        monitors = self.monitors
        shared_options = {}
        for monitor in monitors:
            options = monitor.get_process_options()
            shared_options.update(options)
        return shared_options

    def _send_shared_options(self, shared_options):
        monitors = self.monitors
        for monitor in monitors:
            monitor.send_shared_options(shared_options)

    def _wait_till_ready(self):
        monitors = self.monitors
        not_ready = True

        while not_ready:
            not_ready = False
            for monitor in monitors:
                self._check_processes_ok()
                if not monitor.is_process_ready():
                    not_ready = True

    def _start_processes(self):
        monitors = self.monitors
        for monitor in monitors:
            monitor.run()

    def _wait(self):
        monitors = self.monitors
        runtime_timeout_ms = self._runtime_timeout * 1000
        start_time = time.time() * 1000
        while True:
            if runtime_timeout_ms:
                current_time = time.time() * 1000
                time_diff = current_time - start_time
                if time_diff >= runtime_timeout_ms:
                    raise TimeoutError('Runtime for processes timed out')
            for monitor in monitors:
                monitor.join(self._wait_timeout)
                if not monitor.is_alive():
                    return

    def _stop_processes(self):
        monitors = self.monitors
        for monitor in monitors:
            monitor.terminate()


def create_main_process_wrapper(f, args, kwargs):
    new_args = list(args)

    class MainTestWrapper(ProcessWrapper):
        def setup(self, shared_options):
            self._shared_options = shared_options

        def run(self):
            new_args.append(self._shared_options)
            f(*new_args, **kwargs)
    return MainTestWrapper


def create_process_wrapper(f, args, kwargs, shared_options=None,
        setup=None, teardown=None):
    shared_options_m = shared_options.im_func or (lambda self: {})
    setup_m = setup.im_func or (lambda self, shared_options: None)
    teardown_m = (lambda self: None)

    class ATestWrapper(ProcessWrapper):
        setup = setup_m
        teardown = teardown_m
        shared_options = shared_options_m

        def run(self):
            f(self, *args, **kwargs)
    return ATestWrapper


class MultiprocessDecorator(object):
    def __init__(self, wrappers, initial_options=None, limit=30):
        self._limit = limit
        self._wrappers = wrappers
        self.initial_options = initial_options or (lambda: {})

    def __call__(self, f):
        @wraps(f)
        def run_multiprocess_test(*args, **kwargs):
            initial_options = self.initial_options()
            new_args = list(args)
            new_args.append(initial_options)
            main_wrapper = create_main_process_wrapper(f, new_args, kwargs)
            wrappers_copy = self._wrappers[:]
            wrappers_copy.append(main_wrapper)

            manager = ProcessManager.from_wrappers(wrappers_copy,
                    initial_options, runtime_timeout=self._limit)
            manager.run()
        return run_multiprocess_test

multiprocess = MultiprocessDecorator


class MultiprocessTestProxy(object):
    pass


def _proxy_method(self):
    pass


class MultiprocessTestMeta(type):
    def __init__(cls, name, bases, dct):
        super(MultiprocessTestMeta, cls).__init__(name, bases, dct)
        new_bases = []
        for base in bases:
            # Skip all of the subclasses where this is the metaclass
            proxied_test_base = getattr(base, '_ProxiedTestClass', None)
            if proxied_test_base:
                base = proxied_test_base
            new_bases.append(base)
        new_bases = tuple(new_bases)
        new_dct = {}
        for attr_name, attr_value in dct.iteritems():
            if attr_name.startswith('_'):
                continue
            new_dct[attr_name] = attr_value
        setattr(cls, '_ProxiedTestClass', type('%sProxiedTests' % name,
                new_bases, new_dct))
        setattr(cls, '_ignore_names', ['setup', 'teardown'])


def localattr(self, name):
    return object.__getattribute__(self, name)


class MultiprocessWrappedTest(object):
    pass


def create_multiprocess_wrapper(proxied_test, name, args, kwargs):
    class MultiprocessWrapper(ProcessWrapper):
        def __init__(self, *args, **kwargs):
            super(MultiprocessWrapper, self).__init__(*args, **kwargs)
            self._proxied_test = proxied_test

        def shared_options(self):
            return self._proxied_test.shared_options()

        def setup(self, shared_options):
            self._proxied_test.setup(shared_options)

        def teardown(self):
            self._proxied_test.teardown()

        def run(self):
            method = getattr(self._proxied_test, name)
            method(*args, **kwargs)
    return MultiprocessWrapper


class MultiprocessTest(object):
    """Provides a simple definition for multiprocess tests.

    .. warning::
        This class's metaclass does not copy any attributes that begin with
        ``_`` so these attributes are not correctly passed on to the proxied
        test.
    """
    __metaclass__ = MultiprocessTestMeta

    wrappers = []
    timeout = 2.0

    def __init__(self):
        proxied_test_cls = self._ProxiedTestClass
        self._proxied_test = proxied_test_cls()

    def __getattribute__(self, name):
        ignore_names = localattr(self, '_ignore_names')
        if name.startswith('_'):
            return super(MultiprocessTest, self).__getattribute__(name)
        elif name in ignore_names:
            raise AttributeError('"%s" cannot be accessed' % name)
        proxied_test = self._ProxiedTestClass()
        proxied_value = getattr(proxied_test, name)
        if inspect.ismethod(proxied_value):
            test_timeout = getattr(proxied_value, '_timeout', self.timeout)

            @wraps(proxied_value)
            def wrapped_func(self, *args, **kwargs):
                main_wrapper = create_multiprocess_wrapper(
                        proxied_test, name, args, kwargs)
                wrappers = self.wrappers[:]
                wrappers.append(main_wrapper)

                initial_options = proxied_test.initial_options()

                manager = ProcessManager.from_wrappers(wrappers,
                    initial_options, runtime_timeout=test_timeout)
                manager.run()
            runtime_decorators = getattr(proxied_value, '_runtime_decorators',
                    [])
            for decorator in runtime_decorators:
                wrapped_func = decorator(wrapped_func)
            return partial(wrapped_func, self)
        return proxied_value

    def shared_options(self):
        return {}

    def setup(self, shared_options):
        pass

    def teardown(self):
        pass

    def initial_options(self):
        return {}


def mp_runtime(decorator):
    """Defers some decorators to be evaluated for the runtime of a test within
    a MultiprocessTest.

    This is made for decorators you'd like to apply to the test as a whole. The
    best example of this is for nose.tools.raises decorator. See below::

        from nose.tools import raises
        from testkit import MultiprocessTest, mp_runtime, TimeoutError

        class TestThisThing(MultiprocessTest):
            @mp_runtime(raises(TimeoutError))
            def test_times_out(self):
                while True:
                    pass

    """
    def internal_runtime(f):
        runtime_decorators = getattr(f, '_runtime_decorators', [])
        runtime_decorators.append(decorator)
        f._runtime_decorators = runtime_decorators
        return f
    return internal_runtime


def mp_timeout(timeout):
    """Specify a timeout for a test within a MultiprocessTest"""
    def internal_timeout(f):
        f._timeout = timeout
        return f
    return internal_timeout
