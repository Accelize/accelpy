# coding=utf-8
"""Pytest configuration"""
from os import scandir
from os.path import dirname, join, realpath, isdir, splitext


def parametrize_ansible_role(argvalues, ids):
    """
    Define parameters for testable Ansible roles.

    Args:
        argvalues (list): Parametrize args values
        ids (list): Parametrize ID
    """
    from accelpy._ansible import __file__ as ansible_root

    with scandir(join(dirname(realpath(ansible_root)), 'roles')) as entries:
        for entry in entries:
            if entry.is_dir() and isdir(join(entry.path, 'molecule')):
                ids.append(entry.name)
                argvalues.append(entry.path)


def parametrize_application_yml(argvalues, ids):
    """
    Define parameters for testable application definition.

    Args:
        argvalues (list): Parametrize args values
        ids (list): Parametrize ID
    """
    from accelpy._application import Application

    with scandir(dirname(realpath(__file__))) as entries:
        for entry in entries:
            name, ext = splitext(entry.name)
            if ext == '.yml' and name.startswith('test_'):
                app = Application(entry.path)
                if 'test' not in app._definition and not app.providers:
                    continue

                name = name.split("_", 1)[1].replace('_', '-')
                for provider in app.providers:
                    ids.append(f'{name}_{provider.replace(",", "-")}')
                    argvalues.append(dict(path=entry.path, provider=provider))


PARAMETRIZE = dict(
    ansible_role=parametrize_ansible_role,
    application_yml=parametrize_application_yml
)


def pytest_generate_tests(metafunc):
    """
    Generate tests for configurations.
    """
    for fixture_name in PARAMETRIZE:
        if fixture_name in metafunc.fixturenames:
            argvalues = []
            ids = []
            PARAMETRIZE[fixture_name](argvalues, ids)
            metafunc.parametrize(fixture_name, argvalues, ids=ids)
