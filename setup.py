#!/usr/bin/env python

from pip._internal.req import parse_requirements
from setuptools import setup, find_packages


setup(
    name='ledslie',
    version="0.0.1",
    description='Led display',
    packages=find_packages(),
    install_reqs=parse_requirements('./requirements.txt', session=False),
    package_data = {
        'ledslie': [
            'interface/templates/*',
            # 'defaults.conf',
        ],
        'spacestate': [],
        'serial2mqtt': [],
        'processors': [
            'resources'
        ],
        'reporters': [],
    },
)
