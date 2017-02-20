#!/usr/bin/env python
from setuptools import setup, find_packages, Command

class PyTest(Command):
    user_options = [('pytest-args=', 'a', "Arguments to pass to py.test")]

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        import pytest
        print("Running unit tests")
        pytest.main(['build/'])
        print("Running integration tests for docs examples")
        pytest.main(['doctest/'])


setup(
    name="dibctl",
    version="0.4.3",
    description="diskimage-builder control",
    author="George Shuklin",
    author_email="george.shuklin@gmail.com",
    url="http://github.com/serverscom/dibctl",
    packages=find_packages(),
    install_requires=[
        'PyYAML',
        'diskimage-builder',
        'keystoneauth1',
        'python-glanceclient',
        'python-novaclient',
        'pytest-timeout',
        'jsonschema',
        'pytest' # not a mistake - we use pytest as a part of the app
    ],
    entry_points="""
        [console_scripts]
        dibctl=dibctl.commands:main
#    """,
    cmdclass={'test': PyTest},
    long_description="""diskimage-builder control"""
)
