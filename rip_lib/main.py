import os
import sys
import subprocess
import pickle
import logging

logger = logging.getLogger(__name__)

import rip_lib.disc_info as disc_info
import rip_lib.freedb as cddb
import rip_lib.musicbrainz as musz

DEVICE = "/dev/sr0"

CUEFILE = "disc.cue"
WAVFILE = "disc.wav"
FLACFILE = "disc.flac"
COVERFILE = "cover.jpg"

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


def process_tags(info, idx, multiple):
    """Get the tags from Disc Info, idx is 1 based"""
    album_title = extractStr(info.title)
    if multiple:
        performer = info.tracks[idx-1].artist
        title = info.tracks[idx-1].title
    else:
        performer = info.artist
        title = info.title
    performer = extractStr(performer)
    title = extractStr(title)

    logger.info(album_title)
    logger.info(performer)
    logger.info(title)
    return album_title, performer, title


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
    wav_file = os.path.join(tmp_dir, WAVFILE)
    flac_file = os.path.join(tmp_dir, FLACFILE)
    if not os.path.exists(wav_file) or not os.path.exists(flac_file):
        args = [
            "cdparanoia",
            "-d", DEVICE,
            "\"-{0}\"".format(info.num_tracks),
            temp_file
        ]
        execute(args, temp_file, wav_file)
    else:
        logger.info("CD already read")


def write_cue_file(tmp_dir, info):
    cue_file = os.path.join(tmp_dir, CUEFILE)
    if not os.path.exists(cue_file):
        temp_file = "temp.cue"
        if os.path.exists(temp_file):
            os.unlink(temp_file)
        with open(temp_file, "w") as out_fp:
            info.write_cuefile(out_fp)
        os.rename(temp_file, cue_file)
    else:
        logger.info("Cue file already created")


def get_coverart(tmp_dir, info):
    cover_file = os.path.join(tmp_dir, COVERFILE)
    if not os.path.exists(cover_file):
        musz.get_track_info(discInfo, cover_file)
    else:
        logger.info("Cover Art already fetched")


def to_flac(tmp_dir, info):
    """Convert WAV to FLAC"""
    flac_file = os.path.join(tmp_dir, FLACFILE)
    if not os.path.exists(flac_file):
        wav_file = os.path.join(tmp_dir, WAVFILE)
        cue_file = os.path.join(tmp_dir, CUEFILE)
        temp_file = "temp.flac"
        args = [
            "flac",
            "--best",
            "--no-padding",
            "--cuesheet={}".format(cue_file),
            "-o", temp_file, wav_file]
        execute(args, temp_file, flac_file)
    else:
        logger.info("FLAC archive already created")


def flac2wav(tmp_dir, idx, multiple):
    """Return the WAV filename"""
    if multiple:
        wav = os.path.join(tmp_dir, "track{:02d}.wav".format(idx))
    else:
        wav = os.path.join(tmp_dir, "disc.wav")

    if not os.path.exists(wav):
        flac_file = os.path.join(tmp_dir, FLACFILE)
        temp_file = "temp.wav"
        args = [
            "flac",
            "-d", flac_file
        ]
        if multiple:
            args.append("--cue={}.1-{}.1".format(idx, idx+1))
        args += ["-o", temp_file]
        execute(args, temp_file, wav)
    return wav


def flac48k2wav(tmp_dir, idx, multiple):
    """Return the WAV filename"""
    if multiple:
        wav48k = os.path.join(tmp_dir, "track{:02d}.48k.wav".format(idx))
    else:
        wav48k = os.path.join(tmp_dir, "disc.48k.wav")
    if not os.path.exists(wav48k):
        temp_file = "temp.wav"
        wav = flac2wav(tmp_dir, idx, multiple)
        args = [
            "sox", "-S", "-G", wav, temp_file, "rate", "-v", "48k"
        ]
        execute(args, temp_file, wav48k)
    return wav48k


def ogg_filename(tmp_dir, i, multiple):
    """Return the OGG filename"""
    if multiple:
        return os.path.join(tmp_dir, "track{:02d}.ogg".format(i))
    return os.path.join(tmp_dir, "disc.ogg")


def to_ogg(tmp_dir, info, multiple, do48k):
    """Convert WAV to OGG"""
    if multiple:
        end_idx = info.num_tracks+1
    else:
        end_idx = 2
    for idx in range(1, end_idx):
        ogg = ogg_filename(tmp_dir, idx, multiple)
        if not os.path.exists(ogg):
            temp_file = "temp.ogg"
            if do48k:
                wav = flac48k2wav(tmp_dir, idx, multiple)
            else:
                wav = flac2wav(tmp_dir, idx)
            album_title, performer, track_title = process_tags(info, idx, multiple)
            args = [
                "oggenc", "-q", "7", "--utf8",
                "-a", performer,
                "-l", album_title,
            ]
            if multiple:
                args += [
                    "-t", track_title,
                    "-N", str(idx)
                ]
            args += [
                "-o", temp_file, wav
            ]
            execute(args, temp_file, ogg)


def mp3_filename(tmp_dir, i, multiple):
    """Return the MP3 filename"""
    if multiple:
        return os.path.join(tmp_dir, "track{:02d}.mp3".format(i))
    return os.path.join(tmp_dir, "disc.mp3")


def fix_ogg_tags(tmp_dir, info):
    """Fix the OGG tags"""
    for idx in range(100):
        multiple = (idx == 0)
        ogg = ogg_filename(tmp_dir, idx, multiple)
        if not os.path.exists(ogg):
            continue
        try:
            album_title, performer, track_title = process_tags(info, idx, multiple)
        except IndexError:
            print("%i out of range" % i)
            return False
        args = [
            "metaflac", "--remove-all-tags",
            "--set-tag=album={}".format(album_title),
            "--set-tag=performer={}".format(performer)
        ]
        if multiple:
            args += [
                "--set-tag=trackInfo={}".format(track_title),
                "--set-tag=trackNo={}".format(idx)
            ]
        args.append(ogg)
        print(args)
        subprocess.call(args)
    return True


def to_mp3(tmp_dir, info, multiple, do48k):
    """Convert WAV to MP3"""
    if multiple:
        end_idx = info.num_tracks+1
    else:
        end_idx = 2
    for idx in range(1, end_idx):
        mp3 = mp3_filename(tmp_dir, idx, multiple)
        if not os.path.exists(mp3):
            temp_file = "temp.mp3"
            if do48k:
                wav = flac48k2wav(tmp_dir, idx, multiple)
            else:
                wav = flac2wav(tmp_dir, idx)
            album_title, performer, track_title = process_tags(info, idx, multiple)
            args = ["lame", "-V", "5",
                "--ta", performer,
                "--tl", album_title
            ]
            if multiple:
                args += [
                    "--tt", track_title,
                    "--tn", str(idx),
                ]
            args += [wav, temp_file]
            execute(args, temp_file, mp3)


def fix_mp3_tags(tmp_dir, info, i):
    """Fix the MP3 tags"""
    for idx in range(100):
        multiple = (idx == 0)
        mp3 = mp3_filename(tmp_dir, idx, multiple)

        try:
            album_title, performer, track_title = process_tags(info, idx, multiple)
        except IndexError:
            print("%i out of range" % i)
            return False
        args = [
            "id3tag", 
            "-a", performer,
            "-A", album_title
        ]
        if multiple:
            args += [
                "-t", str(i),
            ]
        args.append(mp3)
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
    cddb.get_track_info(discInfo)
    save_pickle(tmp_dir, discInfo)

    read_cd(tmp_dir, discInfo)
    write_cue_file(tmp_dir, discInfo)
    get_coverart(tmp_dir, discInfo)
    to_flac(tmp_dir, discInfo)

    multiple = yes_or_no("Split into multiple tracks?")
    do48k = yes_or_no("Use 48K sample rate?")

    do_ogg = yes_or_no("Convert to OGG?")
    if do_ogg:
        to_ogg(tmp_dir, discInfo, multiple, do48k)

    do_mp3 = yes_or_no("Convert to MP3?")
    if do_mp3:
        to_mp3(tmp_dir, discInfo, multiple, do48k)

    if not do_ogg or not do_mp3:
        do_tags = yes_or_no("Update tags?")
    else:
        do_tags = False

    if do_tags:
        fix_ogg_tags(tmp_dir, discInfo)
        fix_mp3_tags(tmp_dir, discInfo)

#   os.remove(wav)

    rename_tmp_dir(tmp_dir, discInfo)
