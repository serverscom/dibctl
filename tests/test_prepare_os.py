#!/usr/bin/python
import os
import inspect
import sys
import pytest
import mock
from mock import sentinel


@pytest.fixture
def prepare_os():
    from dibctl import prepare_os
    return prepare_os


@pytest.fixture
def prep_os(prepare_os):
    with mock.patch.object(prepare_os.PrepOS, "__init__", lambda x: None):
        prep_os = prepare_os.PrepOS()
    prep_os.os = mock.MagicMock(spec=prepare_os.osclient.OSClient)
    prep_os.delete_image = True
    prep_os.delete_instance = True
    prep_os.delete_keypair = True
    prep_os.upload_timeout = 1
    prep_os.active_timeout = 1
    prep_os.cleanup_timeout = 1
    prep_os.keypair_timeout = 1
    prep_os.create_timeout = 1
    prep_os.os_image = sentinel.image
    prep_os.os_instance = sentinel.instance
    prep_os.os_key = sentinel.key
    return prep_os


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
                {'net_id': sentinel.uuid1},
                {'net_id': sentinel.uuid2}
            ]
        }
    }
    return env


def test_init_normal(prepare_os, mock_image_cfg, mock_env_cfg):
    with mock.patch.object(prepare_os.osclient, "OSClient"):
        dt = prepare_os.PrepOS(mock_image_cfg, mock_env_cfg)
        assert dt.flavor_id == 'example'
        assert dt.delete_image is True
        assert dt.delete_instance is True


def test_prepare_nics(prepare_os, mock_env_cfg):
    assert list(prepare_os.PrepOS.prepare_nics(mock_env_cfg['nova'])) == [
        {'net-id': sentinel.uuid1},
        {'net-id': sentinel.uuid2}
    ]


@pytest.mark.parametrize("name, output", [
    ["Ubuntu 16.04 x86_64", "DIBCTL-Ubuntu 16.04 x86_64-deadbeef-dead-400-000-79880364a956"],
    ["key", "DIBCTL-key-deadbeef-dead-400-000-79880364a956"],
    ["test", "DIBCTL-test-deadbeef-dead-400-000-79880364a956"]
])
def test_make_test_name(prepare_os, name, output):
    with mock.patch.object(prepare_os.uuid, "uuid4", return_value='deadbeef-dead-400-000-79880364a956'):
        assert prepare_os.PrepOS.make_test_name(name) == output


def test_init_keypair(prep_os):
    prep_os.key_name = sentinel.key_name
    prep_os.init_keypair()
    assert prep_os.os.new_keypair.call_args[0][0] == sentinel.key_name


def test_upload_image_normal(prep_os):
    prep_os.override_image = None
    prep_os.image_name = sentinel.image_name
    prep_os.image = {
        'filename': sentinel.filename,
        'glance': {
            'properties': sentinel.meta
        }
    }
    prep_os.upload_image(1)
    assert prep_os.os_image
    assert prep_os.os.upload_image.call_args == mock.call(
        sentinel.image_name,
        sentinel.filename,
        meta=sentinel.meta
    )


def test_spawn_instance(prep_os):
    prep_os.instance_name = sentinel.instance_name
    prep_os.os_image = sentinel.os_image
    prep_os.availability_zone = None
    prep_os.config_drive = None
    prep_os.flavor_id = sentinel.flavor_id
    prep_os.os_key = mock.MagicMock(name=sentinel.key_name)
    prep_os.nic_list = sentinel.nic_list
    prep_os.spawn_instance(1)
    assert prep_os.os.boot_instance.called


def test_spawn_instance_no_config_drive(prepare_os):
    img = {
        'glance': {
            'name': 'name'
        }
    }
    env = {
        'keystone': {
        },
        'nova': {
            'flavor': 'mock_flavor'
        }
    }
    with mock.patch.object(prepare_os.osclient, "OSClient") as mock_os:
        p = prepare_os.PrepOS(img, env)
        p.os_key = mock.MagicMock()
        p.connect()
        p.spawn_instance(1)
        assert mock_os.return_value.boot_instance.call_args[1]['config_drive'] is False


def test_spawn_instance_no_config_drive2(prepare_os):
    img = {
        'glance': {
            'name': 'name'
        }
    }
    env = {
        'keystone': {
        },
        'nova': {
            'flavor': 'mock_flavor',
            'config_drive': False
        }
    }
    with mock.patch.object(prepare_os.osclient, "OSClient") as mock_os:
        p = prepare_os.PrepOS(img, env)
        p.os_key = mock.MagicMock()
        p.connect()
        p.spawn_instance(1)
        assert mock_os.return_value.boot_instance.call_args[1]['config_drive'] is False


def test_spawn_instance_with_drive(prepare_os):
    img = {
        'glance': {
            'name': 'name'
        }
    }
    env = {
        'keystone': {
        },
        'nova': {
            'flavor': 'mock_flavor',
            'config_drive': True
        }
    }
    with mock.patch.object(prepare_os.osclient, "OSClient") as mock_os:
        p = prepare_os.PrepOS(img, env)
        p.os_key = mock.MagicMock()
        p.connect()
        p.spawn_instance(1)
        assert mock_os.return_value.boot_instance.call_args[1]['config_drive'] is True


def test_get_instance_main_ip(prep_os):
    prep_os.os.get_instance_ip.return_value = sentinel.ip
    prep_os.os_instance = sentinel.instance
    prep_os.main_nic_regexp = sentinel.regexp
    prep_os.get_instance_main_ip()
    assert prep_os.ip == sentinel.ip


def test_wait_for_instance_error(prepare_os, prep_os):
    prep_os.os_instance = mock.MagicMock(status='ERROR')
    with pytest.raises(prepare_os.InstanceError):
        prep_os.wait_for_instance(1)


def test_wait_for_instance_simple_ok(prep_os):
    prep_os.os_instance = mock.MagicMock(status='ACTIVE')
    prep_os.wait_for_instance(1)


def test_wait_for_instance_long_ok(prepare_os, prep_os):
    prep_os.os_instance = mock.MagicMock(status='BUILDING')
    prep_os.os.get_instance.return_value = mock.MagicMock(status='ACTIVE')
    prep_os.wait_for_instance(10)
    prep_os.SLEEP_DELAY = 1
    with mock.patch.object(prepare_os.time, "sleep"):
        assert prep_os.os_instance


def test_wait_for_instance_long_error(prepare_os, prep_os):
    prep_os.os_instance = mock.MagicMock(status='BUILDING')
    prep_os.SLEEP_DELAY = 1
    prep_os.os.get_instance.return_value = mock.MagicMock(status='ERROR')
    with mock.patch.object(prepare_os.time, "sleep"):
        with pytest.raises(prepare_os.InstanceError):
            prep_os.wait_for_instance(10)


def test_wait_for_instance_timeout(prepare_os, prep_os):
    prep_os.os_instance = mock.MagicMock(status='BUILDING')
    with pytest.raises(prepare_os.TimeoutError):
        prep_os.wait_for_instance(1)


def test_prepare(prepare_os, prep_os):
    prep_os.init_keypair = mock.create_autospec(prep_os.init_keypair)
    prep_os.save_private_key = mock.create_autospec(prep_os.save_private_key)
    prep_os.upload_image = mock.create_autospec(prep_os.upload_image)
    prep_os.upload_timeout = sentinel.timeout
    prep_os.spawn_instance = mock.create_autospec(prep_os.spawn_instance)
    prep_os.wait_for_instance = mock.create_autospec(prep_os.wait_for_instance)
    prep_os.get_instance_main_ip = mock.create_autospec(prep_os.get_instance_main_ip)
    prep_os.prepare()
    assert prep_os.init_keypair.called
    assert prep_os.init_keypair.called


def test_cleanup(prepare_os, prep_os):
    prep_os.delete_keypair = True
    prep_os.delete_image = True
    prep_os.delete_instance = True
    prep_os.cleanup()
    assert prep_os.os.delete_image.called
    assert prep_os.os.delete_instance.called
    assert prep_os.os.delete_keypair.called


def test_inner__cleanup_normal(prepare_os):
    mock_delete = mock.MagicMock()
    prepare_os.PrepOS._cleanup("name", sentinel.object, True, mock_delete)
    assert mock_delete.called


def test_inner__cleanup_no_flag(prepare_os):
    mock_delete = mock.MagicMock()
    prepare_os.PrepOS._cleanup("name", sentinel.object, False, mock_delete)
    assert mock_delete.called is False


def test_inner__cleanup_exception(prepare_os, capsys):
    random_uuid = 'fbfc9dbc-bc6c-11e6-843b-ef48d80469ef'
    mock_delete = mock.MagicMock(side_effect=ValueError("mock error " + random_uuid))
    prepare_os.PrepOS._cleanup("name", sentinel.object, True, mock_delete)
    assert mock_delete.called
    assert random_uuid in capsys.readouterr()[0]


def test_cleanup_image(prep_os):
    prep_os._cleanup = mock.create_autospec(prep_os._cleanup)
    prep_os.cleanup_image()
    assert prep_os._cleanup.called


def test_cleanup_ssh_key_delete(prep_os):
    prep_os._cleanup = mock.create_autospec(prep_os._cleanup)
    prep_os.wipe_private_key = mock.create_autospec(prep_os.wipe_private_key)
    prep_os.cleanup_image()
    assert prep_os._cleanup.called


def test_cleanup_ssh_key_not_delete(prep_os):
    prep_os._cleanup = mock.create_autospec(prep_os._cleanup)
    prep_os.delete_keypair = False
    prep_os.wipe_private_key = mock.create_autospec(prep_os.wipe_private_key)
    prep_os.cleanup_image()
    assert prep_os._cleanup.called
    assert prep_os.wipe_private_key.called is False


def test_error_handler_no_timeout(prep_os):
    prep_os.cleanup = mock.MagicMock()
    prep_os.error_handler(sentinel.signum, sentinel.frame, timeout=False)
    assert prep_os.cleanup.called


def test_error_handler_with_timeout(prepare_os, prep_os):
    prep_os.cleanup = mock.MagicMock()
    with pytest.raises(prepare_os.TimeoutError):
        prep_os.error_handler(sentinel.signum, sentinel.frame, timeout=True)
    assert prep_os.cleanup.called


def test_is_port_available_instant(prepare_os, prep_os):
    with mock.patch.object(prepare_os.time, "time", mock.MagicMock(return_value=0)):
        mock_sock = mock.MagicMock()
        mock_sock.connect_ex.return_value = 0
        with mock.patch.object(prepare_os.socket, "socket", mock.MagicMock(return_value=mock_sock)):
            prep_os.ip = sentinel.ip
            assert prep_os.wait_for_port(sentinel.port, 60) is True


def test__enter__normal(prep_os):
    prep_os.prepare = mock.create_autospec(prep_os.prepare)
    assert prep_os.__enter__() == prep_os
    assert prep_os.prepare.called


def test__enter__exception(prep_os, capsys):
    random_uuid = 'af07a744-bc81-11e6-b1c3-ffdeadff6e00'
    prep_os.prepare = mock.Mock(side_effect=ValueError(random_uuid))
    with pytest.raises(ValueError):
        prep_os.__enter__()
    assert prep_os.prepare.called
    assert random_uuid in capsys.readouterr()[0]


def test__exit__(prep_os):
    prep_os.cleanup = mock.create_autospec(prep_os.cleanup)
    prep_os.report = False
    prep_os.__exit__(sentinel.e_type, sentinel.e_val, sentinel.e_tb)
    assert prep_os.cleanup.called


def test_get_env_config(prepare_os, prep_os):
    prep_os.os_instance = mock.Mock()
    prep_os.os_instance.id = sentinel.uuid
    prep_os.os_instance.networks = {
        'net1': [sentinel.ip1],
        'net2': [sentinel.ip2]
    }
    prep_os.os_instance.interface_list.return_value = [
        mock.Mock(_info={}),
        mock.Mock(_info={})
    ]
    prep_os.instance_name = "NAME"
    prep_os.flavor_id = sentinel.flavor_id
    prep_os.ip = sentinel.ip
    prep_os.os_key_private_file = sentinel.private_file
    flavor = mock.Mock()
    flavor.ram = sentinel.ram
    flavor.name = sentinel.name
    flavor.vcpus = sentinel.vcpus
    flavor.disk = sentinel.disk
    flavor.get_keys.return_value = {
        sentinel.name1: sentinel.value1,
        sentinel.name2: sentinel.value2
    }
    prep_os.os.get_flavor.return_value = flavor
    env = prep_os.get_env_config()
    assert env['instance_uuid'] == 'sentinel.uuid'
    assert env['instance_name'] == 'name'
    assert env['flavor_id'] == 'sentinel.flavor_id'
    assert env['main_ip'] == 'sentinel.ip'
    assert env['ssh_private_key'] == 'sentinel.private_file'
    assert env['flavor_ram'] == 'sentinel.ram'
    assert env['flavor_name'] == 'sentinel.name'
    assert env['flavor_disk'] == 'sentinel.disk'
    assert env['ip_1'] in('sentinel.ip1', 'sentinel.ip2')
    assert env['ip_2'] in('sentinel.ip1', 'sentinel.ip2')
    assert env['iface_1_info'] == '{}'
    assert env['iface_2_info'] == '{}'
    assert env['flavor_meta_sentinel.name1'] == 'sentinel.value1'
    assert env['flavor_meta_sentinel.name2'] == 'sentinel.value2'


def test_wait_for_port_never(prepare_os, prep_os):
    with mock.patch.object(prepare_os.time, "time", mock.MagicMock(side_effect=[0, 10, 60, 80])):
        mock_sock = mock.MagicMock()
        mock_sock.connect_ex.return_value = -1
        with mock.patch.object(prepare_os.socket, "socket", mock.MagicMock(return_value=mock_sock)):
            with mock.patch.object(prepare_os.time, "sleep"):
                prep_os.ip = sentinel.ip
                assert prep_os.wait_for_port(sentinel.port, 60) is False


def test_wait_for_port_eventually_succeed(prepare_os, prep_os):
    with mock.patch.object(prepare_os.time, "time", mock.MagicMock(side_effect=[0, 0, 10, 20, 80])):
        mock_sock = mock.MagicMock()
        mock_sock.connect_ex.side_effect = [-1, -1, 0]
        with mock.patch.object(prepare_os.socket, "socket", mock.MagicMock(return_value=mock_sock)):
            with mock.patch.object(prepare_os.time, "sleep"):
                prep_os.ip = sentinel.ip
                assert prep_os.wait_for_port(sentinel.port, 60) is True


def test_wait_for_port_eventually_fail(prepare_os, prep_os):
    with mock.patch.object(prepare_os.time, "time", mock.MagicMock(side_effect=[0, 0, 10, 20, 80])):
        mock_sock = mock.MagicMock()
        mock_sock.connect_ex.side_effect = [-1, -1, -1, 0]
        with mock.patch.object(prepare_os.socket, "socket", mock.MagicMock(return_value=mock_sock)):
            with mock.patch.object(prepare_os.time, "sleep"):
                prep_os.ip = sentinel.ip
                assert prep_os.wait_for_port(sentinel.port, 60) is False


def test_grand_test_for_context_manager_normal(prepare_os, prep_os, mock_image_cfg, mock_env_cfg):

    with mock.patch.object(prepare_os.osclient, "OSClient") as mockos:
        mockos.return_value.new_keypair.return_value.private_key = "key"
        mockos.return_value.boot_instance.return_value.status = "ACTIVE"
        p = prepare_os.PrepOS(mock_image_cfg, mock_env_cfg, delete_instance=False)
        with p:
            pass


def test_grand_test_for_context_manager_fail_not_delete(prepare_os, capsys, mock_image_cfg, mock_env_cfg):
    with pytest.raises(Exception):
        with mock.patch.object(prepare_os.osclient, "OSClient") as mockos:
            mockos.return_value.new_keypair.return_value.private_key = "key"
            mockos.return_value.boot_instance.return_value.status = "ACTIVE"
            p = prepare_os.PrepOS(mock_image_cfg, mock_env_cfg, delete_instance=False)
            with p:
                p.report = True
                raise Exception
    output = capsys.readouterr()[0]
    assert "Instance ip is" in output


if __name__ == "__main__":
    ourfilename = os.path.abspath(inspect.getfile(inspect.currentframe()))
    currentdir = os.path.dirname(ourfilename)
    parentdir = os.path.dirname(currentdir)
    file_to_test = os.path.join(
        parentdir,
        os.path.basename(parentdir),
        os.path.basename(ourfilename).replace("test_", '', 1)
    )
    pytest.main([
     "-vv",
     "--cov", file_to_test,
     "--cov-report", "term-missing"
     ] + sys.argv)
