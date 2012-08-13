"""
tests.test_meta
~~~~~~~~~~~~~~~

Tests for the metaclass of MultiprocessTest
"""
from nose.tools import raises
import time
from mock import patch
from functools import wraps
from testkit.processes import *
from testkit import TimeoutError


def fake_decorator(f):
    @wraps(f)
    def wrappy(*args, **kwargs):
        print "DOING STUFFS"
        return f(*args, **kwargs)
    return wrappy


class SomethingGeneric(MultiprocessTest):
    timeout = 0.5

    @mp_runtime(raises(TimeoutError))
    def test_timeout(self):
        while True:
            pass

    @mp_runtime(raises(TimeoutError))
    @mp_timeout(0.1)
    def test_custom_timeout(self):
        time.sleep(0.6)

    @patch('os.path.abspath')
    def test_with_patch(self, mock_abspath):
        import os
        path = 'hello'
        os.path.abspath(path)

        mock_abspath.assert_called_with(path)


class TestOfTests(SomethingGeneric):
    wrappers = []

    def shared_options(self):
        return {'main': 'hello'}

    def setup(self, shared_options):
        # We can make assertions in the MultiprocessTest
        assert shared_options == {'main': 'hello'}

    def test_simple(self):
        assert 1 == 1
