import urllib.request
import urllib.parse
import hashlib
import base64
import json
import logging

logger = logging.getLogger(__name__)


DEF_SERVER = 'http://musicbrainz.org/ws/2/'

def mbase64(data):
    data = base64.b64encode(data)
    inchars = b"/+="
    outchars = b"_.-"
    trantab = b"".maketrans(inchars, outchars)
    return data.translate(trantab)


def musicbrainz_disc_id(disc_info):
    data = []
    data.append("{:02X}".format(1))
    data.append("{:02X}".format(len(disc_info.tracks)))
    data.append("{:08X}".format(disc_info.disc_len))
    for track in disc_info.tracks:
        data.append("{:08X}".format(track.offset))
    data += ["00000000"] * (99 - len(disc_info.tracks))
    data = "".join(data)
    data = data.encode("ascii")
    chksum = hashlib.sha1()
    chksum.update(data)
    data = chksum.digest()
    return mbase64(data).decode("ascii")


def perform_request(url):
    """Perform a read request to server"""
    print(">", url)
    try:
        response = urllib.request.urlopen(url)
    except urllib.error.URLError as err:
        print("Failed to connect to '%s'" % server_url, err)
        return None
    lines = []
    for line in response.readlines():
        try:
            line = line.decode("utf-8")
        except UnicodeDecodeError:
            line = line.decode("iso-8859-1")
        line = line.strip()
        lines.append(line)
        print("<", line)
    response.close()
    return lines


def query_database(disc_info, server_url=DEF_SERVER):
    """Query the musicbrainz server"""
    url = "{0}discid/{1}/?fmt=json".format(
        server_url, musicbrainz_disc_id(disc_info)
    )
    lines = "".join(perform_request(url))
    if lines is None:
        return None
    obj = json.loads(lines)
    print(json.dumps(obj, sort_keys=True, indent=4))

    possible_discs = []
    return possible_discs


def get_track_info(disc_info, cddb_srv=DEF_SERVER):
    """Get the Track Info"""
    possible_entries = query_database(disc_info, cddb_srv)
    if possible_entries is None:
        return None

    for i, entry in enumerate(possible_entries):
        print("[%i]\t%s\t%s" % (i, entry.category, entry.title))

    if len(possible_entries) > 1:
        selection = input("Select an entry [default=0]?")
        selection = 0 if selection == "" else int(selection)
    else:
        selection = 0

    try:
        entry = possible_entries[selection]

        disc_info.title = entry.title
        disc_info.category = entry.category

        entries = read_cddb_metadata(disc_info, cddb_srv)

    except IndexError:
        disc_info.title = "unknown"
        entries = None

    print(disc_info.title)
#    for track in disc_info.tracks:
#        print(track.num, track.artist, "/", track.title)
    return entries


if __name__ == "__main__":
    class Dummy:
        pass
    info = Dummy()
    info.disc_len = 0x000309B1
    info.tracks = [Dummy() for i in range(14)]
    offsets = (
        0x96, 0xD33, 0x5423, 0xA578, 0xF903, 0x13F42, 0x14D7D, 0x19409,
        0x1D1A0, 0x1F9FF, 0x24014, 0x278B1, 0x28265, 0x2C6F2
    )
    for idx, track in enumerate(info.tracks):
        track.offset = offsets[idx]
    assert "AzDOLlCcF6n_xb9u_4JflT7xDK0-" == musicbrainz_disc_id(info)
    get_track_info(info)
