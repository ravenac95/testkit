import os
import fudge
from nose.tools import raises
from testkit import *


def test_temp_directory():
    """Test temp directory correctly deletes"""
    with temp_directory() as temp_dir:
        pass
    assert os.path.exists(temp_dir) == False


def test_in_temp_directory():
    """Test CWD to temp directory"""
    with in_temp_directory() as temp_directory:
        assert os.getcwd() == temp_directory
    assert os.path.exists(temp_directory) == False


def test_in_temp_directory_write_file():
    """Test CWD to temp directory and create file there"""
    with in_temp_directory() as temp_directory:
        # Create a test file in the directory
        test_filename = "test_file.txt"
        test_file = open(test_filename, "w")
        # Put some random data in it
        random_data = random_string(15)
        test_file.write(random_data)
        test_file.close()
        # Attempt to open the file using the full path to the temp directory
        test_file_path = os.path.join(temp_directory, test_filename)
        # Verify contents
        verify_file = open(test_file_path)
        verify_data = verify_file.read()
        assert random_data == verify_data


class TestException(Exception):
    pass


def test_temp_directory_raises_error():
    raised_error = False
    try:
        with temp_directory() as temp_dir:
            raise TestException()
    except TestException:
        raised_error = True
    assert raised_error
    assert not os.path.exists(temp_dir)


@fudge.test
def test_shunt_mixin():
    """Create an object with the ShuntMixin"""
    class FakeClass(ShuntMixin):
        def my_method(self):
            return "before-shunt"

    obj = FakeClass()
    assert obj.my_method() == 'before-shunt'

    obj.__patch_method__('my_method').returns('after-shunt')
    assert obj.my_method() == 'after-shunt'


@raises(AssertionError)
@fudge.test
def test_shunt_mixin_raises_error():
    class FakeClass(ShuntMixin):
        def my_method(self):
            return "before-shunt"

    obj = FakeClass()
    obj.__patch_method__('my_method').with_args('test')
    obj.my_method()


@fudge.test
def test_shunt_mixin_has_no_expectation_on_patch():
    class FakeClass(ShuntMixin):
        def my_method(self):
            return "before-shunt"

    obj = FakeClass()
    (obj.__patch_method__('my_method', expects_call=False).returns('test')
                    .next_call().with_args('hello').returns('world'))
    assert obj.my_method() == 'test'


@fudge.test
def test_shunt_class_factory_method():
    class FakeClass(object):
        def my_method(self):
            return "before-shunt"
    ShuntClass = shunt_class(FakeClass)
    obj = ShuntClass()
    assert obj.my_method() == 'before-shunt'

    obj.__patch_method__('my_method').returns('after-shunt')
    assert obj.my_method() == 'after-shunt'


def test_dict_to_object():
    obj = dict_to_object(dict(a=1, b=2))
    assert obj.a == 1
    assert obj.b == 2
