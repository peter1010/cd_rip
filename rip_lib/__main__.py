#!/usr/bin/env python3

##
# Copyright (c) 2014 Peter Leese
#
# Licensed under the GPL License. See LICENSE file in the project root for full license information.  
##


import os
import logging
import argparse

import rip_lib.main as rip
import rip_lib.discover as discover

def config_logging(logfile="log.txt"):
    if os.path.exists(logfile):
        os.unlink(logfile)
    fh = logging.FileHandler(logfile)
    fh.setLevel(logging.DEBUG)
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    fh.setFormatter(formatter)

    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    formatter = logging.Formatter(
        '%(levelname)s - %(message)s'
    )
    ch.setFormatter(formatter)
    root = logging.getLogger()
    root.addHandler(fh)
    root.addHandler(ch)

if __name__ == "__main__":
    config_logging()
    parser = argparse.ArgumentParser(description='Rip Cd contents to files')
    parser.add_argument('--only-rip', action='store_const', const=True,
            default=False, help='Only RIP to FLAC')
    parser.add_argument('--only-convert', action='store_const', const=True,
            default=False, help='Only convert flac to OGGs and MP3')
    parser.add_argument('--discover-flacs', action='store_const', const=True,
            default=False, help='Look for flacs to convert')
    parser.add_argument('wdir', nargs='?',
            help='Working directory', default=os.getcwd())
    args = parser.parse_args()
    dont = False
    directories = [args.wdir]
    if args.only_rip:
        if args.only_convert:
            print("Cannot both only-rip and only-convert")
            dont = True
        if args.discover_flacs:
            print("Cannot both only-rip and discover-flacs")
            dont = True
    elif args.discover_flacs:
        if not args.only_convert:
            print("Cannot both discover FLACs and RIP")
            dont = True
        directories = discover.find_directories(args.wdir)

    if not dont:
        for src_dir in directories:
            rip.main(args, src_dir)
