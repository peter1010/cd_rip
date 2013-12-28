import sys
import os
import unittest

lib_path = os.path.join(os.path.dirname(__file__), "..")
sys.path.append(lib_path)

import rip_lib.cddb as cddb

class TestSequenceFunctions(unittest.TestCase):

    def setUp(self):
        pass
    
    def test_1(self):
        self.assertEqual(cddb.get_username(), "peter")
    
    def test_2(self):
        self.assertEqual(cddb.get_hostname(), "gandalf")

    def test_3(self):
        self.assertEqual(cddb.get_hello_str(),
            "hello=peter+gandalf+CDDB.py+1.4")

    def test_4(self):
        self.assertEqual(cddb.get_proto_str(),"proto=5")

    def test_5(self):
        class Dummy: pass
        obj = Dummy()
        obj.disc_id = "id"
        obj.disc_len = 9999
        tracks = [Dummy() for i in range(5)]
        for i, tobj in enumerate(tracks): tobj.length = i*10+6
        obj.num_tracks = len(tracks)
        obj.tracks = tracks
        self.assertEqual(cddb.get_query_str(obj),
                "cmd=cddb+query+id+5+6+16+26+36+46+9999")


if __name__ == '__main__':
    unittest.main()

