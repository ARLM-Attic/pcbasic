"""
PC-BASIC setup module.
based on https://github.com/pypa/sampleproject

(c) 2015 Rob Hagemans
This file is released under the GNU GPL version 3.
"""

from setuptools import setup, find_packages
from codecs import open
from os import path

here = path.abspath(path.dirname(__file__))

with open(path.join(here, 'DESCRIPTION.md'), encoding='utf-8') as f:
    long_description = f.read()

with open(path.join(here, 'pcbasic', 'data', 'version.txt'), encoding='utf-8') as f:
    version_string = f.read()


setup(
    name='pcbasic',
    version=version_string,
    description='Free, cross-platform emulator for the GW-BASIC family of interpreters.',
    long_description=long_description,
    url='http://pc-basic.org',
    author='Rob Hagemans',
    author_email='robhagemans@yahoo.co.uk',
    license='GPLv3',

    # See https://pypi.python.org/pypi?%3Aaction=list_classifiers
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: End Users/Desktop',
        'Topic :: System :: Emulators',
        'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
        'Programming Language :: Python :: 2.7',
    ],

    keywords='emulator interpreter basic retro legacy gwbasic basica pcjr tandy basicode',

    packages=find_packages(exclude=['doc', 'test', 'docsrc', 'packaging', 'patches']),

    # List run-time dependencies here.  These will be installed by pip when
    # your project is installed. For an analysis of "install_requires" vs pip's
    # requirements files see:
    # https://packaging.python.org/en/latest/requirements.html
    install_requires=['pygame', 'numpy', 'pyxdg', 'pyserial', 'pexpect'],

    # List additional groups of dependencies here (e.g. development
    # dependencies). You can install these using the following syntax,
    # for example:
    # $ pip install -e .[dev,test]
    #extras_require={
    #    'dev': ['check-manifest'],
    #    'test': ['coverage'],
    #},

    # If there are data files included in your packages that need to be
    # installed, specify them here.  If using Python 2.6 or less, then these
    # have to be included in MANIFEST.in as well.
    package_data={
        'pcbasic': ['data/*', 'encoding/*',
                    'font/*'],
    },

    # Although 'package_data' is the preferred approach, in some case you may
    # need to place data files outside of your packages. See:
    # http://docs.python.org/3.4/distutils/setupscript.html#installing-additional-files # noqa
    # In this case, 'data_file' will be installed into '<sys.prefix>/my_data'
    #data_files=[('my_data', ['data/data_file'])],

    # To provide executable scripts, use entry points in preference to the
    # "scripts" keyword. Entry points provide cross-platform support and allow
    # pip to create the appropriate form of executable for the target platform.
    entry_points={
        'console_scripts': [
            'pcbasic=pcbasic:main',
        ],
    },
)
