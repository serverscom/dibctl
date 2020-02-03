#!/usr/bin/python
import os
import inspect
import sys
import pytest
import tempfile


@pytest.fixture
def i_p():
    from dibctl import image_preprocessing
    return image_preprocessing


@pytest.mark.parametrize('input, output', [
    ["", ""],
    ["foo", "foo"],
    ["%(input_filename)s", "name"],
    ["%(input_filename)s.%(disk_format)s", "name.raw"],
    ["%(input_filename)s.%(container_format)s", "name.bare"],
])
def test_prep_output_name_normal(i_p, input, output):
    p = i_p.Preprocess('name', {'disk_format': 'raw'}, {'output_filename': input, 'cmdline': 'ignore'})
    p.interpolate()
    assert p.output_filename == output


@pytest.mark.parametrize('input', [
    "%",
    "%{foo}",
    "/tmp/tmpyPhzXr"
    "%(unknown_variable)",
    "%(unknown_variable)s",
    "%(bad"
])
def test_prep_output_name_bad(i_p, input):
    p = i_p.Preprocess('name', {'disk_format': 'raw'}, {'output_filename': input, 'cmdline': 'ignore'})
    with pytest.raises(i_p.config.ConfigError):
        p.interpolate()


@pytest.mark.parametrize('input, output', [
    ["", ""],
    ["foo bar", "foo bar"],
    ["qemu-img %(input_filename)s %(output_filename)s", "qemu-img name name.raw"],
    ["qemu-img -O %(disk_format)s %(input_filename)s %(output_filename)s", "qemu-img -O raw name name.raw"]
])
def test_prep_output_cmdline_normal(i_p, input, output):
    p = i_p.Preprocess(
        'name',
        {'disk_format': 'raw'},
        {'output_filename': "%(input_filename)s.%(disk_format)s", 'cmdline': input}
    )
    p.interpolate()
    assert p.command_line == output


@pytest.mark.parametrize('input', [
    "%",
    "%{foo}",
    "%(unknown_variable)",
    "%(unknown_variable)s",
    "%(bad"
])
def test_prep_output_cmdline_bad(i_p, input):
    p = i_p.Preprocess(
        'name',
        {'disk_format': 'raw'},
        {'output_filename': "%(input_filename)s.%(disk_format)s", 'cmdline': input}
    )
    with pytest.raises(i_p.config.ConfigError):
        p.interpolate()


def test_context_no_preprocessing(i_p):
    with i_p.Preprocess('name', {}, {}) as new_name:
        assert new_name == 'name'


def test_context_reuse_existing_file_no_exec(i_p):
    with tempfile.NamedTemporaryFile() as t:
        with i_p.Preprocess(
            'foo',
            {},
            {'output_filename': t.name, "cmdline": "exit 1", "use_existing": True}
        ) as new_name:
            assert new_name == t.name


def test_context_use_existing_no_file(i_p):
    with tempfile.NamedTemporaryFile() as t:
        tempname = t.name
    del t
    with i_p.Preprocess(
        tempname,
        {},
        {'output_filename': tempname, "cmdline": "touch %(input_filename)s", "use_existing": True}
    ) as new_name:
        assert new_name == tempname
    os.remove(tempname)


def test_context_delete_after_upload_no_use_existing(i_p):
    with tempfile.NamedTemporaryFile() as t:
        tempname = t.name
    del t
    with i_p.Preprocess(
        tempname,
        {},
        {'output_filename': tempname, "cmdline": "touch %(input_filename)s"}
    ) as new_name:
        assert new_name == tempname
    assert os.path.isfile(tempname) is False


def test_context_file_existed_before_upload(i_p):
    with tempfile.NamedTemporaryFile(delete=False) as t:
        tempname = t.name
        t.write(b"no!")
    del t
    with i_p.Preprocess(
        tempname,
        {},
        {'output_filename': tempname, "cmdline": "touch %(input_filename)s"}
    ) as new_name:
        assert new_name == tempname
        assert "no!" not in open(tempname, 'r').read()
    assert os.path.isfile(tempname) is False


def test_context_do_not_delete_after_upload_no_use_existing(i_p):
    with tempfile.NamedTemporaryFile() as t:
        tempname = t.name
    del t
    with i_p.Preprocess(
        tempname,
        {},
        {'output_filename': tempname, "cmdline": "touch %(input_filename)s", 'delete_processed_after_upload': False}
    ) as new_name:
        assert new_name == tempname
    assert os.path.isfile(tempname) is True
    os.remove(tempname)


def test_context_assertion_on_exec(i_p):
    with tempfile.NamedTemporaryFile() as t:
        tempname = t.name
    del t
    with pytest.raises(i_p.PreprocessError):
        with i_p.Preprocess(
            tempname,
            {},
            {'output_filename': tempname, "cmdline": "exit 1"}
        ):
            pass


def test_context_no_file_created(i_p):
    with tempfile.NamedTemporaryFile() as t:
        tempname = t.name
    del t
    with pytest.raises(i_p.PreprocessError):
        with i_p.Preprocess(
            tempname,
            {},
            {'output_filename': tempname, "cmdline": "exit 0"}
        ):
            pass


def test_context_manager_without_processing(i_p):
    with tempfile.NamedTemporaryFile() as t:
        tempname = t.name
    del t
    with i_p.Preprocess(
        tempname,
        {},
        {}
    ) as new_name:
        assert tempname == new_name


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
