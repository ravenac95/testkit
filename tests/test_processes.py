import time
import zmq
from nose.tools import raises, eq_, istest
from testkit.processes import *


class CustomException(Exception):
    pass


class SomeProcess(ProcessWrapper):
    def shared_options(self):
        return {'someproc': 'hello'}

    def run(self):
        while True:
            time.sleep(1.0)


class ZMQProcess(ProcessWrapper):
    def shared_options(self):
        context = zmq.Context()
        server_socket = context.socket(self.socket_type)
        server_uri = self.initial_options.get('server_uri')
        print server_uri
        if server_uri:
            server_socket.bind(server_uri)
        else:
            port = server_socket.bind_to_random_port('tcp://127.0.0.1')
            server_uri = 'tcp://127.0.0.1:%s' % port
        self.server_socket = server_socket
        return {'server_uri': server_uri}


class EchoServerProcess(ZMQProcess):
    socket_type = zmq.REP

    def run(self):
        while True:
            msg = self.server_socket.recv()
            self.server_socket.send(msg)


class ServerThatHangs(ZMQProcess):
    socket_type = zmq.REP

    def run(self):
        self.server_socket.recv()
        while True:
            # Fake hang
            time.sleep(1.0)


class BadProcess(ProcessWrapper):
    def run(self):
        raise CustomException('Exception')


class SomeOtherProcess(ProcessWrapper):
    def shared_options(self):
        return {'otherproc': 'world'}

    def run(self):
        while True:
            time.sleep(1.0)


def initial_options():
    return {'hello': 'world'}


@multiprocess([SomeProcess], initial_options, limit=3.0)
def test_initial_options_are_correct(initial, shared):
    eq_(initial, {'hello': 'world'})


@raises(CustomException)
@multiprocess([SomeProcess, SomeOtherProcess], limit=3.0)
def test_exceptions(initial, shared):
    raise CustomException("CustomException")


@multiprocess([SomeProcess], limit=3.0)
def test_options_are_correct(initial, shared):
    eq_(shared, {'someproc': 'hello'})


@multiprocess([SomeProcess, SomeOtherProcess], limit=3.0)
def test_combined_options_are_correct(initial, shared):
    eq_(shared, {'someproc': 'hello', 'otherproc': 'world'})


@raises(AssertionError)
@multiprocess([SomeProcess, SomeOtherProcess], limit=0.5)
def test_times_out(initial, shared):
    time.sleep(2.0)


@raises(CustomException)
@multiprocess([SomeProcess, BadProcess], limit=3.0)
def test_exception_in_other_process(initial, shared):
    time.sleep(4.0)


@multiprocess([SomeProcess, SomeProcess, SomeProcess, SomeProcess,
    SomeProcess, SomeProcess, SomeProcess], limit=3.0)
def test_with_many_processes(*args):
    pass


@multiprocess([EchoServerProcess], limit=3.0)
def test_with_echo_server(initial, shared):
    context = zmq.Context()
    socket = context.socket(zmq.REQ)
    socket.connect(shared['server_uri'])

    socket.send('hello')
    eq_(socket.recv(), 'hello')

    socket.send('world')
    eq_(socket.recv(), 'world')


@raises(AssertionError)
@multiprocess([ServerThatHangs], limit=1.5)
def test_with_server_that_hangs(initial, shared):
    context = zmq.Context()
    socket = context.socket(zmq.REQ)
    socket.connect(shared['server_uri'])

    socket.send('what')
    socket.recv()


class TestWithClassSetup(object):
    def setup(self):
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REQ)
        self.socket.connect('tcp://127.0.0.1:5432')

    def in_process_setup(self):
        pass

    @multiprocess([EchoServerProcess],
            lambda: {'server_uri': 'tcp://127.0.0.1:5432'},
            limit=3.0)
    def test_with_echo_server(self, initial, shared):
        context = zmq.Context()
        socket = context.socket(zmq.REQ)
        socket.connect(shared['server_uri'])

        socket.send('hello')
        eq_(socket.recv(), 'hello')

        socket.send('world')
        eq_(socket.recv(), 'world')


class TestWithMethodAsDescriptor(object):
    wrappers = [EchoServerProcess]

    @multiprocess_method(3.0)
    def test_what(self):
        assert 1 == 2
