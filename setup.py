# -*- coding: utf-8 -*-

from setuptools import setup, find_packages


with open('README.md') as f:
    readme = f.read()

with open('LICENSE') as f:
    license = f.read()

setup(
    name='patentdata',
    version='0.0.2',
    description='A bag of functions and datamodels for playing around with patent data.',
    long_description=readme,
    author='Ben Hoyle',
    author_email='benjhoyle@gmail.com',
    url='https://github.com/benhoyle/patentdata',
    license=license,
    packages=find_packages(exclude=('tests', 'docs'))
    #packages=['patentdata']
)
