# -*- coding: utf-8 -*-
from setuptools import setup, find_packages

with open('requirements.txt') as f:
	install_requires = f.read().strip().split('\n')

# get version from __version__ variable in opossum/__init__.py
from opossum import __version__ as version

setup(
	name='opossum',
	version=version,
	description='POS integration',
	author='ioCraft',
	author_email='contact@iocraft.org',
	packages=find_packages(),
	zip_safe=False,
	include_package_data=True,
	install_requires=install_requires
)
