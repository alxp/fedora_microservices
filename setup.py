#!/usr/bin/env python
'''
Created on 2010-07-28

@author: aoneill
'''
import os
from setuptools import setup, find_packages

# Utility function to read the README file.
# Used for the long_description.  It's nice, because now 1) we have a top level
# README file and 2) it's easier to type in the README file than to put a raw
# string in below ...
def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()

setup(name='fedora_micro_services',
      version='0.1',
      description='Fedora Stomp Listener',
      author='Alexander O''Neill',
      author_email='aoneill@upei.ca',
      url='http://islandora.ca/',
      long_description=read('README'),
      packages=find_packages('src'),
      py_modules=['src/fedora_listener/__main__', 'content_model_listener/__main__'],
      package_dir = {'': 'src'},
      install_requires=['FeedParser', 'fcrepo', 'stomp.py', 'yapsy'],
     )
