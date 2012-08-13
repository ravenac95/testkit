from setuptools import setup, find_packages
import sys, os

VERSION = '0.1.6'

LONG_DESCRIPTION = open('README.rst').read()

setup(name='testkit',
    version=VERSION,
    description="testkit - A collection of tools for testing",
    long_description=LONG_DESCRIPTION,
    author='Reuven V. Gonzales',
    author_email='reuven@tobetter.us',
    url="https://github.com/ravenac95/testkit",
    license='MIT',
    platforms='Unix',
    packages=find_packages(exclude=['ez_setup', 'examples', 'tests']),
    include_package_data=True,
    zip_safe=False,
    install_requires=[
        'fudge',
    ],
    entry_points={},
    classifiers=[
        'License :: OSI Approved :: MIT License',
        'Intended Audience :: Developers',
        'Programming Language :: Python',
        'Operating System :: POSIX',
    ],
)
