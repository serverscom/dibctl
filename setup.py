#!/usr/bin/env python
from setuptools import setup, find_packages, Command
import sys
from dibctl import version

class PyTest(Command):
    user_options = [('pytest-args=', 'a', "Arguments to pass to py.test")]

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        import pytest
        print("Running unit tests")
        error_code = pytest.main([
			'build',
			'--ignore', 'build/doctest',
			'--ignore', 'build/tests/test_bad_configs.py',
			'--ignore', 'build/integration_tests'
		])
        if error_code:
            sys.exit(error_code)
        print("Running integration tests for docs examples")
        # doctests should be run against current dir, not 'build'
        # because config examples are not copied to build
        # (they are installed as config files)
        error_code = pytest.main(['doctest/'])
        if error_code:
            sys.exit(error_code)


setup(
    name="dibctl",
    version=version.VERSION,
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
        'pytest', # not a mistake - we use pytest as a part of the app
        'semantic_version',
        'requests',
        'urllib3'
    ],
    entry_points="""
        [console_scripts]
        dibctl=dibctl.commands:main
#    """,
    cmdclass={'test': PyTest},
    long_description="""diskimage-builder control"""
)
