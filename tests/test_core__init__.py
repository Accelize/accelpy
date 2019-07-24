# coding=utf-8
"""Test package initialization"""
import pytest


def unimport():
    """Un-import accelpy"""
    from gc import collect
    from sys import modules

    for module in tuple(modules):
        if module.startswith('accelpy'):
            del modules[module]
    collect()


def test_python_version():
    """Test Python version check"""
    from collections import namedtuple
    import sys

    # Mock system version
    sys_version_info = sys.version_info
    version_info = namedtuple(
        'Version_Info',
        ['major', 'minor', 'micro', 'releaselevel', 'serial'])

    # Ensure Accelpy is not imported
    unimport()

    # Test
    try:
        with pytest.raises(ImportError):
            sys.version_info = version_info(3, 5, 0, 'final', 0)
            import accelpy

    # Cleaning
    finally:
        sys.version_info = sys_version_info
        unimport()
