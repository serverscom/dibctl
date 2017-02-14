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
        pytest.main('build/')


setup(
    name="dibctl",
    version="0.4.1",
    description="diskimage-builder control",
    author="George Shuklin",
    author_email="george.shuklin@gmail.com",
    url="http://github.com/serverscom/dibctl",
    packages=find_packages(),
    install_requires=[
        'PyYAML',
        'diskimage-builder',
        'keystoneclient',
        'glanceclient',
        'novaclient',
        'pytest-timeout',
        'jsonschema',
        'pytest' #not a mistake - we use pytest as part of the app
    ],
    include_package_data=True,
    package_data={'dibctl': ['docs/*', 'docs/example_configs/*', 'docs/tests_examples/shell_examples.d/*', 'docs/tests_examples/pytest_examples/*']},
    entry_points="""
        [console_scripts]
        dibctl=dibctl.commands:main
#    """,
    cmdclass={'test': PyTest},
    long_description="""diskimage-builder control"""
)
