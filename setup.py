#! /usr/bin/env python3
#  coding=utf-8
"""Setup script

run "./setup.py --help-commands" for help.
"""
from datetime import datetime
from os import chdir
from os.path import dirname, abspath, join

from setuptools import setup, find_packages

# Sets Package information
PACKAGE_INFO = dict(
    name='accelpy',
    description='FPGA application provisioning utility',
    long_description_content_type='text/markdown; charset=UTF-8',
    classifiers=[
        # Must be listed on: https://pypi.org/classifiers/
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'Intended Audience :: System Administrators',
        'License :: OSI Approved :: Apache Software License',
        'Topic :: System :: Installation/Setup',
        'Topic :: System :: Software Distribution',
        'Topic :: System :: Systems Administration',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Operating System :: POSIX :: Linux'
    ],
    keywords='cloud fpga',
    author='Accelize',
    author_email='info@accelize.com',
    url='https://github.com/Accelize/accelpy',
    project_urls={
        'Documentation': 'https://accelpy.readthedocs.io',
        'Download': 'https://pypi.org/project/accelpy',
        'Accelize Website': 'https://www.accelize.com',
        'Contact': 'https://www.accelize.com/contact-us',
    },
    license='Apache License, Version 2.0',
    python_requires='>=3.6',
    install_requires=[
        'requests>=2.20.0',
        'ansible>=2.8',
        'argcomplete>=1.10',
        'colorama',
        # 'mitogen>=0.2.7',
        'awscli>=1.16'  # To remove once Terraform support spot instance tagging
    ],
    setup_requires=['setuptools'],
    tests_require=['pytest', 'molecule[docker]'],
    packages=find_packages(exclude=['docs', 'tests']),
    include_package_data=True,
    zip_safe=False,
    command_options={},
    entry_points={'console_scripts': [
        'accelpy=accelpy.__main__:_run_command']})

# Gets package __version__ from package
SETUP_DIR = abspath(dirname(__file__))
with open(join(SETUP_DIR, 'accelpy', '__init__.py')) as source_file:
    for line in source_file:
        if line.rstrip().startswith('__version__'):
            PACKAGE_INFO['version'] = line.split('=', 1)[1].strip(" \"\'\n")
            break

# Gets long description from readme
with open(join(SETUP_DIR, 'README.md')) as source_file:
    PACKAGE_INFO['long_description'] = source_file.read()

# Gets Sphinx configuration
PACKAGE_INFO['command_options']['build_sphinx'] = {
    'project': ('setup.py', PACKAGE_INFO['name'].capitalize()),
    'version': ('setup.py', PACKAGE_INFO['version']),
    'release': ('setup.py', PACKAGE_INFO['version']),
    'copyright': ('setup.py', '2019-%s, %s' % (
        datetime.now().year, PACKAGE_INFO['author']))}

# Runs setup
if __name__ == '__main__':
    chdir(SETUP_DIR)
    setup(**PACKAGE_INFO)
