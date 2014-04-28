import os
import sys
import subprocess
import socket
import urllib.request
import urllib.parse

DEF_SERVER = 'http://freedb.freedb.org/~cddb/cddb.cgi'
CLIENT_NAME = 'CDDB.py'
CLIENT_VER = 1.4
CDDB_PROTO = 5


g_cached_hello_str = None


def get_username():
    """Get a username for use in the Query request to CDDB database"""
    try:
        (user, host) = os.environ['EMAIL'].split('@')
    except KeyError:
        try:
            user = os.environ['USER']
        except KeyError:
            user = str(os.geteuid()) or 'user'
    return user


def get_hostname():
    """Get a hostname for use in the Query request to CDDB database"""
    try:
        (user, host) = os.environ['EMAIL'].split('@')
    except KeyError:
        host = socket.gethostname() or 'host'
    return host


def get_hello_str(client_name = CLIENT_NAME, client_ver = CLIENT_VER):
    """Create the hello string for use in the Query request to CDDB database"""
    global g_cached_hello_str
    if g_cached_hello_str:
        return g_cached_hello_str

    hello = "hello=%s+%s+%s+%s" % (get_username(), get_hostname(), client_name, client_ver)
    g_cached_hello_str = hello
    return hello


def get_proto_str(proto_ver = CDDB_PROTO):
    """Create the proto string for use in the Query request to CDDB database"""
    return "proto=%i" % proto_ver


def get_query_str(disc_info):
    """disc_info is an object that should contain following methods:
       - disc_id, num_tracks, disc_len and tracks.
       tracks should be a list of track objects each containing following:
       - length"""
    parts = []
    parts.append('%s' % disc_info.disc_id)
    parts.append('%d' % disc_info.num_tracks)
    for track in disc_info.tracks:
        parts.append('%d' % track.length)
    parts.append('%d' % disc_info.disc_len)
    return "cmd=cddb+query+%s" % urllib.parse.quote_plus(" ".join(parts))


def get_read_str(disc_info):
    return "cmd=cddb+read+%s+%s" % (disc_info.category, disc_info.disc_id)


def perform_request(server_url, query_str, hello_str, proto_str): 
    url = "%s?%s&%s&%s" % (server_url, query_str, hello_str, proto_str)
    print(url)
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
        print(line)
    response.close()
    return lines


class CddbEntry(object):
    def __init__(self, category, title):
        self.category = category
        self.title = title


def query_cddb(disc_info, server_url = DEF_SERVER):
    lines = perform_request(server_url, get_query_str(disc_info), get_hello_str(), get_proto_str())
    if lines is None:
        return None
    # Four elements in header: status, category, disc-id, title
    header = lines.pop(0).split( ' ', 3)

    status_code = int(header[0])
    possible_discs = []

    if status_code == 200:		# OK
        assert(header[2] == disc_info.disc_id)
        possible_discs.append(CddbEntry(header[1], header[3]))

    elif status_code == 211 or status_code == 210: # multiple matches
        for line in lines:
            print(line)
            if line == '.':		# end of matches
                break
                # otherwise: split into 3 pieces, not 4 (thanks to bgp for the fix!)
            match = line.split(' ', 2)

            assert(match[1] == disc_info.disc_id)
            possible_discs.append(CddbEntry(match[0], match[2]))

    else:
        print("Error code %i received" % status_code)
        print("Header = '%s'" % header)
    return possible_discs


def read_cddb_metadata(disc_info, server_url = DEF_SERVER):
    lines = perform_request(server_url, get_read_str(disc_info), get_hello_str(), get_proto_str())
    if lines is None:
        return None

    header = lines.pop(0).split(' ', 3)
    status_code = int(header[0])
    entries = {}

    if status_code == 210 or status_code == 417: # success or access denied
        for line in lines:
            if line == '.':
                break;

            if line.startswith('#'):
                continue

            line = line.replace(r'\t', "\t").replace(r'\n', "\n").replace('\\', "\\").strip()
            try:
                name, value = line.split("=", 2)
            except ValueError:
                continue
            name = name.strip()
            value = value.strip()
            entries[name] = value
            print(name, "=", value)
        if status_code == 210:
            # success, parse the reply
            pass
        else:
            # access denied. :(
            print("Error code %i received" % status_code)
    else:
        print("Error code %i received" % status_code)
        print("Header = '%s'" % header)
        entries = None
    return entries



def get_track_info(discInfo, cddb_srv=DEF_SERVER):
    possible_entries = query_cddb(discInfo, cddb_srv)
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

        discInfo.title = entry.title
        discInfo.category = entry.category

        entries = read_cddb_metadata(discInfo, cddb_srv)

    except IndexError:
        discInfo.title = "unknown"
        entries = None
    
    print(discInfo.title)
#    for track in discInfo.tracks:
#        print(track.num, track.artist, "/", track.title)
    return entries

