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


def test_get_installed_version_actual(dib):
    assert dib.get_installed_version() is not None

