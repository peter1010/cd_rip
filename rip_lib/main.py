import os
import sys
import subprocess
import pickle

import rip_lib.disc_info as disc_info
import rip_lib.freedb as cddb

DEVICE = "/dev/sr0"


def yes_or_no(question=None):
    """Get a Yes or No answer from the user"""
    if question:
        print(question)
    while 1:
        answer = input("?")
        answer = answer.lower()
        if answer.startswith('y'):
            return True
        elif answer.startswith('n'):
            return False
        else:
            print("Please type 'y' or 'n'")


def extractStr(line):
    if len(line) == 0:
        return "-"
    return line


def replace_chars(line, chars="\\\'\" (){}[]<>"):
    """Replace some characters in string"""
    line = line.strip()
    for char in chars:
        idx = 0
        while idx >= 0:
            idx = line.find(char, idx)
            if idx >= 0:
                line = line[:idx] + "_" + line[idx+1:]
                idx = idx+1
    while 1:
        idx = line.find("__")
        if idx >= 0:
            line = line[:idx] + line[idx+1:]
        else:
            break

    return line.strip()


def shrink(line, max_len=30):
    """Shrink line to max_len"""
    if len(line) <= max_len:
        return line

    while len(line) > max_len:
        if line.lower().startswith('the '):
            line = line[4:]
        elif line.lower().endswith(' the'):
            line = line[:-4]
        else:
            idx = line.lower().find(' the ')
            if idx >= 0:
                line = line[:idx] + " " + line[idx+5:]
            else:
                break

    return line[:30]


def remove_chars(line, chars="!?;,."):
    line = line.strip()
    for char in chars:
        idx = 0
        while idx >= 0:
            idx = line.find(char, idx)
            if idx >= 0:
                line = line[:idx] + line[idx+1:]
                idx = idx+1
    return line.strip()


def process_tags(info, idx):
    """Get the tags from Disc Info, idx is 1 based"""
    album_title = extractStr(info.title)
    performer = extractStr(info.tracks[idx-1].artist)
    track_title = extractStr(info.tracks[idx-1].title)

    print(album_title)
    print(performer)
    print(track_title)
    return album_title, performer, track_title


def load_pickle(tmp_dir):
    """Load the Disk information from a pickle file"""
    try:
        with open(os.path.join(tmp_dir, "pickle.info"), "rb") as pkl_fd:
            info = pickle.load(pkl_fd)
    except FileNotFoundError:
        info = None
    return info


def save_pickle(tmp_dir, info):
    """Save the Disk information to a pickle file"""
    info.print_details()
    pkl_fd = open(os.path.join(tmp_dir, "pickle.info"), "wb")
    info = pickle.dump(info, pkl_fd)
    pkl_fd.close()


def make_tmp_dir(working_dir):
    """Make the tmp directory"""
    tmp_dir = os.path.join(working_dir, "tmp_rip")
    try:
        os.mkdir(tmp_dir)
    except FileExistsError:
        pass
    return tmp_dir


def wav_filename(tmp_dir, i):
    """Return the WAV filename"""
    return os.path.join(tmp_dir, "track%02d.cdda.wav" % i)


def rm_file(temp_file):
    try:
        os.unlink(temp_file)
    except FileNotFoundError:
        pass


def execute(args, temp_file, out_file):
    rm_file(temp_file)
    try:
        print(args)
        subprocess.call(args)
        os.rename(temp_file, out_file)
    except FileNotFoundError:
        print("Check %s is installed\n" % args[0])
        sys.exit(-1)
    finally:
        rm_file(temp_file)


def read_cd(tmp_dir, info):
    """Read the CD"""
    temp_file = "temp.wav"
    for idx in range(1, info.num_tracks+1):
        wav = wav_filename(tmp_dir, idx)
        if not os.path.exists(wav):
            # -x = maximum quality
            # -B = bulk
            args = ["cdparanoia", "-d", DEVICE, "-w", str(idx), "temp.wav"]
            execute(args, temp_file, wav)


def flac_filename(tmp_dir, i):
    """Return the FLAC filename"""
    return os.path.join(tmp_dir, "track%02d.flac" % i)


def to_flac(tmp_dir, info):
    """Convert WAV to FLAC"""
    temp_file = "temp.flac"
    for idx in range(1, info.num_tracks+1):
        flac = flac_filename(tmp_dir, idx)
        if not os.path.exists(flac):
            wav = wav_filename(tmp_dir, idx)
            album_title, performer, track_title = process_tags(info, idx)
            args = ["flac", "-S", "-best", "--replay-gain", "--no-padding",
                "-T", "ALBUM={}".format(album_title),
                "-T", "PERFORMER={}".format(performer),
                "-T", "TRACK_INFO={}".format(track_title),
                "-T", "TRACK_NO={}".format(idx),
                "-o", temp_file, wav]
            execute(args, temp_file, flac)


def wav48k_filename(tmp_dir, i):
    """Return the WAV filename"""
    return os.path.join(tmp_dir, "track%02d.48k.wav" % i)


def to_wav48k(tmp_dir, info):
    temp_file = "temp.wav"
    for idx in range(1, info.num_tracks+1):
        wav48k = wav48k_filename(tmp_dir, idx)
        if not os.path.exists(wav48k):
            wav = wav_filename(tmp_dir, idx)
            if not os.path.exists(wav):
                flac = flac_filename(tmp_dir, idx)
                args = ["flac", "-d", flac, "-o", wav]
                execute(args, temp_file, wav)
            args = ["sox", "-S", "-G", wav, temp_file, "rate", "-v", "48k"]
            execute(args, temp_file, wav48k)


def ogg_filename(tmp_dir, i):
    """Return the OGG filename"""
    return os.path.join(tmp_dir, "track%02d.ogg" % i)


def to_ogg(tmp_dir, info):
    """Convert WAV to OGG"""
    temp_file = "temp.ogg"
    for idx in range(1, info.num_tracks+1):
        ogg = ogg_filename(tmp_dir, idx)
        if not os.path.exists(ogg):
            wav = wav48k_filename(tmp_dir, idx)
            if not os.path.exists(wav):
                wav = wav_filename(tmp_dir, idx)
            album_title, performer, track_title = process_tags(info, idx)
            args = ["oggenc", "-q", "7", "--utf8",
                "-a", performer,
                "-t", track_title,
                "-l", album_title,
                "-N", str(idx),
                "-o", temp_file, wav]
            execute(args, temp_file, ogg)


def mp3_filename(tmp_dir, i):
    """Return the MP3 filename"""
    return os.path.join(tmp_dir, "track%02d.mp3" % i)



def fix_ogg_tags(tmp_dir, info, i):
    """Fix the OGG tags"""
    try:
        album_title, performer, track_title = process_tags(info, i)
    except IndexError:
        print("%i out of range" % i)
        return False
    ogg = ogg_filename(tmp_dir, i)
    args = ["metaflac", "--remove-all-tags",
            "--set-tag=album=%s" % album_title,
            "--set-tag=performer=%s" % performer,
            "--set-tag=trackInfo=%s" % track_title,
            "--set-tag=trackNo=%i" % i, ogg]
    print(args)
    subprocess.call(args)
    return True


def to_mp3(tmp_dir, info):
    """Convert WAV to MP3"""
    temp_file = "temp.mp3"
    for idx in range(1, info.num_tracks+1):
        mp3 = mp3_filename(tmp_dir, idx)
        if not os.path.exists(mp3):
            wav = wav48k_filename(tmp_dir, idx)
            if not os.path.exists(wav):
                wav = wav_filename(tmp_dir, idx)
            album_title, performer, track_title = process_tags(info, idx)
            args = ["lame", "-V", "5",
                "--tt", track_title,
                "--ta", performer,
                "--tl", album_title,
                "--tn", str(idx),
                wav, temp_file]
            execute(args, temp_file, mp3)


def fix_mp3_tags(tmp_dir, info, i):
    """Fix the MP3 tags"""

    try:
        album_title, performer, track_title = process_tags(info, i)
    except IndexError:
        print("%i out of range" % i)
        return False
    mp3 = mp3_filename(tmp_dir, i)
    args = [
        "id3tag", "-s", track_title,
        "-a", performer,
        "-A", album_title,
        "-t", i,
        mp3
    ]
    print(args)
    subprocess.call(args)
    return True


def rename_tmp_dir(tmp_dir, info):
    """Rename the tmp directory"""
    dir_name = replace_chars(remove_chars(extractStr(info.title)))
    if yes_or_no("Rename tmp-rip?"):
        os.rename(tmp_dir, dir_name)


def main(working_dir):
    tmp_dir = make_tmp_dir(working_dir)

    discInfo = disc_info.DiscInfo()
    if not discInfo.read_disk(DEVICE):
        discInfo = load_pickle(tmp_dir)
    print(discInfo)
    if not discInfo:
        return
    metadata = cddb.get_track_info(discInfo)
    if metadata:
        discInfo.add_cddb_metadata(metadata)
    save_pickle(tmp_dir, discInfo)

    read_cd(tmp_dir, discInfo)

    if yes_or_no("Convert to FLAC?"):
        to_flac(tmp_dir, discInfo)

    if yes_or_no("Convert to 48K?"):
        to_wav48k(tmp_dir, discInfo)

    do_ogg = yes_or_no("Convert to OGG?")
    if do_ogg:
        to_ogg(tmp_dir, discInfo)

    do_mp3 = yes_or_no("Convert to MP3?")
    if do_mp3:
        to_mp3(tmp_dir, discInfo)

    if not do_ogg or not do_mp3:
        do_tags = yes_or_no("Update tags?")
    else:
        do_tags = False

    for idx in range(1, 100):
        if do_tags:
            if not fix_ogg_tags(tmp_dir, discInfo, idx):
                break

            if not fix_mp3_tags(tmp_dir, discInfo, idx):
                break

#   os.remove(wav)

    rename_tmp_dir(tmp_dir, discInfo)
