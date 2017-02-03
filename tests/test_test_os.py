#!/usr/bin/python
import os
import inspect
import sys
import pytest
import mock
import time
from mock import sentinel

@pytest.fixture
def test_os():
    from dibctl import test_os
    return test_os


@pytest.fixture
def tos(test_os):
    with mock.patch.object(test_os.TestOS, "__init__", lambda x:None):
        tos = test_os.TestOS()
    tos.os = mock.MagicMock(spec = test_os.osclient.OSClient)
    tos.delete_image = True
    tos.delete_instance = True
    tos.delete_keypair = True
    tos.os_image = sentinel.image
    tos.os_instance = sentinel.instance
    tos.os_key = sentinel.key
    return tos


def test_init_normal(test_os):
    with mock.patch.object(test_os.osclient, "OSClient") as mock_client:
        image = {
            'glance':{
                'name': 'foo'
            }
        }
        env = {
            'flavor': 'example',
            'os_auth_url': sentinel.auth,
            'os_tenant_name': sentinel.tenant,
            'os_username': sentinel.user,
            'os_password': sentinel.password
        }
        dt = test_os.TestOS(image, env)
        assert dt.os
        assert dt.flavor_id == 'example'
        assert dt.delete_image is True
        assert dt.delete_instance is True


def test_init_override(test_os):
    with mock.patch.object(test_os.osclient, "OSClient") as mock_client:
        image = {
            'glance':{
                'name': 'foo'
            }
        }
        env = {
            'flavor': 'example',
            'os_auth_url': sentinel.auth,
            'os_tenant_name': sentinel.tenant,
            'os_username': sentinel.user,
            'os_password': sentinel.password
        }
        dt = test_os.TestOS(image, env, override_image = 'image')
        assert dt.os
        assert dt.flavor_id == 'example'
        assert dt.delete_image is False
        assert dt.delete_instance is True



def test_prepare_nics(test_os):
    env = {'nics': [sentinel.uuid1, sentinel.uuid2]}
    assert list(test_os.TestOS.prepare_nics(env)) == [
        {'net-id': sentinel.uuid1},
        {'net-id': sentinel.uuid2}
    ]


@pytest.mark.parametrize("name, output",[
["Ubuntu 16.04 x86_64", "DIBCTL-Ubuntu 16.04 x86_64-deadbeef-dead-400-000-79880364a956"],
["key", "DIBCTL-key-deadbeef-dead-400-000-79880364a956"],
["test", "DIBCTL-test-deadbeef-dead-400-000-79880364a956"]
])
def test_make_test_name(test_os, name, output):
    with mock.patch.object(test_os.uuid, "uuid4", return_value = 'deadbeef-dead-400-000-79880364a956'):
        assert test_os.TestOS.make_test_name(name) == output


def test_init_keypair(tos):
    tos.key_name = sentinel.key_name
    tos.init_keypair()
    assert tos.os.new_keypair.call_args[0][0] == sentinel.key_name


def test_save_private_key(test_os, tos):
    with mock.patch.object(test_os, "tempfile"):
        tos.os_key = mock.MagicMock()
        tos.save_private_key()


def test_wipe_private_key(test_os, tos):
    with mock.patch.object(test_os, "open", mock.mock_open(), create=True) as mock_open:
        with mock.patch.object(test_os.os, "remove") as mock_remove:
            tos.os_key_private_file = sentinel.private_key
            tos.wipe_private_key()
            assert mock_open().write.call_args[0][0] == " " * 4096
            assert mock_remove.call_args[0][0] == sentinel.private_key


def test_upload_image_with_override(test_os, tos):
    tos.override_image = sentinel.override_image
    tos.upload_image(1)
    assert tos.os_image
    assert tos.os.get_image.call_args[0][0] == sentinel.override_image


def test_upload_image_normal(tos):
    tos.override_image = None
    tos.image_name = sentinel.image_name
    tos.image = {
        'filename': sentinel.filename,
        'glance': {
            'properties': sentinel.meta
        }
    }
    tos.upload_image(1)
    assert tos.os_image
    assert tos.os.upload_image.call_args == mock.call(
        sentinel.image_name,
        sentinel.filename,
        meta = sentinel.meta
    )


def test_spawn_instance(tos):
    tos.instance_name = sentinel.instance_name
    tos.os_image = sentinel.os_image
    tos.config_drive = None
    tos.flavor_id = sentinel.flavor_id
    tos.os_key = mock.MagicMock(name=sentinel.key_name)
    tos.nic_list = sentinel.nic_list
    tos.spawn_instance(1)
    assert tos.os.boot_instance.called


def test_get_instance_main_ip(tos):
    tos.os.get_instance_ip.return_value = sentinel.ip
    tos.os_instance = sentinel.instance
    tos.main_nic_regexp = sentinel.regexp
    tos.get_instance_main_ip()
    assert tos.ip == sentinel.ip


def test_wait_for_instance_error(test_os, tos):
    tos.os_instance = mock.MagicMock(status='ERROR')
    with pytest.raises(test_os.InstanceError):
        tos.wait_for_instance(1)


def test_wait_for_instance_simple_ok(tos):
    tos.os_instance = mock.MagicMock(status='ACTIVE')
    tos.wait_for_instance(1)


def test_wait_for_instance_long_ok(test_os, tos):
    tos.os_instance = mock.MagicMock(status='BUILDING')
    tos.os.get_instance.return_value = mock.MagicMock(status='ACTIVE')
    tos.wait_for_instance(10)
    tos.SLEEP_DELAY = 1
    with mock.patch.object(test_os.time, "sleep"):
        assert tos.os_instance


def test_wait_for_instance_long_error(test_os, tos):
    tos.os_instance = mock.MagicMock(status='BUILDING')
    tos.SLEEP_DELAY = 1
    tos.os.get_instance.return_value = mock.MagicMock(status='ERROR')
    with mock.patch.object(test_os.time, "sleep"):
        with pytest.raises(test_os.InstanceError):
            tos.wait_for_instance(10)


def test_wait_for_instance_timeout(test_os, tos):
    tos.os_instance = mock.MagicMock(status='BUILDING')
    with pytest.raises(test_os.TimeoutError):
        tos.wait_for_instance(1)


def test_prepare(test_os, tos):
    tos.init_keypair = mock.create_autospec(tos.init_keypair)
    tos.save_private_key = mock.create_autospec(tos.save_private_key)
    tos.upload_image = mock.create_autospec(tos.upload_image)
    tos.upload_timeout = sentinel.timeout
    tos.spawn_instance = mock.create_autospec(tos.spawn_instance)
    tos.wait_for_instance = mock.create_autospec(tos.wait_for_instance)
    tos.get_instance_main_ip = mock.create_autospec(tos.get_instance_main_ip)
    tos.prepare()
    assert tos.init_keypair.called
    assert tos.init_keypair.called

def test_cleanup_instance(tos):
    tos._cleanup = mock.create_autospec(tos._cleanup)
    tos.os_instance = sentinel.instance
    tos.cleanup_image()
    assert tos._cleanup.called
    assert tos.save_private_key.called
    assert tos.upload_image.called
    assert tos.spawn_instance.called
    assert tos.wait_for_instance.called
    assert tos.get_instance_main_ip.called


def  test_cleanup(test_os, tos):
    tos.wipe_private_key = mock.MagicMock()
    tos.delete_keypair = True
    tos.delete_image = True
    tos.delete_instance = True
    tos.cleanup()
    assert tos.os.delete_image.called
    assert tos.os.delete_instance.called
    assert tos.os.delete_keypair.called
    assert tos.wipe_private_key.called


def test_inner__cleanup_normal(test_os):
    mock_delete = mock.MagicMock()
    test_os.TestOS._cleanup("name", sentinel.object, True, mock_delete)
    assert mock_delete.called


def test_inner__cleanup_no_flag(test_os):
    mock_delete = mock.MagicMock()
    test_os.TestOS._cleanup("name", sentinel.object, False, mock_delete)
    assert mock_delete.called is False


def test_inner__cleanup_exception(test_os, capsys):
    random_uuid = 'fbfc9dbc-bc6c-11e6-843b-ef48d80469ef'
    mock_delete = mock.MagicMock(side_effect = ValueError("mock error " + random_uuid))
    test_os.TestOS._cleanup("name", sentinel.object, True, mock_delete)
    assert mock_delete.called
    assert random_uuid in capsys.readouterr()[0]


def test_cleanup_instance(tos):
    tos._cleanup = mock.create_autospec(tos._cleanup)
    tos.cleanup_instance()
    assert tos._cleanup.called


def test_cleanup_image(tos):
    tos._cleanup = mock.create_autospec(tos._cleanup)
    tos.cleanup_image()
    assert tos._cleanup.called


def test_cleanup_ssh_key_delete(tos):
    tos._cleanup = mock.create_autospec(tos._cleanup)
    tos.wipe_private_key = mock.create_autospec(tos.wipe_private_key)
    tos.cleanup_image()
    assert tos._cleanup.called


def test_cleanup_ssh_key_not_delete(tos):
    tos._cleanup = mock.create_autospec(tos._cleanup)
    tos.delete_keypair = False
    tos.wipe_private_key = mock.create_autospec(tos.wipe_private_key)
    tos.cleanup_image()
    assert tos._cleanup.called
    assert tos.wipe_private_key.called is False


def test_cleanup_ssh_key_exception(tos, capsys):
    random_uuid = '03259c52-bc80-11e6-b6cf-6754ef2724b6'
    tos._cleanup = mock.create_autospec(tos._cleanup)
    tos.wipe_private_key = mock.MagicMock(side_effect=ValueError(random_uuid))
    tos.cleanup_ssh_key()
    assert tos._cleanup.called
    assert tos.wipe_private_key.called is True
    assert random_uuid in capsys.readouterr()[0]


def test_error_handler_no_timeout(tos):
    tos.cleanup = mock.MagicMock()
    tos.error_handler(sentinel.signum, sentinel.frame, timeout=False)
    assert tos.cleanup.called


def test_error_handler_with_timeout(test_os, tos):
    tos.cleanup = mock.MagicMock()
    with pytest.raises(test_os.TimeoutError):
        tos.error_handler(sentinel.signum, sentinel.frame, timeout=True)
    assert tos.cleanup.called


def test_is_port_available_instant(test_os, tos):
    with mock.patch.object(test_os.time, "time", mock.MagicMock(return_value=0)):
        mock_sock = mock.MagicMock()
        mock_sock.connect_ex.return_value = 0
        with mock.patch.object(test_os.socket, "socket", mock.MagicMock(return_value = mock_sock)):
            tos.ip = sentinel.ip
            assert tos.wait_for_port(sentinel.port, 60) is True


def test__enter__normal(tos):
    tos.prepare = mock.create_autospec(tos.prepare)
    assert tos.__enter__() == tos
    assert tos.prepare.called


def test__enter__exception(tos, capsys):
    random_uuid = 'af07a744-bc81-11e6-b1c3-ffdeadff6e00'
    tos.prepare = mock.Mock(side_effect=ValueError(random_uuid))
    with pytest.raises(ValueError):
        tos.__enter__()
    assert tos.prepare.called
    assert random_uuid in capsys.readouterr()[0]


def test__exit__(tos):
    tos.cleanup = mock.create_autospec(tos.cleanup)
    tos.report = False
    tos.__exit__(sentinel.e_type, sentinel.e_val, sentinel.e_tb)
    assert tos.cleanup.called


def test_get_env_config(test_os, tos):
    tos.os_instance = mock.Mock()
    tos.os_instance.id = sentinel.uuid
    tos.os_instance.networks = {
        'net1': [sentinel.ip1],
        'net2': [sentinel.ip2]
    }
    tos.os_instance.interface_list.return_value = [
        mock.Mock(_info={}),
        mock.Mock(_info={})
    ]
    tos.instance_name = "NAME"
    tos.flavor_id = sentinel.flavor_id
    tos.ip = sentinel.ip
    tos.os_key_private_file = sentinel.private_file
    flavor = mock.Mock()
    flavor.ram = sentinel.ram
    flavor.name = sentinel.name
    flavor.vcpus = sentinel.vcpus
    flavor.disk = sentinel.disk
    flavor.get_keys.return_value = {
        sentinel.name1: sentinel.value1,
        sentinel.name2: sentinel.value2
    }
    tos.os.get_flavor.return_value = flavor
    env = tos.get_env_config()
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



def test_wait_for_port_never(test_os, tos):
    with mock.patch.object(test_os.time, "time", mock.MagicMock(side_effect=[0, 10, 60, 80])):
        mock_sock = mock.MagicMock()
        mock_sock.connect_ex.return_value = -1
        with mock.patch.object(test_os.socket, "socket", mock.MagicMock(return_value=mock_sock)):
            with mock.patch.object(test_os.time, "sleep"):
                tos.ip = sentinel.ip
                assert tos.wait_for_port(sentinel.port, 60) is False


def test_wait_for_port_eventually_succeed(test_os, tos):
    with mock.patch.object(test_os.time, "time", mock.MagicMock(side_effect=[0, 0, 10, 20, 80])):
        mock_sock = mock.MagicMock()
        mock_sock.connect_ex.side_effect = [-1, -1, 0]
        with mock.patch.object(test_os.socket, "socket", mock.MagicMock(return_value=mock_sock)):
            with mock.patch.object(test_os.time, "sleep"):
                tos.ip = sentinel.ip
                assert tos.wait_for_port(sentinel.port, 60) is True


def test_wait_for_port_eventually_fail(test_os, tos):
    with mock.patch.object(test_os.time, "time", mock.MagicMock(side_effect=[0, 0, 10, 20, 80])):
        mock_sock = mock.MagicMock()
        mock_sock.connect_ex.side_effect = [-1, -1, -1, 0]
        with mock.patch.object(test_os.socket, "socket", mock.MagicMock(return_value=mock_sock)):
            with mock.patch.object(test_os.time, "sleep"):
                tos.ip = sentinel.ip
                assert tos.wait_for_port(sentinel.port, 60) is False


def test_grand_test_for_context_manager_normal(test_os, tos):
    image = {
        'glance':{
            'name': 'imagename'
        },
        'filename': 'filename',
        'tests': {
            'wait_for_port': 22
        }
    }
    env = {
        'flavor': 'example',
        'os_auth_url': sentinel.auth,
        'os_tenant_name': sentinel.tenant,
        'os_username': sentinel.user,
        'os_password': sentinel.password
    }

    with mock.patch.object(test_os.osclient, "OSClient") as mockos:
        mockos.return_value.new_keypair.return_value.private_key = "key"
        mockos.return_value.boot_instance.return_value.status = "ACTIVE"
        with test_os.TestOS(image, env, delete_instance=False):
            pass


def test_grand_test_for_context_manager_fail_not_delete(test_os, capsys):
    image = {
        'glance':{
            'name': 'imagename'
        },
        'filename': 'filename',
        'tests': {
            'wait_for_port': 22
        }
    }
    env = {
        'flavor': 'example',
        'os_auth_url': sentinel.auth,
        'os_tenant_name': sentinel.tenant,
        'os_username': sentinel.user,
        'os_password': sentinel.password
    }
    with pytest.raises(Exception):
        with mock.patch.object(test_os.osclient, "OSClient") as mockos:
            mockos.return_value.new_keypair.return_value.private_key = "key"
            mockos.return_value.boot_instance.return_value.status = "ACTIVE"
            with test_os.TestOS(image, env, delete_instance=False) as tos:
                tos.report = True
                raise Exception
    output = capsys.readouterr()[0]
    assert "Instance ip is" in output
    assert "Private key file" in output


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
