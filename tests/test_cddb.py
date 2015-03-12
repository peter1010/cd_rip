#!/usr/bin/env python

import sys
import os
import unittest
import socket
import urllib.request

lib_path = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, lib_path)

from rip_lib import freedb

class Dummy:
    pass

class Disc: 
    def __init__(self):
        self.tracks = []
    def disc_total_playtime(self):
        return 1000
    def calc_disc_len_in_secs(self):
        return 9999

class Track:
    pass

a_tiddle = b"\xc3".decode("iso-8859-1")

class Response:
    def readlines(self):
        """Notice the non-utf8 char"""
        return [
            b"",
            b"# Comment 1 \xc3",
            b"",
            b"# Comment 2",
            b"",
            b"name=value"
        ]
    def close(self):
        pass

class Mock_urlopen:
    def __init__(self):
        self.exec_cnt = 0
        self.exec_code = 503
        self.exec_url_error = False

    def __call__(self, url):
        if self.exec_cnt > 0:
            self.exec_cnt -= 1
            if self.exec_url_error:
                raise urllib.error.URLError(url,
                        self.exec_code)
            else:
                raise urllib.error.HTTPError(url,
                        self.exec_code, None, None, None)
        self.url = url
        return Response()


class TestCddbFunctions(unittest.TestCase):
   
    def setUp(self):
        self.mock_urlopen = Mock_urlopen()
        self.__saved_urlopen = urllib.request.urlopen = Mock_urlopen
        urllib.request.urlopen = self.mock_urlopen

    def tearDown(self):
        urllib.request.urlopen = self.__saved_urlopen


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
        freedb.get_hello_str.cache_clear()
        os.environ["EMAIL"] = "bob@localhost"
        self.assertEqual(freedb.get_hello_str(),
            "hello=bob+localhost+CDDB.py+1.4")

    def test_get_proto_str(self):
        self.assertEqual(freedb.get_proto_str(),"proto=5")

    def test_get_query_str(self):
        freedb.get_hello_str.cache_clear()
        obj = Disc()
        obj.disc_id = "id"
        obj.disc_len = 9999
        tracks = [Track() for i in range(5)]
        for i, tobj in enumerate(tracks):
            tobj.offset = i*10+6
        obj.num_tracks = len(tracks)
        obj.tracks = tracks
        self.assertEqual(freedb.get_query_str(obj),
                "cmd=cddb+query+0003e805+5+6+16+26+36+46+9999")

    def test_get_read_str(self):
        freedb.get_hello_str.cache_clear()
        obj = Dummy()
        obj.disc_id = "id"
        obj.category = "pop"
        self.assertEqual(freedb.get_read_str(obj, "0xde4"),
                "cmd=cddb+read+pop+0xde4")

    def test_perform_request_404(self):
        freedb.get_hello_str.cache_clear()
        self.mock_urlopen.exec_cnt = 1
        self.mock_urlopen.exec_code = 404
        lines = freedb.perform_request("http://freedb", "query", "hello", "proto") 
        self.assertEqual(lines, None)

    def test_perform_request_bad_url(self):
        freedb.get_hello_str.cache_clear()
        self.mock_urlopen.exec_cnt = 1
        self.mock_urlopen.exec_code = 404
        self.mock_urlopen.exec_url_error = True
        lines = freedb.perform_request("http://freedb", "query", "hello", "proto") 
        self.assertEqual(lines, None)


    def test_perform_request_503(self):
        expected_lines = ['', '# Comment 1 ' + a_tiddle, '', '# Comment 2', '',
            'name=value']
        freedb.get_hello_str.cache_clear()
        self.mock_urlopen.exec_cnt = 1
        lines = freedb.perform_request("http://freedb", "query", "hello", "proto") 
        self.assertEqual(lines, expected_lines)
        self.mock_urlopen.exec_cnt = 3
        lines = freedb.perform_request("http://freedb", "query", "hello", "proto") 
        self.assertEqual(lines, expected_lines)
        self.mock_urlopen.exec_cnt = 4
        lines = freedb.perform_request("http://freedb", "query", "hello", "proto") 
        self.assertEqual(lines, None)


    def test_perform_request_good(self):
        freedb.get_hello_str.cache_clear()
        lines = freedb.perform_request("http://freedb", "query", "hello", "proto") 
        self.assertEqual(lines,['', '# Comment 1 ' + a_tiddle, '', '# Comment 2', '',
            'name=value'])


    def test_8(self):
        freedb.get_hello_str.cache_clear()
        obj = Dummy()
        obj.disc_id = "id"
        obj.category = "pop"
        url = os.path.abspath(os.path.join(os.path.dirname(__file__), 
                             "freedb.txt"))
        items = freedb.read_cddb_metadata(obj, "file://" + url)
        print(items)
        self.assertEqual(items['name'], 'value')

if __name__ == '__main__':
    unittest.main()

