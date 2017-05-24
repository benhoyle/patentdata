# -*- coding: utf-8 -*-

from setuptools import setup, find_packages


with open('README.md') as f:
    readme = f.read()

with open('LICENSE') as f:
    license = f.read()

setup(
    name='patentdata',
    version='0.0.5',
    description='A bag of functions and datamodels for playing around with patent data.',
    long_description=readme,
    author='Ben Hoyle',
    author_email='benjhoyle@gmail.com',
    url='https://github.com/benhoyle/patentdata',
    license=license,
    packages=find_packages(exclude=('tests', 'docs')),
    install_requires=[
        'beautifulsoup4>=4.5.3'
        'lxml>=3.7.3'
        'nltk>=3.2.2'
        'pytest>=3.0.6'
        'python-dateutil>=2.6.0'
        'python-epo-ops-client>=2.1.0'
        'requests>=2.13.0'
        'six>=1.10.0'
    ]
    #packages=['patentdata']
)
