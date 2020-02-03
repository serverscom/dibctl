#!/usr/bin/python
import os
import inspect
import sys
import pytest
import mock
from mock import sentinel
import tempfile
import subprocess

ourfilename = os.path.abspath(inspect.getfile(inspect.currentframe()))
currentdir = os.path.dirname(ourfilename)
parentdir = os.path.dirname(currentdir)


@pytest.fixture
def config():
    from dibctl import config
    return config


@pytest.mark.parametrize('file_val, res', [
    [[False, False, False], []],
    [[False, False, True], ['path/file2']],
    [[True, True, True], [
        'path/file1',
        'path/file2',
        'path/file3'
    ]]
])
def test_gather_snippets(config, file_val, res):
    with mock.patch.object(config.os, 'listdir', return_value=[
        'file3', 'file1', 'file2'
    ]):
        with mock.patch.object(config.os.path, 'isfile', side_effect=file_val):
            assert config.Config().gather_snippets('path') == res


def test_gather_snippets_empty(config):
    with mock.patch.object(config.os, 'listdir', return_value=[]):
        assert config.Config().gather_snippets('path') == []


class Test_find_all_configs():
    'Semi integration test, as we create actual files and check search output'
    def setup_method(self, request):
        self.mock_root = tempfile.mkdtemp()
        self.curdir = os.getcwd()
        os.chdir(self.mock_root)

    def teardown_method(self, request):
        subprocess.check_call(['rm', '-r', self.mock_root])
        os.chdir(self.curdir)

    def _prep_file(self, dir, file):
        full_dir = os.path.join(self.mock_root, dir)
        subprocess.check_call(['mkdir', '-p', full_dir])  # bad makedirs in 2.7
        if file:
            open(os.path.join(full_dir, file), 'w').close()

    def _prep_conf(self, config):
        c = config.Config()
        c.CONFIG_SEARCH_PATH = ['etc/dibctl', './dibctl', './']
        c.DEFAULT_CONFIG_NAME = 'config.yaml'
        c.CONF_D_NAME = 'config.d'
        return c

    def test_empty(self, config):
        c = self._prep_conf(config)
        assert list(c.find_all_configs()) == []

    @pytest.mark.parametrize('path, result', [
        ['', './config.yaml'],
        ['dibctl', './dibctl/config.yaml'],
        ['etc/dibctl', 'etc/dibctl/config.yaml'],
    ])
    def test_one_config(self, config, path, result):
        c = self._prep_conf(config)
        self._prep_file(path, 'config.yaml')
        assert list(c.find_all_configs()) == [result]

    def test_three_config(self, config):
        c = self._prep_conf(config)
        self._prep_file('', 'config.yaml')
        self._prep_file('dibctl', 'config.yaml')
        self._prep_file('etc/dibctl', 'config.yaml')
        assert list(c.find_all_configs()) == [
            'etc/dibctl/config.yaml',
            './dibctl/config.yaml',
            './config.yaml'
        ]

    @pytest.mark.parametrize('path, result', [
        ['config.d', './config.d/01-config.yaml'],
        ['dibctl/config.d', './dibctl/config.d/01-config.yaml'],
        ['etc/dibctl/config.d', 'etc/dibctl/config.d/01-config.yaml'],
    ])
    def test_d_one_snippet(self, config, path, result):
        c = self._prep_conf(config)
        self._prep_file(path, '01-config.yaml')
        assert list(c.find_all_configs()) == [result]

    def test_d_snippet_order(self, config):
        c = self._prep_conf(config)
        self._prep_file('config.d', '03-foo.yaml')
        self._prep_file('config.d', '01-bar.yaml')
        self._prep_file('config.d', '02-baz.yaml')
        assert list(c.find_all_configs()) == [
            './config.d/01-bar.yaml',
            './config.d/02-baz.yaml',
            './config.d/03-foo.yaml'
        ]

    def test_full_size_test_configs_and_snippets(self, config):
        c = self._prep_conf(config)
        self._prep_file('', 'config.yaml')
        self._prep_file('dibctl', 'config.yaml')
        self._prep_file('etc/dibctl', 'config.yaml')
        self._prep_file('config.d', '60-foo.yaml')
        self._prep_file('config.d', '70-foo.yaml')
        self._prep_file('dibctl/config.d', '50-bar.yaml')
        self._prep_file('dibctl/config.d', '80-bar.yaml')
        self._prep_file('etc/dibctl/config.d', '40-baz.yaml')
        self._prep_file('etc/dibctl/config.d', '90-baz.yaml')
        assert list(c.find_all_configs()) == [
            'etc/dibctl/config.yaml',
            'etc/dibctl/config.d/40-baz.yaml',
            'etc/dibctl/config.d/90-baz.yaml',
            './dibctl/config.yaml',
            './dibctl/config.d/50-bar.yaml',
            './dibctl/config.d/80-bar.yaml',
            './config.yaml',
            './config.d/60-foo.yaml',
            './config.d/70-foo.yaml'
        ]

    def test_with_wrong_file_type(self, config):
        c = self._prep_conf(config)
        self._prep_file('config.d/03-foo.yaml', 'boo')
        self._prep_file('config.d', '01-bar.yaml')
        assert list(c.find_all_configs()) == [
            './config.d/01-bar.yaml'
        ]


@pytest.mark.parametrize('old, new, result', [
    [{}, {}, {}],
    [{'a': 1}, {}, {'a': 1}],
    [{}, {'a': 1}, {'a': 1}],
    [{'b': 2}, {'a': 1}, {'a': 1, 'b': 2}],
])
def test_merge_config_snippet(config, old, new, result):
    c = config.Config(old)
    c.merge_config_snippet(new, 'new_name')
    assert c.config == result


def test_merge_config_snippet_with_overwrite(config, capfd):
    c = config.Config({'a': 1, 'b': 2, 'c': 3})
    c.merge_config_snippet({'a': 2}, 'new_name')
    assert c.config == {'a': 2, 'b': 2, 'c': 3}
    out = capfd.readouterr()[0]
    assert 'redefines' in out


def test_add_config_no_file(config):
    with mock.patch.object(config.os.path, "isfile", return_value=False):
        c = config.Config()
        with pytest.raises(config.ConfigNotFound):
            c.add_config(sentinel.not_a_file)


def test_add_config_simple(config):
    with tempfile.NamedTemporaryFile() as mock_cfg:
        mock_cfg.write('a: b')
        mock_cfg.flush()
        c = config.Config()
        c.add_config(mock_cfg.name)
        assert c.get('a') == 'b'
        assert c.config_list == [mock_cfg.name]


def test_add_config_double(config, capfd):
    with tempfile.NamedTemporaryFile() as mock_cfg1:
        mock_cfg1.write('some_label: bad!')
        mock_cfg1.flush()
        with tempfile.NamedTemporaryFile() as mock_cfg2:
            mock_cfg2.write('some_label: good')
            mock_cfg2.flush()
            c = config.Config()
            c.add_config(mock_cfg1.name)
            c.add_config(mock_cfg2.name)
            assert c.get('some_label') == 'good'
            assert c.config_list == [mock_cfg1.name, mock_cfg2.name]
    out = capfd.readouterr()[0]
    assert "redefines some_label" in out


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
    mock_config = mock.mock_open(
        read_data='{"image1":{"filename": "bad"}, "image2":{"filename":"bad"}}'
    )
    with mock.patch.object(config, "open", mock_config):
        with mock.patch.object(config.os.path, "isfile", return_value=True):
            conf = config.ImageConfig(override_filename='new')
            assert conf.get('image1') == {'filename': 'new'}
            assert conf.get('image2') == {'filename': 'new'}


@pytest.mark.parametrize('bad_config', [
    '{"foo": "bar"}',  # must be object
    '{"foo": {}}',  # no filename
    '{"foo": {random: junk}}',  # no unknown things should be here
    # timeout should be int
    '{"foo": {"filename": "x", "glance": {"upload_timeout": "3"}}}',
    # name should be string
    '{"foo": {"filename": "x", "glance": {"name": 1}}}',
    '{"foo": {"filename": "x", "dib": {}}}',  # no elements
    '{"foo": {"filename": "//"}}',  # bad path
    '{foo: {filename: x, dib: {elements: []}}}',  # elements shoudn't be empty
    '{foo: {filename: x, dib: {elements: [1]}}}',  # elements should be strings
    # flavors are not allowed in images
    '{foo: {filename: x, nova: {flavor: 3}}}',
    # version 2 is not supported yet
    '{foo: {filename: x, glance: {api_version: 2}}}',
    '{foo: {filename: x, glance: {name: 1}}}',  # name should be string
    # properties should be an object
    '{foo: {filename: x, glance: {properties:[foo, bar]}}}',
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
    good_config = '{foo: {filename: x, glance: {properties:{foo: bar}}},' \
        ' baz: {filename: y}}'
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
    good_config = '{foo: {filename: x, glance: {properties:{foo: bar}}}, '\
        'baz: {filename: y}}'
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
    mock_config = mock.mock_open(
        read_data='{"env1":{ "os_tenant_name": "good_name"}}'
    )
    with mock.patch.object(config, "open", mock_config):
        with mock.patch.object(config.os.path, "isfile", return_value=True):
            conf = config.Config()
            with pytest.raises(config.TestEnvironmentNotFoundInConfigError):
                conf.get_environment('env3')["os_tenant_name"]


def test_config_dict_conversion(config):
    d = {"a": 1, "b": "c"}
    x = config.Config(d)
    y = dict(x)
    assert y == d


def test_config_items(config):
    d = {"a": 1}
    l = list(config.Config(d).items())
    assert l == [('a', 1)]


def test_config_str(config):
    d = {"a": 1}
    assert str(config.Config(d)) == str(d)


def test_config_repr(config):
    d = {"a": 1}
    r = repr(config.Config(d))
    assert r == "Config({'a': 1})"


@pytest.mark.parametrize('bad_config', [
    '{"foo": "bar"}',
    '{"foo": {}}',
    '{"foo": {keystone: {}}}',
    '{"foo": {keystone: {api_version: 4}}}',
    '{"foo": {keystone: {}, nova: {}}}',
    '{"foo": {keystone: {}, nova: {nics: [], flavor: foo}}}',
    ('{"foo": {keystone: {}, nova: {flavor: foo, nics: '
        '[{net_id: 27c642c-invalid-uuid}]}}}')
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
    c = config.Config(input)
    c.config_file = 'foo'
    assert (query in c) is result


@pytest.mark.parametrize('bad_config', [
    '{"foo": "bar"}',
    '{"foo": {"keystone": {"api_version": 4}}}',
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
    c1 = config.Config(conf1)
    c2 = config.Config(conf2)
    assert config.get_max(c1, c2, path, 99) == result


def test_non_zero_true(config):
    assert bool(config.Config({'a': 1})) is True


def test_empty_is_false(config):
    assert bool(config.Config()) is False


@pytest.mark.parametrize('data', [
    {},
    {'a': 1},
    {'a': 1, 'b': 2}
])
def test_len(config, data):
    assert len(config.Config(data)) == len(data)


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
