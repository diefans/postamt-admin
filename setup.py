"""package setup"""

__version__ = "0.0.4"

import sys

from setuptools import setup, find_packages
from setuptools.command.test import test as TestCommand


class PyTest(TestCommand):
    """Our test runner."""

    user_options = [('pytest-args=', 'a', "Arguments to pass to py.test")]

    def initialize_options(self):
        TestCommand.initialize_options(self)
        self.pytest_args = ["src/postamt"]

    def finalize_options(self):
        # pylint: disable=W0201
        TestCommand.finalize_options(self)
        self.test_args = []
        self.test_suite = True

    def run_tests(self):
        # import here, cause outside the eggs aren't loaded
        import pytest
        errno = pytest.main(self.pytest_args)
        sys.exit(errno)


setup(
    name="Postamt",
    version=__version__,
    author="Oliver Berger",
    author_email="diefans@gmail.com",
    license="Apache Version 2",
    url="https://github.com/diefans/postamt-admin",

    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: Apache Software License',
        'Topic :: Communications :: Email',
        'Operating System :: OS Independent',
    ],
    keywords="postfix dovecot sqlite",
    package_dir={'': 'src'},
    namespace_packages=['postamt'],
    packages=find_packages(
        'src',
        exclude=[]
    ),
    include_package_data=True,
    zip_safe=False,

    entry_points="""\
    [console_scripts]
    postamt = postamt.scripts.admin:main
    """,

    install_requires=[
        'sqlalchemy',
        #'zope.sqlalchemy',
        'click',
    ],

    cmdclass={'test': PyTest},
    tests_require=[
        # tests
        'pytest',
        'pytest-pep8',
    ]
)
