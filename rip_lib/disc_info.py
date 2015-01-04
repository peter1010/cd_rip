import sys
import subprocess
import logging


logger = logging.getLogger(__name__)

DEVICE = "/dev/sr0"


def read_discid(devname=DEVICE):
    """Perform a cd-discid call"""
    args = ["cd-discid", "--musicbrainz", devname]
#    args = ["cd-discid", devname]
    try:
        info = subprocess.check_output(args)
    except FileNotFoundError:
        logger.error("Check {} is installed", args[0])
        sys.exit(1)
    except subprocess.CalledProcessError:
        logger.error("No CD found")
        return None
    info = info.decode("ascii").split()
    if args[1] == "--musicbrainz":
        disc_id = None
        num_tracks = int(info[0])
        tracks = [int(x) for x in info[1:-1]]
        disc_len = int(info[-1])
    else:
        disc_id = info[0]
        num_tracks = int(info[1])
        tracks = [int(x) for x in info[2:-1]]
        disc_len = 75 * int(info[-1])
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
        logger.error("Check {} is installed", args[0])
        sys.exit(1)
    except subprocess.CalledProcessError:
        logger.error("No CD found")
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
        self._artist = None
        self._title = None
        self.begin = 0
        self.length = 0

    def add_toc_info(self, pre, begin, length):
        self.pre_emphasis = pre
        self.begin = begin[1]
        print("length", length)
        self.length = length[0]

    def set_title(self, title):
        if title:
            self._title = title

    def get_title(self):
        if self._title is None:
            return "unknown"
        return self._title

    title = property(get_title, set_title)

    def set_artist(self, artist):
        if artist is not None:
            self._artist = artist

    def get_artist(self):
        if self._artist is None:
            return "unknown"
        return self._artist

    artist = property(get_artist, set_artist)

    def print_details(self):
        print("[{:0>2}] OFF={:>6} LEN={:>6} {} '{}' / '{}'".format(
            self.num,
            self.offset,
            self.length,
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

    def __init__(self, fps=75):
        self.disc_len = 0
        self.tracks = []
        self._title = None
        self._artist = None
        self.fps = fps

    def disc_total_playtime(self):
        return int((self.disc_len - self.lead_in) // self.fps)

    def read_disk(self, devname=DEVICE):
        info = read_discid(devname)
        if info:
            disc_id = info[0]
            self.disc_len = info[1]
            self.lead_in = info[2][0]
            self.tracks = [TrackInfo(i+1, x) for i, x in enumerate(info[2])]
            if disc_id:
                try:
                    import rip_lib.freedb as freedb
                    assert disc_id == freedb.freedb_disc_id(self)
                except ImportError:
                    pass
            if True:
                try:
                    import rip_lib.musicbrainz as musz
                    assert musz.musicbrainz_disc_id(self)
                except ImportError:
                    pass
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
        return "DiscLen:{} - ({})".format(
            self.disc_len, ",".join([str(x.offset) for x in self.tracks])
        )

    def set_artist(self, artist):
        """Set the artist name for the Disc"""
        if artist:
            self._artist = artist
            for track in self.tracks:
                track.set_artist(artist)


    def get_artist(self):
        """Get the artist name for the Disc"""
        if self._artist is None:
            return "unknown"
        return self._artist

    artist = property(get_artist, set_artist)

    def set_title(self, title):
        """Set the title for the disc"""
        if title:
            self._title = title

    def get_title(self):
        if self._title is None:
            return "unkown"
        return self._title

    title = property(get_title, set_title)

    def print_details(self):
        print()
        print("'{}' / '{}' LEAD_IN={} LENGTH={} FFS={}".format(
            self.artist,
            self.title,
            self.lead_in,
            self.disc_len,
            self.fps
        ))
        print()
        for track in self.tracks:
            track.print_details()

    def write_cuefile(self, out_fp):
        out_fp.write('PERFORMER "{}"\n'.format(self.artist))
        out_fp.write('TITLE "{}"\n'.format(self.title))
        for track in self.tracks:
            track.write_cue(out_fp)
