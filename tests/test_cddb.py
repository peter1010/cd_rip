import sys
import os
import unittest
import socket

lib_path = os.path.join(os.path.dirname(__file__), "..")
sys.path.append(lib_path)

import rip_lib.cddb as cddb

class Dummy: 
    pass

class TestCddbFunctions(unittest.TestCase):

    
    def test_1(self):
        os.environ["EMAIL"] = "bob@localhost"
        self.assertEqual(cddb.get_username(), "bob")
        del os.environ["EMAIL"]
        os.environ["USER"] = "fred"
        self.assertEqual(cddb.get_username(), "fred")
        del os.environ["USER"]
        self.assertEqual(cddb.get_username(), str(os.geteuid()))


    def test_2(self):
        os.environ["EMAIL"] = "bob@localhost"
        self.assertEqual(cddb.get_hostname(), "localhost")
        del os.environ["EMAIL"]
        self.assertEqual(cddb.get_hostname(), socket.gethostname())


    def test_3(self):
        os.environ["EMAIL"] = "bob@localhost"
        self.assertEqual(cddb.get_hello_str(),
            "hello=bob+localhost+CDDB.py+1.4")

    def test_4(self):
        self.assertEqual(cddb.get_proto_str(),"proto=5")

    def test_5(self):
        obj = Dummy()
        obj.disc_id = "id"
        obj.disc_len = 9999
        tracks = [Dummy() for i in range(5)]
        for i, tobj in enumerate(tracks): tobj.length = i*10+6
        obj.num_tracks = len(tracks)
        obj.tracks = tracks
        self.assertEqual(cddb.get_query_str(obj),
                "cmd=cddb+query+id+5+6+16+26+36+46+9999")

    def test_6(self):
        obj = Dummy()
        obj.disc_id = "id"
        obj.category = "pop"
        self.assertEqual(cddb.get_read_str(obj),
                "cmd=cddb+read+pop+id")

    def test_7(self):
        url = os.path.abspath(os.path.join(os.path.dirname(__file__), 
                             "cddb.txt"))
        lines = cddb.perform_request("file://" + url, "query", "hello", "proto") 
        self.assertEqual(lines,['', '# Comment 1', '', '# Comment 2', '',
            'name=value'])

    def test_8(self):
        obj = Dummy()
        obj.disc_id = "id"
        obj.category = "pop"
        url = os.path.abspath(os.path.join(os.path.dirname(__file__), 
                             "cddb.txt"))
        items = cddb.read_cddb_metadata(obj, "file://" + url)
        print(items)
        self.assertEqual(items['name'], 'value')

if __name__ == '__main__':
    unittest.main()

