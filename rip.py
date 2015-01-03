#!/usr/bin/env python3

import os
import logging

import rip_lib.main as rip

logging.basicConfig(level=logging.DEBUG)
rip.main(os.getcwd())
