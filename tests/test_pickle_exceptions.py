from mock import Mock
from nose.tools import raises
from testkit.exceptionutils import *


class CustomException(Exception):
    pass


@raises(CustomException)
def test_exception_raised_correctly():
    exception_info = store_any_exception(a_function)
    exception_info.reraise()


def test_exception_raised_correctly_with_args():
    mock_function = Mock()
    mock_function.side_effect = CustomException
    args = ['a', 'b', 'c']
    kwargs = dict(alpha='alpha')

    store_any_exception(mock_function, args, kwargs)

    mock_function.assert_called_with('a', 'b', 'c', alpha='alpha')


def a_function():
    raise CustomException('someexception')
