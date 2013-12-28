import os
import sys
import subprocess
import socket

DEVICE="/dev/sr0"

def splitOnSlash(value):
    idx = value.find(" / ")
    if idx >= 0:
        first = value[:idx].strip()
        second = value[idx+3:].strip()
    else:
        first = None
        second = value.strip()
    return first, second


class TrackInfo:
    def __init__(self, trackNum, trackLen):
        self.num = trackNum
        self.length = trackLen
        self.artist = "unknown"
        self.title = "unknown"

    def add_cddb_metadata(self, metadata):
        try:
            ttitle = metadata["TTITLE%i" % self.num]
        except KeyError:
            try:
                ttitle = metadata["TTITLE%02i" % self.num]
            except KeyError:
                return
        artist, title = splitOnSlash(ttitle)
        if artist is not None:
            self.artist = artist
        self.title = title

    def print_details(self):
        print("TRACK ID=", self.num)
        print("TRACK LENGTH=", self.length)
        print("TRACK TITLE=", self.title)
        print("TRACK ARTIST=", self.artist)



class DiscInfo(object):

    def __init__(self):
        self.disc_id = None
        self.disc_len = 0
        self.tracks = []
        self.title = None
        self.artist = None

    def read_disk(self, devname=DEVICE):
        args = ["cd-discid", devname]
        try:
            info = subprocess.check_output(args)
        except FileNotFoundError:
            print("Check %s is installed\n" % args[0])
            sys.exit(1)
        except subprocess.CalledProcessError:
            print("No CD found\n")
            return False
        info = info.decode("ascii").split()
        self.disc_id = info[0]
        self.disc_len = int(info[-1])
        assert(int(info[1]) == len(info)-3)
        self.tracks = [TrackInfo(i,int(x)) for i,x in enumerate(info[2:-1])]
        return True

    @property
    def num_tracks(self):
        return len(self.tracks)
    
    def __repr__(self):
        return "DiscId:%s - (%s)" % (self.disc_id, ",".join([str(x.length) for x in self.tracks]))

    def add_cddb_metadata(self, metadata):
        try:
            artist, title = splitOnSlash(metadata["DTITLE"])
        except KeyError:
            artist, title = None, None
        if artist: 
            for t in self.tracks:
                t.artist = artist
        if title:
            self.title = title

        for t in self.tracks:
            t.add_cddb_metadata(metadata)

    def print_details(self):
        print("DISC ID=", self.disc_id)
        print("DISC LENGTH=", self.disc_len)
        print("DISC TITLE=", self.title)
        print("DISC ARTIST=", self.artist)
        for t in self.tracks:
            t.print_details()

