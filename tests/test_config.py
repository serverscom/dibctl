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


def test_set_conf_name_not_found_forced(config):
    c = config.Config({}, sentinel.name)
    with mock.patch.object(config.os.path, "isfile", return_value=False):
        with pytest.raises(config.ConfigNotFound):
            c.set_conf_name('foo')


def test_set_conf_name_not_found_natural(config):
    with mock.patch.object(config.os.path, "isfile", return_value=False):
        with pytest.raises(config.ConfigNotFound):
            config.ImageConfig()


def test_imageconfig(config):
    mock_config = mock.mock_open(read_data='{"image1": {"filename": "ok"}}')
    with mock.patch.object(config, "open", mock_config) as mock_open:
        with mock.patch.object(config.os.path, "isfile", return_value=True):
            config.ImageConfig()
        assert mock_open.call_args[0][0] == './images.yaml'


def test_imageconfig_with_defaults(config):
    mock_config = mock.mock_open(read_data='{"image1":{"filename": "ok"}}')
    with mock.patch.object(config, "open", mock_config):
        with mock.patch.object(config.os.path, "isfile", return_value=True):
            conf = config.ImageConfig()
            assert conf.get('image1') == {'filename': 'ok'}


def test_imageconfig_filename(config):
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
    '{foo: {filename: x, glance: {properties:{foo: bar}}}}'

])
def test_imageconfig_schema_good(config, good_config):
    mock_config = mock.mock_open(read_data=good_config)
    with mock.patch.object(config, "open", mock_config):
        with mock.patch.object(config.os.path, "isfile", return_value=True):
            config.ImageConfig("mock_config_name")


def test_config_get_simple(config):
    good_config = '{foo: {filename: x}}'
    mock_config = mock.mock_open(read_data=good_config)
    with mock.patch.object(config, "open", mock_config):
        with mock.patch.object(config.os.path, "isfile", return_value=True):
            c = config.ImageConfig("mock_config_name")
            assert c.get('foo') == {'filename': 'x'}


@pytest.mark.parametrize("path, value", [
    ['baz', {'filename': 'y'}],
    ['baz.filename', 'y'],
    ['foo.glance', {'properties': {'foo': 'bar'}}],
    ['foo.glance.properties', {'foo': 'bar'}],
    ['foo.glance.properties.foo', 'bar']
])
def test_config_get_dotted(config, path, value):
    good_config = '{foo: {filename: x, glance: {properties:{foo: bar}}}, baz: {filename: y}}'
    mock_config = mock.mock_open(read_data=good_config)
    with mock.patch.object(config, "open", mock_config):
        with mock.patch.object(config.os.path, "isfile", return_value=True):
            c = config.ImageConfig("mock_config_name")
            assert c.get(path) == value


@pytest.mark.parametrize("path, value", [
    ['baz', {'filename': 'y'}],
    ['baz.filename', 'y'],
    ['foo.glance', {'properties': {'foo': 'bar'}}],
    ['foo.glance.properties', {'foo': 'bar'}],
    ['foo.glance.properties.foo', 'bar']
])
def test_config_getitem_dotted(config, path, value):
    good_config = '{foo: {filename: x, glance: {properties:{foo: bar}}}, baz: {filename: y}}'
    mock_config = mock.mock_open(read_data=good_config)
    with mock.patch.object(config, "open", mock_config):
        with mock.patch.object(config.os.path, "isfile", return_value=True):
            c = config.ImageConfig("mock_config_name")
            assert c[path] == value


@pytest.mark.parametrize("path", [
    'bad',
    'foo.bad',
    'foo.glance.bad',
    'foo.glance.properties.bad'
])
def test_config_get_default(config, path):
    good_config = '{foo: {filename: x, glance: {properties:{foo: bar}}}}'
    mock_config = mock.mock_open(read_data=good_config)
    with mock.patch.object(config, "open", mock_config):
        with mock.patch.object(config.os.path, "isfile", return_value=True):
            c = config.ImageConfig("mock_config_name")
            assert c.get(path, sentinel.notfound) == sentinel.notfound


@pytest.mark.parametrize("path", [
    'bad',
    'foo.bad',
    'foo.glance.bad',
    'foo.glance.properties.bad'
])
def test_config_getitem_error(config, path):
    good_config = '{foo: {filename: x, glance: {properties:{foo: bar}}}}'
    mock_config = mock.mock_open(read_data=good_config)
    with mock.patch.object(config, "open", mock_config):
        with mock.patch.object(config.os.path, "isfile", return_value=True):
            c = config.ImageConfig("mock_config_name")
            with pytest.raises(config.NotFoundInConfigError):
                c[path]


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


@pytest.mark.parametrize("input, query, result", [
    [{}, 'foo', False],
    [{'a': 1}, 'a', True],
    [{'a': {'b': 2}}, "a.b", True]
])
def test_config_in(config, input, query, result):
    c = config.Config(input, sentinel.name)
    c.config_file = 'foo'
    assert (query in c) is result


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


@pytest.mark.parametrize('conf1, conf2, path, result', [
    [{'a': 1}, {'a': 2}, 'a', 2],
    [{'a': 2}, {'a': 1}, 'a', 2],
    [{'a': 2}, {}, 'a', 2],
    [{}, {'a': 100}, 'a', 100],
    [{}, {}, 'a', 99],
    [{'a': {'b': 2}}, {}, 'a.b', 2],
])
def test_get_max(config, conf1, conf2, path, result):
    c1 = config.Config(conf1, sentinel.name)
    c2 = config.Config(conf2, sentinel.name)
    assert config.get_max(c1, c2, path, 99) == result


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
