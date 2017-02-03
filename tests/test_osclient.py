#!/usr/bin/python
import os
import inspect
import sys
import pytest
import mock
from mock import sentinel


@pytest.fixture
def osclient():
    from dibctl import osclient
    return osclient


@pytest.fixture
def empty_OSClient(osclient):
    with mock.patch.object(osclient.OSClient, "__init__", return_value=None):
        eos = osclient.OSClient()
    return eos


@pytest.fixture
def mock_os(osclient):
    with mock.patch.object(osclient, "glanceclient"):
        with mock.patch.object(osclient, "novaclient"):
            with mock.patch.object(osclient, "session"):
                with mock.patch.object(osclient, "identity"):
                    with mock.patch.object(osclient.OSClient, "_ask_for_version", return_value='v2'):
                        o = osclient.OSClient(sentinel.auth, sentinel.tenant, sentinel.username, sentinel.password)
                        o.glance = mock.MagicMock()
                        o.nova = mock.MagicMock()
    return o


@pytest.mark.parametrize('ver, libver, expected', [
    ['v2', ['v2'], True],
    ['v3', ['v2', 'v3', 'v4'], True],
    ['v1', ['v2', 'v3'], False],
    ['v4', ['v2', 'v3', 'v4'], False]  # no v4 support!
])
def test_is_supported_version(empty_OSClient, ver, libver, expected):
    assert empty_OSClient._issupported_version(ver, libver) == expected


@pytest.mark.parametrize('in_version, out_version', [
    ['v2', 'v2'],
    ['v3.4', 'v3'],
    ['vXXX', 'unsupported'],
    [None, 'unsupported'],
    [open('/dev/null'), 'unsupported'],
    ['v', 'unsupported'],
    ['', 'unsupported'],
    ['v0', 'unsupported']
])
def test_major_version(osclient, in_version, out_version):
    assert osclient.OSClient._major_version(in_version) == out_version


@pytest.mark.parametrize('versions, out_versions', [
    [['v2', 'v3'], ['v2', 'v3']],
    [['v2', 'ver'], ['v2']],
    [['v2', 'odd_v3'], ['v2']],
    [['v', 'v3'], ['v3']],
    [[], []]
])
def test_find_local_version(osclient, versions, out_versions):
    class MockIdentity(object):
        pass
    mock_identity = MockIdentity()
    for version in versions:
        mock_identity.__setattr__(version, True)
    with mock.patch.object(osclient, 'identity', mock_identity):
        assert osclient.OSClient._find_local_versions() == out_versions


def test_find_local_real_v2_or_v3(osclient):
    # this test relies on support for v2 or v3 from actual keystoneauth1 lib
    versions = osclient.OSClient._find_local_versions()
    assert 'v2' in versions or 'v3' in versions


@pytest.mark.parametrize('reply, version', [
    [{u'version': {u'id': u'v2.0',  # from our real keystone
                   u'links': [{u'href': u'https://auth.servers.mo01.cloud.servers.com:5000/v2.0/',
                              u'rel': u'self'},
                              {u'href': u'http://docs.openstack.org/',
                               u'rel': u'describedby',
                               u'type': u'text/html'}],
                   u'media-types': [{u'base': u'application/json',
                                    u'type': u'application/vnd.openstack.identity-v2.0+json'}],
                   u'status': u'stable',
                   u'updated': u'2014-04-17T00:00:00Z'}}, 'v2'],
    [{u'version': {u'id': u'v3.6',
                   u'links': [{u'href': u'https://auth.servers.mo01.cloud.servers.com:5000/v3/',
                               u'rel': u'self'}],
                   u'media-types': [{u'base': u'application/json',
                                     u'type': u'application/vnd.openstack.identity-v3+json'}],
                   u'status': u'stable',
                   u'updated': u'2016-04-04T00:00:00Z'}}, 'v3'],
    [{u'versions': {u'values': [{u'id': u'v3.6',
                                 u'links': [{u'href': u'https://auth.servers.mo01.cloud.servers.com:5000/v3/',
                                             u'rel': u'self'}],
                                 u'media-types': [{u'base': u'application/json',
                                                   u'type': u'application/vnd.openstack.identity-v3+json'}],
                                 u'status': u'stable',
                                 u'updated': u'2016-04-04T00:00:00Z'},
                                {u'id': u'v2.0',
                                 u'links': [{u'href': u'https://auth.servers.mo01.cloud.servers.com:5000/v2.0/',
                                             u'rel': u'self'},
                                            {u'href': u'http://docs.openstack.org/',
                                             u'rel': u'describedby',
                                             u'type': u'text/html'}],
                                 u'media-types': [{u'base': u'application/json',
                                                   u'type': u'application/vnd.openstack.identity-v2.0+json'}],
                                 u'status': u'stable',
                                 u'updated': u'2014-04-17T00:00:00Z'}]}}, 'v3']
])
def test__ask_for_version_ok(osclient, empty_OSClient, reply, version):
    keystone_data = {'auth_url': sentinel.auth_url}
    with mock.patch.object(osclient.requests, 'get') as mock_get:
        mock_get.return_value.json.return_value = reply
        assert empty_OSClient._ask_for_version(keystone_data, ['v2', 'v3'], False) == version


def test__ask_for_version_not_json(osclient, empty_OSClient):
    keystone_data = {'auth_url': sentinel.auth_url}
    with mock.patch.object(osclient.requests, 'get') as mock_get:
        mock_get.return_value.json.side_effect = osclient.simplejson.scanner.JSONDecodeError
        with pytest.raises(osclient.DiscoveryError):
            empty_OSClient._ask_for_version(keystone_data, ['v3'], False)


@pytest.mark.parametrize('json', [
    "I'm Azure!",
    ["I'm Azure!"],
    {'type': 'azure'},
    {'versions': 'Azure'},
    {'versions': {'values': 'Azure!'}},
])
def test__ask_for_version_bad_json(osclient, empty_OSClient, json):
    keystone_data = {'auth_url': sentinel.auth_url}
    with mock.patch.object(osclient.requests, 'get') as mock_get:
        mock_get.return_value.json.return_value = json
        with pytest.raises(osclient.DiscoveryError):
            empty_OSClient._ask_for_version(keystone_data, ['v3'], False)


def test__ask_for_version_bad_verion(osclient, empty_OSClient):
    keystone_data = {'auth_url': sentinel.auth_url}
    with mock.patch.object(osclient.requests, 'get') as mock_get:
        mock_get.return_value.json.return_value = {'versions': {'values': [{'id': 'azure'}]}}
        with pytest.raises(osclient.MissmatchError):
            empty_OSClient._ask_for_version(keystone_data, ['v3'], False)


def test_set_auth_version_ok_non_forced(empty_OSClient):
    with mock.patch.object(empty_OSClient, '_ask_for_version', return_value='v2'):
        empty_OSClient._set_auth_version({}, False)
        assert empty_OSClient.auth_version == 'v2'


def test_set_auth_version_bad_non_forced(empty_OSClient, osclient):
    with pytest.raises(osclient.DiscoveryError):
        with mock.patch.object(empty_OSClient, '_ask_for_version', side_effect=osclient.DiscoveryError):
            empty_OSClient._set_auth_version({}, False)


@pytest.mark.parametrize('version', ['v2', 'v3'])
def test_set_auth_version_ok_forced(empty_OSClient, osclient, version):
    empty_OSClient._set_auth_version({'api_version': version}, False)
    assert empty_OSClient.auth_version == version


def test_set_auth_version_bad_forced(empty_OSClient, osclient):
    with pytest.raises(osclient.DiscoveryError):
        empty_OSClient._set_auth_version({'auth_version': '2'}, False)


@pytest.mark.parametrize('lowpriority, highpriority, target', [
    [{'os_username': sentinel.value}, {}, 'username'],
    [{}, {'pass': sentinel.value}, 'password'],
    [{'uri': sentinel.BAD_VALUE}, {'url': sentinel.value}, 'auth_url'],
    [{}, {'OS_TENANT_NAME': sentinel.value}, 'project'],
    [{'OS_USER_DOMAIN': sentinel.value}, {'OS_USER_DOMAIN': sentinel.value}, 'user_domain'],
    [{'os_project_domain_name': sentinel.value}, {'project_domain': sentinel.value}, 'project_domain'],

])
def test_get_static_field_ok(osclient, lowpriority, highpriority, target):
    res = osclient.OSClient._get_generic_field(
        lowpriority,
        highpriority,
        target,
        osclient.OSClient.OPTION_NAMINGS[target]
    )
    assert res[target] == sentinel.value


@pytest.mark.parametrize('target', ['user_domain', 'project_domain'])
def test_get_static_field_defaults(osclient, target):
    res = osclient.OSClient._get_generic_field({}, {}, target, osclient.OSClient.OPTION_NAMINGS[target])
    assert res[target] == 'default'


@pytest.mark.parametrize('target', ['password', 'username', 'project', 'auth_url'])
def test_get_static_field_not_ok(osclient, target):
    with pytest.raises(osclient.CredNotFound):
        osclient.OSClient._get_generic_field({}, {}, target, osclient.OSClient.OPTION_NAMINGS[target])


@pytest.mark.parametrize('v', ['v2', 'v3'])
def test_map_creds_all_in(osclient, v):
    in_creds = {
        'username': sentinel.username,
        'password': sentinel.password,
        'project': sentinel.project,
        'auth_url': sentinel.auth_url,
        'user_domain': sentinel.user_domain,
        'project_domain': sentinel.project_domain
    }
    osclient.OSClient.map_creds(in_creds, v, osclient.OSClient.OPTIONS_MAPPING)


@pytest.mark.parametrize('version', ['v2', 'v3'])
@pytest.mark.parametrize('override', [
    'OS_AUTH_URL',
    'OS_TENANT_NAME',
    'OS_PASSWORD',
    'OS_USERNAME',
])
def test_prepare_auth_check_overrides(empty_OSClient, override, version):
    with mock.patch.object(empty_OSClient, "auth_version", version, create=True):
        data = {
            'os_username': sentinel.old,
            'os_password': sentinel.old,
            'project': sentinel.old,
            'auth_url': sentinel.old,
            'user_domain': sentinel.old,
            'project_domain': sentinel.old
        }
        creds = empty_OSClient._prepare_auth(data, {override: sentinel.new})
        assert sentinel.new in creds.values()


@pytest.mark.parametrize('version', ['v2', 'v3'])
def test_prepare_auth_normal(empty_OSClient, version):
    data = {
        'auth_url': sentinel.url,
        'username': sentinel.username,
        'tenant': sentinel.tenant
    }
    overrides = {
        'OS_PASSWORD': sentinel.password
    }
    with mock.patch.object(empty_OSClient, "auth_version", version, create=True):
        creds = empty_OSClient._prepare_auth(data, overrides)
        assert creds


#@pytest.mark.parametrize('version', ['v2', 'v3'])
#@pytest.mark.parametrize('insecure', [True, False])
#def test_create_session_v2(osclient, version, insecure):#
    #with mock.patch.object(osclient.identity, version) as mock_identity:
    #    mock_identity.Password.return_value = sentinel.auth
    #    with mock.patch.object(osclient.session, 'Session') as mock_session:
    #        osclient.OSClient.create_session(version, sentinel.auth_data, insecure)
    #        assert mock.call(auth=sentinel.auth) in mock_session.call_args
    #        assert (not insecure) in mock_session.call_args[0]


# -----------------------------------------------------------------------------------------------------------
# -----------------------------------------------------------------------------------------------------------
# -----------------------------------------------------------------------------------------------------------

def notest_osclient_init(osclient):
    with mock.patch.object(osclient.glanceclient, "Client") as mock_gc:  # disable for test
        with mock.patch.object(osclient.keystoneclient.v2_0, "Client"):
            with mock.patch.object(osclient.novaclient.client, "Client"):
                o = osclient.OSClient(sentinel.auth, sentinel.tenant, sentinel.username, sentinel.password)
                assert o.keystone_auth
                assert o.glance
                assert o.nova
                assert mock_gc.called


def test_osclient_upload_image_simple(osclient, mock_os):
    with mock.patch.object(osclient, "open", mock.mock_open()):
        mock_os.upload_image(sentinel.name, sentinel.filename)
        assert mock_os.glance.images.create.called


# FIXME
def notest_osclient_upload_image_meta(osclient, mock_os):
    with mock.patch.object(osclient, "open", mock.mock_open()):
        mock_os.upload_image(sentinel.name, sentinel.filename, meta={sentinel.key: sentinel.value})


def test_osclient_older_images(osclient, mock_os):
    mock_os.glance.images.list.return_value = [mock.MagicMock(id=42), mock.MagicMock(id=43)]
    assert mock_os.older_images(sentinel.name, 42) == set([43, ])


def test_osclinet_mark_image_obsolete(osclient, mock_os):
    mock_os.mark_image_obsolete("Name", sentinel.uuid)
    assert mock_os.glance.images.update.call_args == mock.call(
            sentinel.uuid,
            name="Obsolete Name",
            properties={"obsolete": "True"}
        )


def test_osclient_get_image(mock_os):
    assert mock_os.get_image(sentinel.uuid)


def test_osclient_new_keypair(mock_os):
    assert mock_os.new_keypair(sentinel.name)
    assert mock_os.nova.keypairs.create.called


def test_osclient_boot_instance(mock_os):
    mock_os.boot_instance(
        sentinel.name,
        sentinel.uuid,
        sentinel.flavor,
        sentinel.key_name,
        [sentinel.nic1, sentinel.nic2]
    )
    assert mock_os.nova.servers.create.called


def test_osclient_delete_instance(mock_os):
    mock_os.delete_instance(sentinel.uuid)
    assert mock_os.nova.servers.delete.called


def test_osclient_delete_keypair(mock_os):
    mock_os.delete_keypair(sentinel.uuid)
    assert mock_os.nova.keypairs.delete.called


def test_osclient_delete_image(mock_os):
    mock_os.delete_image(sentinel.uuid)
    assert mock_os.glance.images.delete.called


def test_osclient_get_instance(mock_os):
    assert mock_os.get_instance(sentinel.uuid)
    assert mock_os.nova.servers.get.called


def test_osclient_get_flavor(mock_os):
    assert mock_os.get_flavor(sentinel.uuid)
    assert mock_os.nova.flavors.find.called


@pytest.mark.parametrize("networks, regexp, output", [
    [{"internet_8.8.0.0/16": ["8.8.8.8"]}, "internet", "8.8.8.8"],
    [{"internet_8.8.0.0/16": ["8.8.8.8"], "local": ["192.168.1.1"]}, "internet", "8.8.8.8"],
    [{"local": ["192.168.1.1"], "internet_8.8.0.0/16": ["8.8.8.8"]}, "internet", "8.8.8.8"],
    [{"complicated_internet_name": ["8.8.8.8"]}, "internet", "8.8.8.8"],
    [{"single_network": ["8.8.8.8"]}, None, "8.8.8.8"]
])
def test_osclient_get_instance_ip_good(osclient, networks, regexp, output):
    mock_instance = mock.MagicMock()
    mock_instance.networks = networks
    assert osclient.OSClient.get_instance_ip(mock_instance, regexp) == output


@pytest.mark.parametrize("networks, regexp", [
    [{"local": ["192.168.1.1"]}, "internet"],
    [{"internet1": ["8.8.8.8"], "internet2": ["8.8.4.4"]}, "internet"],
    [{"local": ["192.168.1.1"], "internet_8.8.0.0/16": ["8.8.8.8"]}, None],
])
def test_osclient_get_instance_ip_bad(osclient, networks, regexp):
    mock_instance = mock.MagicMock()
    mock_instance.networks = networks
    with pytest.raises(osclient.IPError):
        osclient.OSClient.get_instance_ip(mock_instance, regexp)


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
