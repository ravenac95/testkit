from nose.tools import *
from testkit.utils import *
from tests import fixtures_path

class TestException(Exception):
    pass

def test_in_directory():
    """Test change CWD to a specific directory"""
    original_working_dir = os.getcwd()
    sample_dir = fixtures_path('sample_dir')
    with in_directory(sample_dir):
        assert os.getcwd() != original_working_dir, "CWD is still the original"
        assert sample_dir == os.path.abspath('.')
    assert sample_dir != os.path.abspath('.')
    assert os.getcwd() == original_working_dir, "CWD did not revert to original"

def test_in_directory_raises_error():
    raised_error = False
    original_working_dir = os.getcwd()
    sample_dir = fixtures_path('sample_dir')
    try:
        with in_directory(sample_dir):
            raise TestException()
    except TestException:
        raised_error = True
    assert raised_error == True, "An error was not raised"
    assert os.getcwd() == original_working_dir, "CWD did not revert to original"
