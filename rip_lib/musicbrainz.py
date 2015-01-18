import urllib.request
import urllib.parse
import hashlib
import base64
import json
import logging

logger = logging.getLogger(__name__)


MUSICBRAINZ_SERVER = 'http://musicbrainz.org/ws/2/'
COVER_SERVER = 'http://coverartarchive.org/release/'

def mbase64(data):
    """musicbrainz version of base64 encoding"""
    data = base64.b64encode(data)
    inchars = b"/+="
    outchars = b"_.-"
    trantab = b"".maketrans(inchars, outchars)
    return data.translate(trantab)


def musicbrainz_disc_id(disc_info):
    """Cover disc info converted into musicbrainz disc ID"""
    data = []
    data.append("{:02X}".format(1))
    data.append("{:02X}".format(len(disc_info.tracks)))
    data.append("{:08X}".format(disc_info.calc_disc_len()))
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
    logging.debug("Getting %s", url)
    try:
        response = urllib.request.urlopen(url)
    except urllib.error.URLError as err:
        print("Failed to connect to '{}' {}".format(url, err))
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
    return "".join(lines)


def query_database(disc_info, server_url=MUSICBRAINZ_SERVER):
    """Query the musicbrainz server using disc ID"""
    disc_id = musicbrainz_disc_id(disc_info)
    url = "{0}discid/{1}/?fmt=json".format(
        server_url, disc_id
    )
    data = perform_request(url)
    if data is None:
        return None
    obj = json.loads(data)
    assert obj["id"] == disc_id
    releases = obj["releases"]
    possible_discs = []
    for rel in releases:
        mbid, title = rel["id"], rel["title"]
        logger.info("MBID=%s title=%s", mbid, title)
        # print(json.dumps(rel, sort_keys=True, indent=4))
        possible_discs.append((title, mbid))
    if possible_discs is None:
        return None

    for i, entry in enumerate(possible_discs):
        print("[{}]\t{}".format(i, entry[0]))

    if len(possible_discs) > 1:
        selection = input("Select an entry [default=0]?")
        selection = 0 if selection == "" else int(selection)
    else:
        selection = 0
    return possible_discs[selection]


def read_track_metadata(disc_info, server_url=MUSICBRAINZ_SERVER):
    url = "{0}release/{1}/?inc=artist-credits+recordings&fmt=json".format(
        server_url, disc_info.mbid
    )
    data = perform_request(url)
    if data is None:
        return None
    obj = json.loads(data)
    print(json.dumps(obj, sort_keys=True, indent=4))
    assert obj["id"] == disc_info.mbid
    media = obj["media"]
    assert(len(media) == 1)
    media = media[0]
    for track in media["tracks"]:
#        print(json.dumps(track, sort_keys=True, indent=4))
        num = int(track["number"])
        length = int(track["length"])
        title = track["title"]
        logger.info("[%i] %s (%i)", num, title, length)


def get_coverart(disc_info, filename="cover.jpg",
    server_url=COVER_SERVER
):
    """Read the covert art, the mbid must be known"""
    if not hasattr(disc_info, "mbid") or disc_info is None:
        entry = query_database(disc_info, MUSICBRAINZ_SERVER)
        if entry is None:
            disc_info.title = "unknown"
            return None
        disc_info.title = entry[0]
        disc_info.mbid = entry[1]

    url = "{0}{1}".format(
        server_url, disc_info.mbid
    )
    data = perform_request(url)
    if data is None:
        return None
    obj = json.loads(data)
    for image in obj["images"]:
        if image["front"]:
            resource = image["image"]
    print(resource)
#    print(json.dumps(obj, sort_keys=True, indent=4))
    try:
        response = urllib.request.urlopen(resource)
    except urllib.error.URLError as err:
        print("Failed to connect to '{}' {}".format(url, err))
        return None
    with open(filename, "wb") as out_fp:
        out_fp.write(response.read())


def get_track_info(disc_info, server_url=MUSICBRAINZ_SERVER):
    """Get the Track Info"""
    if not hasattr(disc_info, "mbid") or disc_info is None:
        entry = query_database(disc_info, server_url)
        if entry is None:
            disc_info.title = "unknown"
            return None
        disc_info.title = entry[0]
        disc_info.mbid = entry[1]


    entries = read_track_metadata(disc_info)

    print(disc_info.title)
#    for track in disc_info.tracks:
#        print(track.num, track.artist, "/", track.title)
    return entries


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
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
