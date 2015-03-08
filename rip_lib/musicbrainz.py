import urllib.request
import urllib.parse
import hashlib
import base64
import json
import logging
import time

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

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
    magic = mbase64(data).decode("ascii")
    logger.debug("Musicbrainz DISC ID = %s", magic)
    return magic


def perform_request(url):
    """Perform a read request to server"""
    logging.debug("Getting %s", url)
    headers = { 'User-Agent' : 'CD-RIP/1.0 (peter1010 at the github)' }
    req = urllib.request.Request(url, headers=headers)
    for i in range(5):
        try:
            response = urllib.request.urlopen(req)
        except urllib.error.HTTPError as err:
            print("Sleeping")
            time.sleep(3 + i*0.5)
            print("Awake")
            if err.code == 503:
                logger.debug("Failed with 503 so will try again")
                continue
            logger.error("Failed to connect to '%s' %s", url, err)
            return None
        except urllib.error.URLError as err:
            logger.error("Failed to connect to '%s' %s", url, err)
            return None
        break
    else:
        logger.error("Failed to connect to '%s' after %i attempts", url, i)
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

def _extract_artist(json_obj):
    artists = json_obj["artist-credit"]
    if len(artists) > 1:
        logger.warn("More that one Artist, (%i)", len(artists))
        for idx, artist in enumerate(artists):
            logger.debug("[%i] %s", idx, artist["artist"]["name"])
#    assert len(artists) == 1
    artist = artists[0]["artist"]["name"]
    logger.debug("Artist = %s", artist)
    return artist

def _select_media(json_obj, disc_info):
    choice = []
    for media in json_obj:
        num_of_tracks = media["track-count"]
        if num_of_tracks != len(disc_info.tracks):
            logger.warn("Reject media Num tracks %i != %i",
                num_of_tracks, len(disc_info.tracks)
            )
            continue
        for track in media["tracks"]:
            length = (int(track["length"]) + 500)//1000 # In seconds
            idx = int(track["number"])
            t_length = (disc_info.get_track(idx).length + disc_info.fps/2) // disc_info.fps
            diff = t_length - length
            if diff > 1 or diff < -1:
                logger.warn("Reject media track %i length %i s != %i s",
                    idx, length, _track.length
                )
                break
        else:
            choice.append(media)
    print( len(choice))
    assert len(choice) == 1
    return choice[0]


def read_track_metadata(disc_info, server_url=MUSICBRAINZ_SERVER):
    url = "{0}release/{1}/?inc=artist-credits+recordings&fmt=json".format(
        server_url, disc_info.mbid
    )
    data = perform_request(url)
    if data is None:
        return False
    obj = json.loads(data)
    result = json.dumps(obj, sort_keys=True, indent=4)
    for line in result.splitlines():
        logger.debug(">> %s", line)
    assert obj["id"] == disc_info.mbid
    media = _select_media(obj["media"], disc_info)
    disc_info.set_artist(_extract_artist(obj))
    for track in media["tracks"]:
#        print(json.dumps(track, sort_keys=True, indent=4))
        num = int(track["number"])
        title = track["title"]
        artist = _extract_artist(track)
        logger.info("[%i] %s / %s", num, artist, title)
        obj = disc_info.get_track(num)
        obj.set_title(title)
        obj.set_artist(artist)
    return True


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
        if not image["back"]:
            resource = image["image"]
    for line in json.dumps(obj, sort_keys=True, indent=4).splitlines():
        logger.debug(">> %s", line)

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
            return False
        disc_info.set_title(entry[0])
        disc_info.mbid = entry[1]

    return read_track_metadata(disc_info)


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
