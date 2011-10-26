#!/usr/bin/env python

import os
from setuptools import setup, find_packages

# Utility function to read the README file.
# Used for the long_description.  It's nice, because now 1) we have a top level
# README file and 2) it's easier to type in the README file than to put a raw
# string in below ...
def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()

setup(name='islandora_microservices',
      version='2.0',
      description='Fedora/Islandora Microservice System',
      author='Jonathan Green, Alexander O''Neill',
      author_email='islandora@googlegroups.com',
      maintainer='Jonathan Green',
      maintainer_email='jonathan@discoverygarden.ca',
      url='http://islandora.ca/',
      long_description=read('README'),
      install_requires=['fcrepo', 'stomp.py<=3.0.3', 'yapsy', 'lxml'],
     )
