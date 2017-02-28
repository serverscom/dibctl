#!/usr/bin/python
import os
import inspect
import sys
import pytest
import mock


ourfilename = os.path.abspath(inspect.getfile(inspect.currentframe()))
currentdir = os.path.dirname(ourfilename)
parentdir = os.path.dirname(currentdir)


@pytest.fixture
def config():
    from dibctl import config
    return config


@pytest.fixture
def commands():
    from dibctl import commands
    return commands


# this is integration test
# it uses 'docs/example_configs/upload.yaml' file to
# ensure that examples and code stay in sync
# plus this is a good way to store huge input data sample
# it mainly checks the schema but also all other
# bits related to 'forced config'. No mocks involved

images_yaml = os.path.join(parentdir, "docs/example_configs/images.yaml")
test_yaml = os.path.join(parentdir, "docs/example_configs/test.yaml")
upload_yaml = os.path.join(parentdir, "docs/example_configs/upload.yaml")


def test_integration_uploadenvconfig_schema_from_docs_example(config):
    config.UploadEnvConfig(upload_yaml)


def test_integration_testenvconfig_schema_from_docs_example(config):
    config.TestEnvConfig(test_yaml)


def test_integration_imageconfig_schema_from_docs_example(config):
    config.ImageConfig(images_yaml)


def test_call_actual_dibctl_validate(commands):
    with mock.patch.object(commands.sys, "exit") as mock_exit:
        commands.main([
            'validate',
            '--images-config', images_yaml,
            '--upload-config', upload_yaml,
            '--test-config', test_yaml
        ])
        assert mock_exit.call_args[0][0] == 0


if __name__ == "__main__":
    file_to_test = os.path.join(
        parentdir,
        os.path.basename(parentdir),
        os.path.basename(ourfilename).replace("test_", '')
    )
    pytest.main([
     "-vv"
     ] + sys.argv)
