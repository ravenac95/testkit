testkit - A collection of tools for testing
===========================================

This is a simple collection of test tools that have been developed out of need
for some projects. However, some of these tools needed to be duplicated so I
decided to consolidate them in this library.

Features
--------

- Provides a way to use context managers in setup/teardown of a test
- Provides a context manager for temporary directories
- Provides a way to create shunts via fudge

TODO
----

- Add docs

Developing
----------

Install virtstrap via pip. Please install this system wide::
    
    $ pip install virtstrap

Then cd to the project's root directory and do the following::
    
    $ vstrap init

You can then activate the virtualenv::
    
    $ . quickactivate
