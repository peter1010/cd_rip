#!/usr/bin/env python3

##
# Copyright (c) 2014 Peter Leese
#
# Licensed under the GPL License. See LICENSE file in the project root for full license information.  
##

from distutils.core import setup

setup(
    name='CD Rip',
    version='1.0',
    description="Yet another script for ripping CDs",
    url='https://github.com/peter1010/cd_rip',
    author='Peter1010',
    author_email='peter1010@localnet',
    license='GPL',
    package_dir={'rip_lib': 'rip_lib'},
    packages=['rip_lib'],
    data_files=[
        ('/usr/bin/', ('cd_rip.sh',))],
)
