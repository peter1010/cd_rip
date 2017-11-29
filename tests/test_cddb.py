#!/usr/bin/env python

##
# Copyright (c) 2013 Peter Leese
#
# Licensed under the GPL License. See LICENSE file in the project root for full license information.  
##

import sys
import os
import unittest
import socket
import urllib.request

import mocks

lib_path = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, lib_path)

from rip_lib import freedb
from rip_lib import __main__ as rip_lib_main

class Dummy:
    pass

 
class Track:
    pass


class Disc: 
    def __init__(self):
        self.tracks = []
    def disc_total_playtime(self):
        return 1000
    def calc_disc_len_in_secs(self):
        return 9999

    def test_create1(self):
        self.disc_id = "id"
        self.disc_len = 9999
        tracks = [Track() for i in range(5)]
        for i, tobj in enumerate(tracks):
            tobj.offset = i*10+6
        self.num_tracks = len(tracks)
        self.tracks = tracks

a_tiddle = b"\xc3".decode("iso-8859-1")

class Response:
    def __init__(self, case):
        self.case = case

    def readlines(self):
        """Notice the non-utf8 char"""
        if self.case == 1:
            lines = [
                b"",
                b"# Comment 1 \xc3",
                b"",
                b"# Comment 2",
                b"",
                b"name=value"
            ]
        elif self.case == 2:
            lines =  [
                b"210",
                b"category1 disc-id1  artist1 / title1",
                b"category2 disc-id2  title2",
                b"category3 disc-id3  title3",
                b"."
            ]
        elif self.case == 3:
            lines = [
                b"200 category disc-id artist / title"
            ]
        else:
            lines =  [
                b"210",
                b"name1=value1",
                b"name2=value2",
                b"."
            ]
 
        return lines

    def close(self):
        pass


class TestCddbFunctions(unittest.TestCase):
   
    def setUp(self):
        freedb.get_hello_str.cache_clear()

    def tearDown(self):
        pass


    def test_split_on_slash(self):
        self.assertEqual(
            freedb.split_on_slash("asasas / fdfdf"),
            ("asasas", "fdfdf")
        )
        self.assertEqual(
            freedb.split_on_slash("asasas /"),
            (None, "asasas /")
        )


    def test_freedb_disc_id(self):
        disc = Disc()
        self.assertEqual(
            freedb.freedb_disc_id(disc),
            "0003e800"
        )
        tracks = [Track() for i in range(5)]
        for i, tobj in enumerate(tracks):
            tobj.offset = i*1001+801
        disc.tracks = tracks
        self.assertEqual(
            freedb.freedb_disc_id(disc),
            "2003e805"
        )


    def test_get_username(self):
        os.environ["EMAIL"] = "bob@localhost"
        self.assertEqual(freedb.get_username(), "bob")
        del os.environ["EMAIL"]
        os.environ["USER"] = "fred"
        self.assertEqual(freedb.get_username(), "fred")
        del os.environ["USER"]
        self.assertEqual(freedb.get_username(), str(os.geteuid()))


    def test_get_hostname(self):
        os.environ["EMAIL"] = "bob@localhost"
        self.assertEqual(freedb.get_hostname(), "localhost")
        del os.environ["EMAIL"]
        self.assertEqual(freedb.get_hostname(), socket.gethostname())


    def test_get_hello_str(self):
        os.environ["EMAIL"] = "bob@localhost"
        self.assertEqual(freedb.get_hello_str(),
            "hello=bob+localhost+CDDB.py+1.4")

    def test_get_proto_str(self):
        self.assertEqual(freedb.get_proto_str(),"proto=5")

    def test_get_query_str(self):
        obj = Disc()
        obj.test_create1()
        self.assertEqual(freedb.get_query_str(obj),
                "cmd=cddb+query+0003e805+5+6+16+26+36+46+9999")

    def test_get_read_str(self):
        obj = Dummy()
        obj.disc_id = "id"
        obj.category = "pop"
        self.assertEqual(freedb.get_read_str(obj, "0xde4"),
                "cmd=cddb+read+pop+0xde4")

    def test_perform_request_404(self):
        with mocks.PatchUrlOpen(None, 1, 404) as opener:
            lines = freedb.perform_request(
                    "http://freedb", "query", "hello", "proto"
            ) 
        self.assertEqual(lines, None)

    def test_perform_request_bad_url(self):
        with mocks.PatchUrlOpen(None, 1, "bad_url") as opener:
            lines = freedb.perform_request(
                "http://freedb", "query", "hello", "proto"
            ) 
        self.assertEqual(lines, None)


    def test_perform_request_503(self):
        expected_lines = ['', '# Comment 1 ' + a_tiddle, '', '# Comment 2', '',
            'name=value']
        with mocks.PatchUrlOpen(Response(1), 1, 503) as opener:
            lines = freedb.perform_request(
                    "http://freedb", "query", "hello", "proto"
            ) 
        self.assertEqual(lines, expected_lines)
        with mocks.PatchUrlOpen(Response(1), 3, 503) as opener:
            lines = freedb.perform_request(
                    "http://freedb", "query", "hello", "proto"
            ) 
        self.assertEqual(lines, expected_lines)
        with mocks.PatchUrlOpen(None, 4, 503) as opener:
            lines = freedb.perform_request(
                    "http://freedb", "query", "hello", "proto"
            ) 
        self.assertEqual(lines, None)


    def test_perform_request_good(self):
        with mocks.PatchUrlOpen(Response(1), 0, None) as opener:
            lines = freedb.perform_request(
                    "http://freedb", "query", "hello", "proto"
            ) 
        self.assertEqual(lines,
                ['', '# Comment 1 ' + a_tiddle, '',
                 '# Comment 2', '', 'name=value'])

    def test_query_cddb210(self):
        obj = Disc()
        obj.test_create1()
        with mocks.PatchUrlOpen(Response(2), 0, None) as opener:
            with mocks.PatchInput(["1"]) as p:
                result = freedb.query_cddb(obj)
        self.assertEqual(result.category, "category2")
        self.assertEqual(result.disc_id, "disc-id2")
        self.assertEqual(result.artist, None)
        self.assertEqual(result.title, "title2")
        self.assertEqual(result.name(), "title2")

    def test_query_cddb200(self):
        obj = Disc()
        obj.test_create1()
        with mocks.PatchUrlOpen(Response(3), 0, None) as opener:
            result = freedb.query_cddb(obj)
        self.assertEqual(result.category, "category")
        self.assertEqual(result.disc_id, "disc-id")
        self.assertEqual(result.artist, "artist")
        self.assertEqual(result.title, "title")
        self.assertEqual(result.name(), "artist / title")


    def test_read_cddb_metadata(self):
        obj = Dummy()
        obj.disc_id = "id"
        obj.category = "pop"
        url = os.path.abspath(os.path.join(os.path.dirname(__file__), 
                             "freedb.txt"))
        with mocks.PatchUrlOpen(Response(4), 0, None) as opener:
            items = freedb.read_cddb_metadata(obj, "file://" + url)
        print(items)
        self.assertEqual(items['name1'], 'value1')
        self.assertEqual(items['name2'], 'value2')


if __name__ == '__main__':
    rip_lib_main.config_logging()
    unittest.main()

