import time
from nose.tools import raises
from testkit.timeouts import timeout


@raises(AssertionError)
@timeout(0.05)
def test_timeout():
    time.sleep(0.1)


@raises(AssertionError)
@timeout(0.05)
def test_timeout_with_infinite_loop():
    while True:
        time.sleep(0.001)


@timeout(0.5)
def test_timeout_no_errors():
    pass
