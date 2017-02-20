#!/usr/bin/python
import os
import inspect
import sys
import pytest
import mock
from mock import sentinel
import argparse


@pytest.fixture
def commands():
    from dibctl import commands
    return commands


@pytest.fixture
def cred():
    return {
        'os_auth_url': 'mock',
        'os_tenant_name': 'mock',
        'os_username': 'mock',
        'os_password': 'mock'
    }


@pytest.fixture
def mock_image_cfg():
    image = {
        'glance': {
            'name': 'foo'
        },
        'filename': sentinel.filename
    }
    return image


@pytest.fixture
def mock_env_cfg():
    env = {
        'keystone': {
            'auth_url': sentinel.auth,
            'tenant_name': sentinel.tenant,
            'password': sentinel.password,
            'username': sentinel.user
        },
        'nova': {
            'flavor': 'example',
            'nics': [
                {'net-id': sentinel.net_id}
            ]
        }
    }
    return env


def create_subparser(ParserClass):
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(title='commands')
    inst = ParserClass(subparsers)
    return parser, inst


@pytest.mark.parametrize('args, expected', [
    [['generic', '--debug'], True],
    [['generic'], False]
])
def test_GenericCommand_debug(commands, args, expected):
    parser = create_subparser(commands.GenericCommand)[0]
    args = parser.parse_args(args)
    assert args.debug == expected
    assert args.command.__func__ == commands.GenericCommand.command.__func__


def test_GenericCommand_no_command(commands):
    parser = create_subparser(commands.GenericCommand)[0]
    args = parser.parse_args(['generic'])
    with pytest.raises(NotImplementedError):
        args.command(sentinel.args)


@pytest.mark.parametrize('name, dname', [
    ('OS_AUTH_URL', 'os_auth_url'),
    ('OS_TENANT_NAME', 'os_tenant_name'),
    ('OS_USERNAME', 'os_username'),
    ('OS_PASSWORD', 'os_password')
])
def test_GenericCommand_set_overrides_from_env(commands, capsys, name, dname):
    parser, gen_comm = create_subparser(commands.GenericCommand)
    mock_env = {name: 'test_value'}
    with mock.patch.object(commands.os, "environ", mock_env):
        gen_comm.set_overrides_from_env()
        assert gen_comm.env_overrides[dname] == 'test_value'
        s_in = capsys.readouterr()[0]
        assert name in s_in
        assert dname in s_in


def test_GenericCommand_set_overrides_from_env_empty(commands, capsys):
    parser, gen_comm = create_subparser(commands.GenericCommand)
    mock_env = {}
    with mock.patch.object(commands.os, "environ", mock_env):
        gen_comm.set_overrides_from_env()
        s_in = capsys.readouterr()[0]
        assert len(s_in) == 0
        assert gen_comm.overrides == {}


def test_GenericCommand_get_from_config_normal(commands):
    mock_Cfg = mock.MagicMock()
    mock_Cfg.get.return_value = sentinel.value
    assert commands.GenericCommand.get_from_config(
        mock_Cfg,
        sentinel.label
    ) == sentinel.value


def test_GenericCommand_get_from_config_no_config(commands):
    mock_Cfg = mock.MagicMock()
    mock_Cfg.get.side_effect = commands.config.ConfigError
    with pytest.raises(commands.NotFoundInConfigError):
        commands.GenericCommand.get_from_config(
            mock_Cfg,
            sentinel.label
        )


def test_BuildCommand_actual(commands):
    parser, obj = create_subparser(commands.BuildCommand)
    args = parser.parse_args(['build', 'label'])
    assert args.imagelabel == 'label'
    assert args.output is None
    assert args.images_config is None
    with mock.patch.object(obj, "_command"):
        with mock.patch.object(commands.config, "ImageConfig"):
            args.command(args)
            assert obj.image


def test_BuildCommand_output(commands):
    parser = create_subparser(commands.BuildCommand)[0]
    args = parser.parse_args(['build', 'label', '--output', 'foo'])
    assert args.output is 'foo'


def test_BuildCommand_img_config(commands):
    parser = create_subparser(commands.BuildCommand)[0]
    args = parser.parse_args(['build', '--images-config', 'bar', 'label'])
    assert args.images_config is 'bar'


def test_BuildCommand_prepare(commands):
    parser, obj = create_subparser(commands.BuildCommand)
    args = parser.parse_args(['build', 'label'])
    assert args.imagelabel == 'label'
    with mock.patch.object(obj, "_run"):
        with mock.patch.object(commands.config, "ImageConfig"):
            args.command(args)
            assert obj.dib


def test_BuildCommand_run_success(commands, capsys):
    parser, obj = create_subparser(commands.BuildCommand)
    args = parser.parse_args(['build', 'label'])
    assert args.imagelabel == 'label'
    with mock.patch.object(commands.dib.DIB, "run") as mock_run:
        mock_run.return_value = 0
        with mock.patch.object(commands.config, "ImageConfig"):
            assert args.command(args) == 0
            assert mock_run.called
            s_in = capsys.readouterr()[0]
            assert 'successfully' in s_in


def test_BuildCommand_run_error(commands, capsys):
    parser, obj = create_subparser(commands.BuildCommand)
    args = parser.parse_args(['build', 'label'])
    assert args.imagelabel == 'label'
    with mock.patch.object(commands.dib.DIB, "run") as mock_run:
        mock_run.return_value = 1
        with mock.patch.object(commands.config, "ImageConfig"):
            assert args.command(args) == 1
            assert mock_run.called
            s_in = capsys.readouterr()[0]
            assert 'Error' in s_in


@pytest.mark.parametrize('status, exit_code', [
    [True, 0],
    [False, 1]
])
def test_TestCommand_actual(commands, status, exit_code):
    parser, obj = create_subparser(commands.TestCommand)
    args = parser.parse_args(['test', 'label'])
    assert args.imagelabel == 'label'
    with mock.patch.object(commands.config, "ImageConfig"):
        with mock.patch.object(commands.config, "TestEnvConfig"):
            with mock.patch.object(commands.do_tests, "DoTests") as dt:
                dt.return_value.run_all_tests.return_value = status
                assert args.command(args) == exit_code
                assert obj.image


def test_TestCommand__command_exception(commands):
    parser, obj = create_subparser(commands.TestCommand)
    args = parser.parse_args(['test', 'label'])
    assert args.imagelabel == 'label'
    with mock.patch.object(commands.config, "ImageConfig"):
        with mock.patch.object(commands.config, "TestEnvConfig"):
            with mock.patch.object(commands.do_tests, "DoTests") as dt:
                dt.return_value.run_all_tests.side_effect = commands.do_tests.TestError
                assert args.command(args) == 1


def test_TestCommand_input(commands):
    parser = create_subparser(commands.TestCommand)[0]
    args = parser.parse_args(['test', 'label', '--input', 'file'])
    assert args.input == 'file'
    with mock.patch.object(commands.config, "TestEnvConfig"):
        with mock.patch.object(commands.config, "ImageConfig"):
            with mock.patch.object(commands.do_tests, "DoTests"):
                args.command(args)
                assert args.input == 'file'


def test_TestCommand_test_env(commands):
    parser = create_subparser(commands.TestCommand)[0]
    args = parser.parse_args(['test', 'label', '--test-config', 'cfg'])
    with mock.patch.object(commands.config, "TestEnvConfig") as mock_tec:
        mock_tec.get.return_value = sentinel.data
        with mock.patch.object(commands.config, "ImageConfig"):
            with mock.patch.object(commands.do_tests, "DoTests"):
                args.command(args)
                assert args.test_config == 'cfg'


def test_TestCommand_env_name(commands):
    parser = create_subparser(commands.TestCommand)[0]
    args = parser.parse_args(['test', 'label', '--environment', 'env'])
    assert args.envlabel == 'env'
    with mock.patch.object(commands.config, "TestEnvConfig"):
        with mock.patch.object(commands.config, "ImageConfig"):
            with mock.patch.object(commands.do_tests, "DoTests"):
                args.command(args)
                assert args.envlabel == 'env'


def test_TestCommand_existing(commands):
    parser = create_subparser(commands.TestCommand)[0]
    args = parser.parse_args(['test', 'label', '--use-existing-image', 'myuuid'])
    assert args.uuid == 'myuuid'
    with mock.patch.object(commands.config, "TestEnvConfig"):
        with mock.patch.object(commands.config, "ImageConfig"):
            with mock.patch.object(commands.do_tests, "DoTests"):
                args.command(args)
                assert args.uuid == 'myuuid'


def test_TestCommand_keep_image(commands):
    parser = create_subparser(commands.TestCommand)[0]
    args = parser.parse_args(['test', 'label', '--keep-failed-image'])
    assert args.keep_failed_image is True
    with mock.patch.object(commands.config, "TestEnvConfig"):
        with mock.patch.object(commands.config, "ImageConfig"):
            with mock.patch.object(commands.do_tests, "DoTests"):
                args.command(args)
                assert args.keep_failed_image is True


def test_TestCommand_keep_instance(commands):
    parser = create_subparser(commands.TestCommand)[0]
    args = parser.parse_args(['test', 'label', '--keep-failed-instance'])
    assert args.keep_failed_instance is True
    with mock.patch.object(commands.config, "TestEnvConfig"):
        with mock.patch.object(commands.config, "ImageConfig"):
            with mock.patch.object(commands.do_tests, "DoTests"):
                args.command(args)
                assert args.keep_failed_instance is True


def test_TestCommand_actual_no_tests(commands):
    parser, obj = create_subparser(commands.TestCommand)
    args = parser.parse_args(['test', 'label'])
    assert args.imagelabel == 'label'
    with mock.patch.object(commands.config, "ImageConfig") as ic:
        ic.return_value.get.return_value = {}
        with mock.patch.object(commands.config, "TestEnvConfig"):
            with pytest.raises(commands.NoTestsError):
                args.command(args)


def test_TestCommand_actual_no_proper_env(commands):
    parser, obj = create_subparser(commands.TestCommand)
    args = parser.parse_args(['test', 'label'])
    assert args.imagelabel == 'label'
    with mock.patch.object(commands.config, "ImageConfig") as ic:
        ic.return_value.get.return_value = {'tests': {'something': 'unrelated'}}
        with mock.patch.object(commands.config, "TestEnvConfig"):
            with pytest.raises(commands.TestEnvironmentNotFoundError):
                args.command(args)


def test_TestCommand_actual_proper_env_override(commands):
    parser, obj = create_subparser(commands.TestCommand)
    args = parser.parse_args(['test', 'label', '--environment', 'foo'])
    assert args.imagelabel == 'label'
    with mock.patch.object(commands.config, "ImageConfig") as ic:
        ic.return_value.get.return_value = {'tests': {'environment_name': 'unrelated', 'tests_list': []}}
        with mock.patch.object(commands.config, "TestEnvConfig") as tec:
            tec.return_value = {'foo': 'bar'}
            with mock.patch.object(commands.do_tests, "DoTests"):
                args.command(args)
            assert obj.test_env == 'bar'


def test_UploadCommand_actual_with_obsolete(commands, cred, mock_env_cfg, mock_image_cfg):
    parser, obj = create_subparser(commands.UploadCommand)
    args = parser.parse_args(['upload', 'label', 'uploadlabel'])
    assert args.imagelabel == 'label'
    assert args.no_obsolete is False
    assert args.images_config is None
    assert args.input is None

    with mock.patch.object(commands.config, "UploadEnvConfig", autospec=True, strict=True) as uec:
        uec.return_value.get.return_value = mock_env_cfg
        with mock.patch.object(commands.osclient, "OSClient") as mock_os:
            mock_os.return_value.older_images.return_value = [sentinel.one, sentinel.two]
            with mock.patch.object(commands.config, "ImageConfig", autospec=True, strict=True) as ic:
                ic.return_value.get.return_value = mock_image_cfg
                args.command(args)


def test_UploadCommand_no_glance_section(commands, mock_env_cfg):
    img_config = {}
    parser, obj = create_subparser(commands.UploadCommand)
    args = parser.parse_args(['upload', 'label', 'uploadlabel'])
    with mock.patch.object(commands.config, "UploadEnvConfig") as uec:
        uec.return_value.get.return_value = mock_env_cfg
        with mock.patch.object(commands.osclient, "OSClient"):
            with mock.patch.object(commands.config, "ImageConfig") as ic:
                ic.return_value.get.return_value = img_config
                with pytest.raises(commands.NotFoundInConfigError):
                    args.command(args)


def test_UploadCommand_obsolete(commands):
    parser = create_subparser(commands.UploadCommand)[0]
    args = parser.parse_args(['upload', 'label', 'uploadlabel', '--no-obsolete'])
    assert args.no_obsolete is True


def test_RotateCommand_actual(commands, mock_env_cfg):
    parser, obj = create_subparser(commands.RotateCommand)
    args = parser.parse_args(['rotate', 'uploadlabel'])
    with mock.patch.object(commands.config, "UploadEnvConfig") as uec:
        uec.return_value.get.return_value = mock_env_cfg
        with mock.patch.object(commands.osclient, "OSClient"):
            args.command(args)
    assert obj.upload_env


def test_ObsoleteCommand_actual(commands, mock_env_cfg):
    parser, obj = create_subparser(commands.ObsoleteCommand)
    args = parser.parse_args(['mark-obsolete', 'uploadlabel', 'myuuid'])
    assert args.uuid == 'myuuid'
    with mock.patch.object(commands.config, "UploadEnvConfig") as uec:
        uec.return_value.get.return_value = mock_env_cfg
        with mock.patch.object(commands.osclient, "OSClient"):
            args.command(args)
    assert obj.upload_env


def test_TransferCommand_simple(commands):
    parser = create_subparser(commands.TransferCommand)[0]
    args = parser.parse_args(['transfer', 'myuuid'])
    assert args.uuid == 'myuuid'
    assert args.src_auth_url is None
    assert args.dst_auth_url is None
    assert args.src_tenant_name is None
    assert args.dst_tenant_name is None
    assert args.src_username is None
    assert args.dst_username is None
    assert args.src_password is None
    assert args.dst_password is None
    assert args.ignore_meta is False
    assert args.ignore_membership is False
    args.command(args)


@pytest.mark.parametrize("opt", [
    "src-auth-url",
    "dst-auth-url",
    "src-tenant-name",
    "dst-tenant-name",
    "src-username",
    "dst-username",
    "src-password",
    "dst-password",
])
def test_TransferCommand_args_param(commands, opt):
    parser = create_subparser(commands.TransferCommand)[0]
    args = parser.parse_args(['transfer', 'myuuid', "--" + opt, 'foo'])
    name = opt.replace('-', '_')
    assert args.__getattribute__(name) == 'foo'


@pytest.mark.parametrize("opt", [
    "ignore-meta",
    "ignore-membership"
])
def test_TransferCommand_args_param_ignore(commands, opt):
    parser = create_subparser(commands.TransferCommand)[0]
    args = parser.parse_args(['transfer', 'myuuid', "--" + opt])
    name = opt.replace('-', '_')
    assert args.__getattribute__(name) is True


def test_Main_empty_cmdline(commands):
    with pytest.raises(SystemExit):
        commands.Main([])


def test_Main_build_success(commands):
    with mock.patch.object(commands, 'config'):
        with mock.patch.object(commands.dib.DIB, 'run', return_value=0):
            m = commands.Main(['build', 'label'])
            assert m.run() == 0


def test_Main_build_error(commands):
    with mock.patch.object(commands, 'config'):
        with mock.patch.object(commands.dib.DIB, 'run', return_value=1):
            m = commands.Main(['build', 'label'])
            assert m.run() == 1


def test_main(commands):
    with mock.patch.object(commands, 'config'):
        with mock.patch.object(commands.dib.DIB, 'run', return_value=1):
            with mock.patch.object(commands.sys, 'exit') as mock_exit:
                commands.main(['build', 'label'])
                assert mock_exit.call_args[0][0] == 1


def test_main_premature_exit_config(commands):
    with mock.patch.object(commands.config, "ImageConfig") as m:
        m.side_effect = commands.NotFoundInConfigError
        with mock.patch.object(commands.sys, 'exit') as mock_exit:
            commands.main(['build', 'label'])
            assert mock_exit.call_args[0][0] == -1


def test_main_premature_exit_config2(commands):
    with mock.patch.object(commands, "config"):
        with mock.patch.object(commands.osclient, 'OSClient') as m_func:
            m_func.side_effect = commands.osclient.CredNotFound
            with mock.patch.object(commands.sys, 'exit') as mock_exit:
                commands.main(['test', 'label'])
                assert mock_exit.call_args[0][0] == -1


def test_init(commands):
    with mock.patch.object(commands, "Main") as m:
        m.return_value.run.return_value = 42
        with mock.patch.object(commands, "__name__", "__main__"):
            with mock.patch.object(commands.sys, 'exit') as mock_exit:
                commands.init()
                assert mock_exit.call_args[0][0] == 42


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
