#!/usr/bin/python
import os
import inspect
import sys
import pytest
import mock
from mock import sentinel


@pytest.fixture
def config():
    from dibctl import config
    return config


def test_set_conf_name_forced_ok(config):
    with mock.patch.object(config.Config, "read_and_validate_config"):
        with mock.patch.object(config.Config, "_apply_overrides"):
            with mock.patch.object(config.os.path, "isfile", return_value=True) as isfile:
                c = config.Config(sentinel.my_config, {})
                assert c.config_file == sentinel.my_config
                assert isfile.called


def test_set_conf_name_forced_not_ok(config):
    with mock.patch.object(config.Config, "read_and_validate_config"):
        with mock.patch.object(config.Config, "_apply_overrides"):
            with mock.patch.object(config.os.path, "isfile", return_value=False) as isfile:
                with pytest.raises(config.ConfigNotFound):
                    config.Config(sentinel.bad_config, {})
                    assert isfile.called


def test_set_conf_default_name_not_ok(config):
    with mock.patch.object(config.Config, "read_and_validate_config"):
        with mock.patch.object(config.Config, "_apply_overrides"):
            with mock.patch.object(config.os.path, "isfile", return_value=False) as isfile:
                with mock.patch.object(config.Config, "DEFAULT_CONFIG_NAME", "name"):
                    with pytest.raises(config.ConfigNotFound):
                        config.Config()
                    assert isfile.call_count == len(config.Config.CONFIG_SEARCH_PATH)


@pytest.mark.parametrize("sequence, return_name", [
    [[True, False, False], './somename'],
    [[False, True, False], './dibctl/somename'],
    [[False, False, True], '/etc/dibctl/somename']
])
def test_set_conf_default_name_ok_3(config, sequence, return_name):
    with mock.patch.object(config.Config, "read_and_validate_config"):
        with mock.patch.object(config.Config, "_apply_overrides"):
            with mock.patch.object(config.Config, "DEFAULT_CONFIG_NAME", "somename"):
                with mock.patch.object(config.os.path, "isfile", side_effect=sequence):
                    c = config.Config()
                    assert c.config_file == return_name


def test_read_and_validate_config_simple(config):
    mock_config = mock.mock_open(read_data='[]')
    with mock.patch.object(config.Config, "_apply_overrides"):
        with mock.patch.object(config.Config, "DEFAULT_CONFIG_NAME", "foobar.yaml"):
            with mock.patch.object(config, "open", mock_config) as mock_open:
                with mock.patch.object(config.os.path, "isfile", return_value=True):
                    conf = config.Config()
                    assert conf.config == []
                    assert mock_open.call_args[0][0] == './foobar.yaml'


def test_get_ok(config):
    mock_config = mock.mock_open(read_data='{"image1":{"filename": "ok"}}')
    with mock.patch.object(config.Config, "_apply_overrides"):
        with mock.patch.object(config.Config, "DEFAULT_CONFIG_NAME", "name"):
            with mock.patch.object(config, "open", mock_config):
                with mock.patch.object(config.os.path, "isfile", return_value=True):
                    conf = config.Config()
                    assert conf.get('image1') == {"filename": "ok"}


def test_get_notok(config):
    mock_config = mock.mock_open(read_data='{"image1":{"filename": "ok"}}')
    with mock.patch.object(config.Config, "_apply_overrides"):
        with mock.patch.object(config.Config, "DEFAULT_CONFIG_NAME", "name"):
            with mock.patch.object(config, "open", mock_config):
                with mock.patch.object(config.os.path, "isfile", return_value=True):
                    conf = config.Config()
                    with pytest.raises(config.NotFoundInConfigError):
                        assert conf.get('image2')


def test_empty_apply_overrides(config):
    with mock.patch.object(config.Config, "read_and_validate_config"):
        with mock.patch.object(config.os.path, "isfile", return_value=True):
            with pytest.raises(TypeError):
                config.Config(sentinel.fake_file_name)


def test_imageconfig(config):
    mock_config = mock.mock_open(read_data='{"image1":{"filename": "ok"}}')
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
            conf = config.ImageConfig(overrides={'filename': 'new'})
            assert conf.get('image1') == {'filename': 'new'}
            assert conf.get('image2') == {'filename': 'new'}


def test_imageconfig_filename_override_absent(config):
    mock_config = mock.mock_open(read_data='{"image1":{"element": "ignore"}}')
    with mock.patch.object(config, "open", mock_config):
        with mock.patch.object(config.os.path, "isfile", return_value=True):
            conf = config.ImageConfig(overrides={'filename': 'new'})
            assert conf.get('image1')['filename'] == 'new'


def test_envconfig(config):
    mock_config = mock.mock_open(read_data='{"env1":{"filename": "ok"}}')
    with mock.patch.object(config, "open", mock_config) as mock_open:
        with mock.patch.object(config.os.path, "isfile", return_value=True):
            config.EnvConfig()
        assert mock_open.call_args[0][0] == './test-environments.yaml'


def test_envconfig_no_override(config):
    mock_config = mock.mock_open(read_data='{"env1":{"os_tenant_name": "somename"}}')
    with mock.patch.object(config, "open", mock_config):
        with mock.patch.object(config.os.path, "isfile", return_value=True):
            conf = config.EnvConfig()
            assert conf.get('env1')['os_tenant_name'] == 'somename'


def test_envconfig_filename_override(config):
    mock_config = mock.mock_open(read_data='{"env1":{"os_tenant_name": "bad"}, "env2":{"os_password":"bad"}}')
    with mock.patch.object(config, "open", mock_config):
        with mock.patch.object(config.os.path, "isfile", return_value=True):
            conf = config.EnvConfig(overrides={'os_tenant_name': 'new', 'os_password': 'other'})
            assert conf.get('env1')['os_tenant_name'] == 'new'
            assert conf.get('env2')['os_password'] == 'other'


def test_envconfig_filename_override_absent(config):
    mock_config = mock.mock_open(read_data='{"env1":{"os_tenant_name": "something"}}')
    with mock.patch.object(config, "open", mock_config):
        with mock.patch.object(config.os.path, "isfile", return_value=True):
            conf = config.EnvConfig(overrides={'os_password': 'pass'})
            assert conf.get('env1')['os_password'] == 'pass'


def notest_get_environment_not_ok(config):
    mock_config = mock.mock_open(read_data='{"env1":{ "os_tenant_name": "good_name"}}')
    with mock.patch.object(config, "open", mock_config):
        with mock.patch.object(config.os.path, "isfile", return_value=True):
            conf = config.Config()
            with pytest.raises(config.TestEnvironmentNotFoundInConfigError):
                conf.get_environment('env3')["os_tenant_name"]


if __name__ == "__main__":
    ourfilename = os.path.abspath(inspect.getfile(inspect.currentframe()))
    currentdir = os.path.dirname(ourfilename)
    parentdir = os.path.dirname(currentdir)
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
