import sys
import subprocess
import logging

logger = logging.getLogger(__name__)

DEVICE = "/dev/sr0"


def split_on_slash(value):
    idx = value.find(" / ")
    if idx >= 0:
        first = value[:idx].strip()
        second = value[idx + 3:].strip()
    else:
        first = None
        second = value.strip()
    return first, second


def read_discid(devname=DEVICE):
    args = ["cd-discid", devname]
    try:
        info = subprocess.check_output(args)
    except FileNotFoundError:
        print("Check {} is installed\n".format(args[0]))
        sys.exit(1)
    except subprocess.CalledProcessError:
        print("No CD found\n")
        return None
    info = info.decode("ascii").split()
    disc_id = info[0]
    num_tracks = int(info[1])
    tracks = [int(x) for x in info[2:-1]]
    disc_len = int(info[-1])
    assert num_tracks == len(tracks)
    return (disc_id, disc_len, tracks)


def timeStr2time(line):
    assert line[0] == '[' and line[-1] == ']'
    line = line[1:-1]
    mins, secs = line.split(":")
    return int(mins) * 60 + float(secs)


def time2cuetime(secs):
    """Cue time is in mm:ss:ff where ff is 1/75 of a second"""
    iMins = int(secs // 60)
    secs -= 60 * iMins
    iSecs = int(secs)
    iFF = int(75 * (secs-iSecs))
    return "{:02}:{:02}:{:02}".format(iMins, iSecs, iFF)


def read_toc(devname=DEVICE):
    """Read and parse the CD TOC"""
    args = ["cdparanoia", "-d", DEVICE, "-Q"]
    try:
        info = subprocess.check_output(args, stderr=subprocess.STDOUT)
    except FileNotFoundError:
        print("Check {} is installed\n".format(args[0]))
        sys.exit(1)
    except subprocess.CalledProcessError:
        print("No CD found\n")
        return None
    lines = info.decode("ascii").splitlines()
    assert lines[0].startswith("cdparanoia")
    lines.pop(0)
    while lines[0] == '':
        lines.pop(0)
    assert lines[0].startswith("Table of contents")
    lines.pop(0)
    headers = lines[0].split()
    lines.pop(0)
    assert lines[0].startswith("=================")
    lines.pop(0)
    rows = []
    #headers = 'track', 'length', 'begin', 'copy', 'pre', 'ch'
    for line in lines:
        values = line.split()
        data = {}
        for hdr in headers:
            if hdr in ("length", "begin"):
                sectors, time, values = values[0], values[1], values[2:]
                value = (int(sectors), timeStr2time(time))
            else:
                value, values = values[0], values[1:]
                if hdr in ("copy", "pre"):
                    value = value.lower()
                    if value == 'no':
                        value = False
                    elif value == 'yes':
                        value = True
                    else:
                        raise RuntimeError(value)
                elif hdr == "track":
                    if value == "TOTAL":
                        data = None
                        break
                    assert value[-1] == '.'
                    value = int(value[:-1])
                else:
                    value = int(value)
            data[hdr] = value
        if not data:
            break
        rows.append(data)
    return rows



class TrackInfo:
    def __init__(self, trackNum, trackOffset):
        # Track Number is one-based
        self.num = trackNum
        self.offset = trackOffset
        self.artist = "unknown"
        self.title = "unknown"
        self.begin = 0
        self.length = 0

    def add_toc_info(self, pre, begin, length):
        self.pre_emphasis = pre
        self.begin = begin[1]
        self.length = length[1]

    def add_cddb_metadata(self, metadata):
        i = self.num -1 # Cover to zero based
        try:
            ttitle = metadata["TTITLE%i" % i]
        except KeyError:
            try:
                ttitle = metadata["TTITLE%02i" % i]
            except KeyError:
                return
        artist, title = split_on_slash(ttitle)
        if artist is not None:
            self.artist = artist
        self.title = title

    def print_details(self):
        print("TRACK ID={:0>2} OFF={:>6} {} ARTIST='{}' TITLE='{}'".format(
            self.num,
            self.offset,
            time2cuetime(self.begin),
            self.artist,
            self.title
        ))

    def write_cue(self, out_fp):
        out_fp.write('  TRACK {} AUDIO\n'.format(self.num))
        out_fp.write('    TITLE "{}"\n'.format(self.title))
        out_fp.write('    PERFORMER "{}"\n'.format(self.artist))
        out_fp.write('    INDEX 01 {}\n'.format(time2cuetime(self.begin)))


class DiscInfo(object):

    def __init__(self):
        self.disc_id = None
        self.disc_len = 0
        self.tracks = []
        self.title = None
        self.artist = None

    def read_disk(self, devname=DEVICE):
        info = read_discid(devname)
        if info:
            self.disc_id = info[0]
            self.disc_len = info[1]
            self.tracks = [TrackInfo(i+1, x) for i, x in enumerate(info[2])]
            info2 = read_toc(devname)
            for row in info2:
                idx = row['track']-1
                self.tracks[idx].add_toc_info(
                    row['pre'],
                    row['begin'],
                    row['length']
                )
            return True
        return False

    @property
    def num_tracks(self):
        return len(self.tracks)

    def __repr__(self):
        return "DiscId:%s - (%s)" % (
            self.disc_id, ",".join([str(x.offset) for x in self.tracks])
        )

    def add_cddb_metadata(self, metadata):
        try:
            artist, title = split_on_slash(metadata["DTITLE"])
        except KeyError:
            artist, title = None, None
        if artist:
            for track in self.tracks:
                track.artist = artist
        if title:
            self.title = title

        for track in self.tracks:
            track.add_cddb_metadata(metadata)

    def print_details(self):
        print()
        print("DISC ID={:0>2} LENGTH={:>6} ARTIST='{}' TITLE='{}'".format(
            self.disc_id,
            self.disc_len,
            self.artist,
            self.title
        ))
        print()
        for track in self.tracks:
            track.print_details()

    def write_cuefile(self, out_fp):
        out_fp.write('PERFORMER "{}"\n'.format(self.artist))
        out_fp.write('TITLE "{}"\n'.format(self.title))
        for track in self.tracks:
            track.write_cue(out_fp)
