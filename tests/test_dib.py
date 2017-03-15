#!/usr/bin/python
import os
import inspect
import sys
import pytest
import mock
from mock import sentinel


@pytest.fixture
def dib():
    from dibctl import dib
    return dib


@pytest.fixture
def DIB(dib):
    DIB = dib.DIB(sentinel.filename, [sentinel.element])
    return DIB


def test_dib_cmdline_all_defaults(dib):
    dib = dib.DIB(sentinel.filename, [sentinel.element])
    assert dib.cmdline == ['disk-image-create', '-a', 'amd64', '-o', sentinel.filename, sentinel.element]


def test_dib_cmdline_no_tracing(dib):
    dib = dib.DIB(sentinel.filename, [sentinel.element], tracing=False)
    assert '-x' not in dib.cmdline


def test_dib_cmdline_tracing(dib):
    dib = dib.DIB(sentinel.filename, [sentinel.element], tracing=True)
    assert '-x' in dib.cmdline


def test_dib_cmdline_offline(dib):
    dib = dib.DIB(sentinel.filename, [sentinel.element], offline=True,  tracing=False)
    assert '--offline' in dib.cmdline


def test_dib_cmdline_additional_options(dib):
    opts = [sentinel.opt1, sentinel.opt2]
    dib = dib.DIB(sentinel.filename, [sentinel.element], additional_options=opts)
    assert opts[0] in dib.cmdline
    assert opts[1] in dib.cmdline


def test_dib_cmdline_no_elements(dib):
    with pytest.raises(dib.NoElementsError):
        dib = dib.DIB(sentinel.filename, [])


def test_prep_env(dib):
    with mock.patch.object(dib.os, "environ", {"key1": "value1"}):
        dib = dib.DIB(sentinel.filename, [sentinel.element], env={"key1": "value2", "key2": "value2"})
        new_env = dib._prep_env()
        assert new_env["key1"] == "value2"
        assert new_env["key2"] == "value2"


def test_prep_env_empy(dib):
    with mock.patch.object(dib.os, "environ", {"key1": "value1"}):
        dib = dib.DIB(sentinel.filename, [sentinel.element])
        new_env = dib._prep_env()
        assert new_env["key1"] == "value1"


def test_run_mocked_check_output(dib, DIB, capsys):
    with mock.patch.object(dib.subprocess, "Popen"):
        dib = dib.DIB("filename42", ["element42"])
        dib.run()
        out = capsys.readouterr()[0]
        assert 'filename42' in out
        assert 'element42' in out


def test_run_echoed(dib, DIB):
    dib = dib.DIB("filename", ["element1", "element2"], exec_path="echo")
    assert dib.run() == 0


def test_get_installed_version_normal(dib):
    with mock.patch.object(dib.pkg_resources, 'get_distribution') as mock_gd:
        mock_gd.return_value.version = '0.1.1'
        assert dib.get_installed_version() == dib.semantic_version.Version('0.1.1')


def test_get_installed_version_normal_with_rc(dib):
    with mock.patch.object(dib.pkg_resources, 'get_distribution') as mock_gd:
        mock_gd.return_value.version = '2.0.0rc2'
        assert dib.get_installed_version() == dib.semantic_version.Version('2.0.0-rc2')


def test_get_installed_version_no(dib):
    with mock.patch.object(dib.pkg_resources, 'get_distribution') as mock_gd:
        mock_gd.side_effect = dib.pkg_resources.DistributionNotFound
        with pytest.raises(dib.NoDibError):
            dib.get_installed_version()


def test_get_installed_version_actual(dib):
    assert dib.get_installed_version() is not None


def test_version_good(dib):
    assert dib._version('1.0.0') == dib.semantic_version.Version('1.0.0')


def test_version_not_bad(dib):
    assert dib._version('1.0.0rc1') == dib.semantic_version.Version('1.0.0-rc1')


def test_version_bad(dib):
    with pytest.raises(dib.BadVersion):
        dib._version('not-a-version')


@pytest.mark.parametrize('min_version, max_version', [
    [None, None],
    ['0.0.1', None],
    [None, '999.999.999'],
    ['0.0.1', '999.99.999']
])
def test_validate_version_pass(dib, min_version, max_version):
    assert dib.validate_version(min_version, max_version) is True


@pytest.mark.parametrize('min_version, max_version', [
    [None, '0.0.1'],
    ['999.999.999', '0.0.1'],
    ['999.999.999', None],
    ['0.0.1', '0.0.1'],
    ['999.999.999', '999.99.999']
])
def test_validate_version_not_pass(dib, min_version, max_version):
    with pytest.raises(dib.BadDibVersion):
        dib.validate_version(min_version, max_version)


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
