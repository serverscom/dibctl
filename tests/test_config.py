#!/usr/bin/python
import os
import inspect
import sys
import pytest
import mock
from mock import sentinel

ourfilename = os.path.abspath(inspect.getfile(inspect.currentframe()))
currentdir = os.path.dirname(ourfilename)
parentdir = os.path.dirname(currentdir)


@pytest.fixture
def config():
    from dibctl import config
    return config


def test_imageconfig(config):
    mock_config = mock.mock_open(read_data='{"image1": {"filename": "ok"}}')
    with mock.patch.object(config, "open", mock_config) as mock_open:
        with mock.patch.object(config.os.path, "isfile", return_value=True):
            config.ImageConfig()
        assert mock_open.call_args[0][0] == './images.yaml'


def test_imageconfig_no_override(config):
    mock_config = mock.mock_open(read_data='{"image1":{"filename": "ok"}}')
    with mock.patch.object(config, "open", mock_config):
        with mock.patch.object(config.os.path, "isfile", return_value=True):
            conf = config.ImageConfig()
            assert conf.get('image1') == {'filename': 'ok'}


def test_imageconfig_filename_override(config):
    mock_config = mock.mock_open(read_data='{"image1":{"filename": "bad"}, "image2":{"filename":"bad"}}')
    with mock.patch.object(config, "open", mock_config):
        with mock.patch.object(config.os.path, "isfile", return_value=True):
            conf = config.ImageConfig(filename='new')
            assert conf.get('image1') == {'filename': 'new'}
            assert conf.get('image2') == {'filename': 'new'}


@pytest.mark.parametrize('bad_config', [
    '{"foo": "bar"}',
    '{"foo": {}}',
    '{"foo": {"filename": "x", "glance": {"upload_timeout": "3"}}}',
    '{"foo": {"filename": "x", "glance": {"name": 1}}}',
    '{"foo": {"filename": "x", "dib": {}}}'
])
def test_imageconfig_schema_bad(config, bad_config):
    mock_config = mock.mock_open(read_data=bad_config)
    with mock.patch.object(config, "open", mock_config):
        with mock.patch.object(config.os.path, "isfile", return_value=True):
            with pytest.raises(config.InvaidConfigError):
                config.ImageConfig("mock_config_name")


def test_testenvconfig(config):
    mock_config = mock.mock_open(read_data='{}')
    with mock.patch.object(config, "open", mock_config) as mock_open:
        with mock.patch.object(config.os.path, "isfile", return_value=True):
            config.TestEnvConfig()
        assert mock_open.call_args[0][0] == './test.yaml'


def notest_get_environment_not_ok(config):
    mock_config = mock.mock_open(read_data='{"env1":{ "os_tenant_name": "good_name"}}')
    with mock.patch.object(config, "open", mock_config):
        with mock.patch.object(config.os.path, "isfile", return_value=True):
            conf = config.Config()
            with pytest.raises(config.TestEnvironmentNotFoundInConfigError):
                conf.get_environment('env3')["os_tenant_name"]


@pytest.mark.parametrize('bad_config', [
    '{"foo": "bar"}',
    '{"foo": {}}',
    '{"foo": {keystone: {}}}',
    '{"foo": {keystone: {api_version: 4}}}',
    '{"foo": {keystone: {}, nova: {}}}',
    '{"foo": {keystone: {}, nova: {nics: [], flavor: foo}}}',
    '{"foo": {keystone: {}, nova: {flavor: foo, nics: [{net_id: 27c642c-invalid-uuid}]}}}'
])
def test_testenv_config_schema_bad(config, bad_config):
    mock_config = mock.mock_open(read_data=bad_config)
    with mock.patch.object(config, "open", mock_config):
        with mock.patch.object(config.os.path, "isfile", return_value=True):
            with pytest.raises(config.InvaidConfigError):
                config.TestEnvConfig("mock_config_name")


@pytest.mark.parametrize('bad_config', [
    '{"foo": "bar"}',
    '{"foo": {}}',
    '{"foo": {"keystone": {"api_version": 4}}}',
    '{"foo": {"glance": {}}}'
])
def test_uploadenv_config_schema_bad(config, bad_config):
    mock_config = mock.mock_open(read_data=bad_config)
    with mock.patch.object(config, "open", mock_config):
        with mock.patch.object(config.os.path, "isfile", return_value=True):
            with pytest.raises(config.InvaidConfigError):
                config.UploadEnvConfig("mock_config_name")


if __name__ == "__main__":
    file_to_test = os.path.join(
        parentdir,
        os.path.basename(parentdir),
        os.path.basename(ourfilename).replace("test_", '')
    )
    pytest.main([
     "-vv",
     "--cov", file_to_test,
     "--cov-report", "term-missing"
     ] + sys.argv)
