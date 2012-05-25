from __future__ import with_statement
import os
from contextlib import contextmanager

class ChangedWorkingDirectory(object):
    def __init__(self, directory):
        self._directory = directory
        self._original_directory = os.getcwd()

    def __enter__(self):
        # Change the directory to the new cwd
        directory = self._directory
        # Change to the new directory
        os.chdir(directory)
        # Return the directory
        return directory

    def __exit__(self, ex_type, ex_value, traceback):
        # Return back to normal
        os.chdir(self._original_directory)

@contextmanager
def in_directory(directory):
    """Context manager for changing CWD to a directory

    Don't use this if you plan on writing files to the directory.
    This does not delete anything. It is purely to change the CWD
    """
    with ChangedWorkingDirectory(directory) as directory:
        yield directory
