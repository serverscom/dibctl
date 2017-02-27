#!/usr/bin/python
import os
import inspect
import sys
import pytest


ourfilename = os.path.abspath(inspect.getfile(inspect.currentframe()))
currentdir = os.path.dirname(ourfilename)
parentdir = os.path.dirname(currentdir)


@pytest.fixture
def config():
    from dibctl import config
    return config

# this is integration test
# it uses 'docs/example_configs/upload.yaml' file to
# ensure that examples and code stay in sync
# plus this is a good way to store huge input data sample
# it mainly checks the schema but also all other
# bits related to 'forced config'. No mocks involved


def test_integration_uploadenvconfig_schema_from_docs_example(config):
    config.UploadEnvConfig(os.path.join(parentdir, "docs/example_configs/upload.yaml"))


def test_integration_testenvconfig_schema_from_docs_example(config):
    config.TestEnvConfig(os.path.join(parentdir, "docs/example_configs/test.yaml"))


def test_integration_imageconfig_schema_from_docs_example(config):
    config.ImageConfig(os.path.join(parentdir, "docs/example_configs/images.yaml"))


if __name__ == "__main__":
    file_to_test = os.path.join(
        parentdir,
        os.path.basename(parentdir),
        os.path.basename(ourfilename).replace("test_", '')
    )
    pytest.main([
     "-vv"
     ] + sys.argv)
