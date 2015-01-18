import sys
import subprocess
import logging


logger = logging.getLogger(__name__)

DEVICE = "/dev/sr0"
DEF_FPS = 75
CUE_RES = 75.0 # Cue file expresses LSB time in 1/75th of sec
DEF_LEAD_IN = 150

def call_cd_discid(devname=DEVICE):
    """Perform a cd-discid call"""
    args = ["cd-discid", "--musicbrainz", devname]
#    args = ["cd-discid", devname]
    try:
        info = subprocess.check_output(args)
    except FileNotFoundError:
        logger.error("Check %s is installed", args[0])
        return None, False
    except subprocess.CalledProcessError:
        logger.error("No CD found")
        return None, False
    info = info.decode("ascii").split()
    return info, args[1] == "--musicbrainz"


def timeStr2time(line):
    assert line[0] == '[' and line[-1] == ']'
    line = line[1:-1]
    mins, secs = line.split(":")
    secs, sectors = secs.split(".")
    return int(mins) * 60 + int(secs) + int(sectors) / CUE_RES


def time2cuetime(secs):
    """Cue time is in mm:ss:ff where ff is 1/75 of a second"""
    iMins = int(secs // 60)
    secs -= 60 * iMins
    iSecs = int(secs)
    iFF = int(CUE_RES * (secs-iSecs))
    return "{:02}:{:02}:{:02}".format(iMins, iSecs, iFF)

def str2bool(value):
    value = value.lower()
    if value == 'no':
        return False
    if value == 'yes':
        return True
    raise ValueError(value)


def read_toc(devname=DEVICE, lead_in=DEF_LEAD_IN, fps=DEF_FPS):
    """Read and parse the CD TOC"""
    args = ["cdparanoia", "-d", DEVICE, "-Q"]
    try:
        info = subprocess.check_output(args, stderr=subprocess.STDOUT)
    except FileNotFoundError:
        logger.error("Check %s is installed", args[0])
        return None, 0
    except subprocess.CalledProcessError:
        logger.error("No CD found")
        return None, 0
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
                time = timeStr2time(time)
                sectors = int(sectors)
                if time > 0:
                    fps = int(0.5 + sectors / time)
                    assert fps == DEF_FPS
                if hdr == "begin":
                    sectors += lead_in
                value = sectors
            else:
                value, values = values[0], values[1:]
                if hdr in ("copy", "pre"):
                    value = str2bool(value)
                elif hdr == "track":
                    if value == "TOTAL":
                        data = None
                        disc_len = lead_in + int(values[0])
                        break
                    assert value[-1] == '.'
                    value = int(value[:-1])
                else:
                    value = int(value)
            data[hdr] = value
        if not data:
            break
        rows.append(data)
    return rows, disc_len


class TrackInfo:
    def __init__(self, trackNum, trackOffset):
        # Track Number is one-based
        self.num = trackNum
        self.offset = trackOffset
        self._artist = None
        self._title = None
        self.begin = 0
        self.length = 0

    def calc_start_time(self):
        """Return start time in seconds"""
        return (self.offset - self.disc.lead_in) // self.disc.fps

    def add_toc_info(self, pre, length):
        self.pre_emphasis = pre
        self.length = length

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
            time2cuetime(self.calc_start_time()),
            self.artist,
            self.title
        ))

    def write_cue(self, out_fp):
        out_fp.write('  TRACK {} AUDIO\n'.format(self.num))
        out_fp.write('    TITLE "{}"\n'.format(self.title))
        out_fp.write('    PERFORMER "{}"\n'.format(self.artist))
        out_fp.write('    INDEX 01 {}\n'.format(
            time2cuetime(self.calc_start_time()))
        )


class DiscInfo(object):
    """Holds information about a disk, all duration units
    are in frames (i.e. disc sectors)"""

    def __init__(self, fps=DEF_FPS, lead_in=DEF_LEAD_IN):
        self.tracks = []
        self._title = None
        self._artist = None
        self.fps = fps
        self.lead_in = lead_in

    def calc_disc_len(self):
        return self.lead_in + \
                sum([track.length for track in self.tracks])

    def disc_total_playtime(self):
        return int((self.calc_disc_len() - self.lead_in) // self.fps)

    def add_track(self, track_num, track_offset):
        for track in self.tracks:
            if track.num == track_num:
                track.offset = track_offset
                return track
        track = TrackInfo(track_num, track_offset)
        track.disc = self
        self.tracks.append(track)
        return track

    def _read_discid(self, devname=DEVICE, fps=DEF_FPS):
        """Perform a cd-discid call"""
        info, is_musicbrainz = call_cd_discid(devname)
        if info is None:
            return False
        if is_musicbrainz:
            num_tracks = int(info[0])
            offsets = [int(x) for x in info[1:-1]]
            disc_len = int(info[-1])
        else:
            ### TO REMOVE, A cross-check
            disc_id = info[0]
            try:
                import rip_lib.freedb as freedb
                assert disc_id == freedb.freedb_disc_id(self)
            except ImportError:
                pass
            ###
            num_tracks = int(info[1])
            offsets = [int(x) for x in info[2:-1]]
            disc_len = fps * int(info[-1])
        assert num_tracks == len(offsets)
        lengths = [offsets[i+1] - offsets[i] \
            for i in range(num_tracks-1)
        ]
        lengths.append(disc_len - offsets[-1])
        self.lead_in = offsets[0]
        for i, offset in enumerate(offsets):
            track = self.add_track(i+1, offset)
            track.length = lengths[i]
        assert disc_len == self.calc_disc_len()
        return True

    def _read_toc(self, devname=DEVICE):
        self.lead_in = DEF_LEAD_IN
        info, disc_len = read_toc(devname, self.lead_in)
        if info is None:
            return False
        self.fps = DEF_FPS
        for row in info:
            num = row['track']
            offset = row['begin']
            if num == 1:
                assert self.lead_in == offset
            track = self.add_track(num, offset)
            track.add_toc_info(
                row['pre'],
                row['length']
            )
        assert disc_len == self.calc_disc_len()
        return True

    def read_disk(self, devname=DEVICE):
        got = self._read_discid(devname)
        got = self._read_toc(devname) or got
        if got:
            ### TO REMOVE, A cross-check
            try:
                import rip_lib.musicbrainz as musz
                assert musz.musicbrainz_disc_id(self)
            except ImportError:
                pass
            ###
            return True
        return False


    @property
    def num_tracks(self):
        return len(self.tracks)

    def __repr__(self):
        return "DiscLen:{} - ({})".format(
            self.calc_disc_len(),
            ",".join([str(x.offset) for x in self.tracks])
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
            self.calc_disc_len(),
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
