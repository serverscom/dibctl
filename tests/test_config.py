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
    '{"foo": "bar"}',  # must be object
    '{"foo": {}}',  # no filename
    '{"foo": {random: junk}}',  # no unknown things should be here
    '{"foo": {"filename": "x", "glance": {"upload_timeout": "3"}}}',  # timeout should be int
    '{"foo": {"filename": "x", "glance": {"name": 1}}}',  # name should be string
    '{"foo": {"filename": "x", "dib": {}}}',  # no elements
    '{"foo": {"filename": "//"}}',  # bad path
    '{foo: {filename: x, dib: {elements: []}}}',  # elements shoudn't be empty
    '{foo: {filename: x, dib: {elements: [1]}}}',  # elements should be strings
    '{foo: {filename: x, nova: {flavor: 3}}}',  # flavors are not allowed in images
    '{foo: {filename: x, glance: {api_version: 2}}}',  # version 2 is not supported yet
    '{foo: {filename: x, glance: {name: 1}}}',  # name should be string
    '{foo: {filename: x, glance: {properties:[foo, bar]}}}',  # properties should be an object
])
def test_imageconfig_schema_bad(config, bad_config):
    mock_config = mock.mock_open(read_data=bad_config)
    with mock.patch.object(config, "open", mock_config):
        with mock.patch.object(config.os.path, "isfile", return_value=True):
            with pytest.raises(config.InvaidConfigError):
                config.ImageConfig("mock_config_name")


@pytest.mark.parametrize('good_config', [
    '{foo: {filename: x}}',
    '{foo: {filename: x}, bar: {filename: y}}',
    '{foo: {filename: x, dib: {elements: [el1, el2]}}}',
    '{foo: {filename: x, nova: {}}}',
    '{foo: {filename: x, nova: {active_timeout: 10}}}',
    '{foo: {filename: x, glance: {}}}',
    '{foo: {filename: x, glance: {api_version: 1}}}',
    '{foo: {filename: x, glance: {name: foo}}}',
    '{foo: {filename: x, glance: {properties:{foo: bar}}}}',
])
def test_imageconfig_schema_good(config, good_config):
    mock_config = mock.mock_open(read_data=good_config)
    with mock.patch.object(config, "open", mock_config):
        with mock.patch.object(config.os.path, "isfile", return_value=True):
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
