import os
import socket
import urllib.request
import urllib.parse
import functools
import logging

logger = logging.getLogger(__name__)

#DEF_SERVER = 'http://freedb.freedb.org/~cddb/cddb.cgi'
DEF_SERVER = 'http://freedb.musicbrainz.org/~cddb/cddb.cgi'

CLIENT_NAME = 'CDDB.py'
CLIENT_VER = 1.4
CDDB_PROTO = 5


def split_on_slash(value):
    """Split on hash"""
    idx = value.find(" / ")
    if idx >= 0:
        first = value[:idx].strip()
        second = value[idx + 3:].strip()
    else:
        first = None
        second = value.strip()
    return first, second


def freedb_disc_id(disc_info):
    """Calculate the freedb disc ID"""
    chksum = 0
    for track in disc_info.tracks:
        start = int(track.offset/75)
        while start > 0:
            chksum += (start % 10)
            start //= 10
    chksum = chksum % 255
    return "{:02x}{:04x}{:02x}".format(
        chksum,
        disc_info.disc_total_playtime(),
        len(disc_info.tracks)
    )


def get_username():
    """Get a username for use in the Query request to CDDB database"""
    try:
        user = os.environ['EMAIL'].split('@')[0]
    except KeyError:
        try:
            user = os.environ['USER']
        except KeyError:
            user = str(os.geteuid()) or 'user'
    return user


def get_hostname():
    """Get a hostname for use in the Query request to CDDB database"""
    try:
        host = os.environ['EMAIL'].split('@')[1]
    except KeyError:
        host = socket.gethostname() or 'host'
    return host


@functools.lru_cache()
def get_hello_str(client_name=CLIENT_NAME, client_ver=CLIENT_VER):
    """Create the hello string for use in the Query request to CDDB database"""

    hello = "hello={0}+{1}+{2}+{3}".format(
        get_username(),
        get_hostname(),
        client_name,
        client_ver
    )
    return hello


def get_proto_str(proto_ver=CDDB_PROTO):
    """Create the proto string for use in the Query request to CDDB database"""
    return "proto={}".format(proto_ver)


def get_query_str(disc_info):
    """disc_info is an object that should contain following methods:
       - disc_id, num_tracks, disc_len and tracks.
       tracks should be a list of track objects each containing following:
       - length"""
    parts = []
    parts.append(str(freedb_disc_id(disc_info)))
    parts.append(str(disc_info.num_tracks))
    for track in disc_info.tracks:
        parts.append(str(track.offset))
    parts.append(str(disc_info.calc_disc_len()))
    return "cmd=cddb+query+{}".format(
        urllib.parse.quote_plus(" ".join(parts))
    )


def get_read_str(disc_info):
    """Return the string to send to server to read disc info"""
    return "cmd=cddb+read+{}+{}".format(
        disc_info.category, freedb_disc_id(disc_info)
    )


def perform_request(server_url, query_str, hello_str, proto_str):
    """Perform a read request to server"""
    url = "%s?%s&%s&%s" % (server_url, query_str, hello_str, proto_str)
    logger.debug("GET %s", url)
    try:
        response = urllib.request.urlopen(url)
    except urllib.error.URLError as err:
        logger.error("Failed to connect to '%s' %s", server_url, err)
        return None
    lines = []
    for line in response.readlines():
        try:
            line = line.decode("utf-8")
        except UnicodeDecodeError:
            line = line.decode("iso-8859-1")
        line = line.strip()
        lines.append(line)
    response.close()
    return lines


class CddbEntry(object):
    """Hold a CBBD entry"""

    def __init__(self, category, name):
        self.category = category
        self.artist, self.title = split_on_slash(name)

    def name(self):
        if self.artist:
            return "{} / {}".format(self.artist, self.title)
        return self.title


def query_cddb(disc_info, server_url=DEF_SERVER):
    """Query the CDDB server"""
    lines = perform_request(server_url, get_query_str(disc_info),
                            get_hello_str(), get_proto_str())
    if lines is None:
        return None
    # Four elements in header: status, category, disc-id, title
    header = lines.pop(0).split(' ', 3)

    status_code = int(header[0])
    possible_discs = []
    disc_id = freedb_disc_id(disc_info)

    if status_code == 200:		# OK
        assert header[2] == disc_id
        possible_discs.append(CddbEntry(header[1], header[3]))

    elif status_code == 211 or status_code == 210:  # multiple matches
        for line in lines:
            if line == '.':		# end of matches
                break
            # three elements in line: category, disc-id, artist / title
            body = line.split(' ', 2)

            if body[1] == disc_id:
                possible_discs.append(CddbEntry(body[0], body[2]))

    else:
        logger.error("Error code %i received", status_code)
        logger.error("Header = '%s'", header)
    if possible_discs is None:
        return None

    for i, entry in enumerate(possible_discs):
        print("[{}]\t{}\t{}".format(i, entry.category, entry.name()))

    if len(possible_discs) > 1:
        selection = input("Select an entry [default=0]?")
        selection = 0 if selection == "" else int(selection)
    else:
        selection = 0
    return possible_discs[selection]


def read_cddb_metadata(disc_info, server_url=DEF_SERVER):
    """Read Metadata from the CBBD server"""
    assert disc_info.category
    lines = perform_request(server_url, get_read_str(disc_info),
                            get_hello_str(), get_proto_str())
    if lines is None:
        return None

    header = lines.pop(0).split(' ', 3)
    status_code = int(header[0])
    entries = {}

    if status_code == 210 or status_code == 417:  # success or access denied
        for line in lines:
            if line == '.':
                break

            if line.startswith('#'):
                continue

            line = line.replace(r'\t', "\t").replace(r'\n', "\n").replace('\\',
                                "\\").strip()
            try:
                name, value = line.split("=", 2)
            except ValueError:
                continue
            name = name.strip()
            value = value.strip()
            if value:
                entries[name] = value
                logging.info("%s=%s", name, value)
        if status_code == 210:
            # success, parse the reply
            pass
        else:
            # access denied. :(
            logger.error("Error code %i received", status_code)
    else:
        logger.error("Error code %i received", status_code)
        logger.error("Header = '%s'", header)
        entries = None
    return entries


def get_track_info(disc_info, cddb_srv=DEF_SERVER):
    """Get the Track Info from cddb and set value is disc_info"""
    entry = query_cddb(disc_info, cddb_srv)
    if entry is None:
        disc_info.title = "unknown"
        return None

    disc_info.set_title(entry.title)
    disc_info.set_artist(entry.artist)
    disc_info.category = entry.category

    metadata = read_cddb_metadata(disc_info, cddb_srv)

    try:
        artist, title = split_on_slash(metadata["DTITLE"])
    except KeyError:
        artist, title = None, None

    disc_info.set_artist(artist)
    disc_info.set_title(title)

    for track in disc_info.tracks:
        i = track.num -1 # Cover to zero based
        try:
            ttitle = metadata["TTITLE%i" % i]
        except KeyError:
            try:
                ttitle = metadata["TTITLE%02i" % i]
            except KeyError:
                return
        artist, title = split_on_slash(ttitle)
        track.set_artist(artist)
        track.set_title(title)
