import os
import sys
import subprocess
import pickle
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

import rip_lib.disc_info as disc_info
import rip_lib.freedb as cddb
import rip_lib.musicbrainz as musz
import rip_lib.ogg as ogg

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


def replace_chars(line, chars="/\\\'\" (){}[]<>"):
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
    performer = info.tracks[idx-1].artist
    title = info.tracks[idx-1].title
    performer = extractStr(performer)
    title = extractStr(title)

    logger.info(album_title)
    logger.info(performer)
    logger.info(title)
    return album_title, performer, title


def load_pickle(tmp_dir):
    """Load the Disk information from a pickle file"""
    try:
        logger.debug("Loading pickle.info")
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


def get_wip_dir(working_dir):
    """Get or Make the tmp working directory"""
    if os.path.exists("pickle.info"):
        tmp_dir = "."
    else:
        tmp_dir = os.path.join(working_dir, "tmp_rip")
        try:
            os.mkdir(tmp_dir)
        except FileExistsError:
            pass
    logger.debug("working_dir='%s'", tmp_dir)
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
        return False
    finally:
        rm_file(temp_file)
    return True


def read_cd(tmp_dir, info):
    """Read the CD"""
    temp_file = "temp.wav"
    wav_file = os.path.join(tmp_dir, WAVFILE)
    flac_file = os.path.join(tmp_dir, FLACFILE)
    if not (os.path.exists(wav_file) or os.path.exists(flac_file)):
        args = [
            "cdparanoia",
            "-d", DEVICE,
            "\"-{0}\"".format(info.num_tracks),
            temp_file
        ]
        if not execute(args, temp_file, wav_file):
            args[3] = "\"-{}\"".format(info.num_tracks-1)
            if not execute(args, temp_file, wav_file):
                sys.exit(-1)
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
        musz.get_coverart(info, cover_file)
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
        if not execute(args, temp_file, flac_file):
            sys.exit(-1)
    else:
        logger.info("FLAC archive already created")


def flac2wav(tmp_dir, idx):
    """Return the WAV filename"""
    wav = os.path.join(tmp_dir, "track{:02d}.wav".format(idx))
    if not os.path.exists(wav):
        flac_file = os.path.join(tmp_dir, FLACFILE)
        temp_file = "temp.wav"
        args = [
            "flac",
            "-d", flac_file
        ]
        args.append("--cue={}.1-{}.1".format(idx, idx+1))
        args += ["-o", temp_file]
        if not execute(args, temp_file, wav):
            sys.exit(-1)
    return wav


def flac48k2wav(tmp_dir, idx):
    """Return the WAV filename"""
    wav48k = os.path.join(tmp_dir, "track{:02d}.48k.wav".format(idx))
    if not os.path.exists(wav48k):
        temp_file = "temp.wav"
        wav = flac2wav(tmp_dir, idx)
        args = [
            "sox", "-S", "-G", wav, temp_file, "rate", "-v", "48k"
        ]
        if not execute(args, temp_file, wav48k):
            sys.exit(-1)
    return wav48k


def ogg_filename(tmp_dir, i):
    """Return the OGG filename"""
    return os.path.join(tmp_dir, "track{:02d}.ogg".format(i))


def to_ogg(tmp_dir, info, do48k):
    """Convert WAV to OGG"""
    start_idx = 1
    end_idx = info.num_tracks+1
    for idx in range(start_idx, end_idx):
        ogg_file = ogg_filename(tmp_dir, idx)
        if not os.path.exists(ogg_file):
            temp_file = "temp.ogg"
            if do48k:
                wav = flac48k2wav(tmp_dir, idx)
            else:
                wav = flac2wav(tmp_dir, idx)
            album_title, performer, track_title = process_tags(
                info, idx
            )
            ogg.oggenc(wav, ogg_file, performer, album_title,
                track_title, idx
            )
            if idx <= 0:
                cover_file = os.path.join(tmp_dir, COVERFILE)
                ogg.add_coverart(ogg_file, cover_file)


def mp3_filename(tmp_dir, i):
    """Return the MP3 filename"""
    return os.path.join(tmp_dir, "track{:02d}.mp3".format(i))


def fix_ogg_tags(tmp_dir, info):
    """Fix the OGG tags"""
    for idx in range(100):
        ogg_file = ogg_filename(tmp_dir, idx)
        if not os.path.exists(ogg_file):
            continue
        try:
            album_title, performer, track_title = process_tags(info, idx)
        except IndexError:
            print("%i out of range" % i)
            return False
        args = [
            "metaflac", "--remove-all-tags",
            "--set-tag=album={}".format(album_title),
            "--set-tag=performer={}".format(performer),
            "--set-tag=trackInfo={}".format(track_title)
        ]
        args += [
                "--set-tag=trackNo={}".format(idx)
        ]
        args.append(ogg_file)
        print(args)
        subprocess.call(args)
    return True


def to_mp3(tmp_dir, info, do48k):
    """Convert WAV to MP3"""
    end_idx = info.num_tracks+1
    for idx in range(1, end_idx):
        mp3 = mp3_filename(tmp_dir, idx)
        if not os.path.exists(mp3):
            temp_file = "temp.mp3"
            if do48k:
                wav = flac48k2wav(tmp_dir, idx)
            else:
                wav = flac2wav(tmp_dir, idx)
            album_title, performer, track_title = process_tags(
                info, idx
            )
            args = ["lame", "-V", "5",
                "--ta", performer,
                "--tl", album_title,
                "--tt", track_title,
            ]
            args += [
                    "--tn", str(idx),
            ]
            args += [wav, temp_file]
            if not execute(args, temp_file, mp3):
                sys.exit(-1)


def fix_mp3_tags(tmp_dir, info, i):
    """Fix the MP3 tags"""
    for idx in range(100):
        mp3 = mp3_filename(tmp_dir, idx)

        try:
            album_title, performer, track_title = process_tags(info, idx)
        except IndexError:
            print("%i out of range" % i)
            return False
        args = [
            "id3tag", 
            "-a", performer,
            "-A", album_title,
            "-s", track_title
        ]
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


def main(args, working_dir):
    tmp_dir = get_wip_dir(working_dir)

    discInfo = disc_info.DiscInfo()
    if args.only_convert or not discInfo.read_disk(DEVICE):
        logger.info("Reading from pickle file (no disc detected)")
        discInfo = load_pickle(tmp_dir)
    if not discInfo:
        logger.error("No disc information available")
        return
    if not musz.get_track_info(discInfo):
        cddb.get_track_info(discInfo)
    save_pickle(tmp_dir, discInfo)

    if not args.only_convert:
        read_cd(tmp_dir, discInfo)
        write_cue_file(tmp_dir, discInfo)
        get_coverart(tmp_dir, discInfo)
        to_flac(tmp_dir, discInfo)

    do48k = yes_or_no("Use 48K sample rate?")

    do_ogg = yes_or_no("Convert to OGG?")
    if do_ogg:
        to_ogg(tmp_dir, discInfo, do48k)

    do_mp3 = yes_or_no("Convert to MP3?")
    if do_mp3:
        to_mp3(tmp_dir, discInfo, do48k)

    if not do_ogg or not do_mp3:
        do_tags = yes_or_no("Update tags?")
    else:
        do_tags = False

    if do_tags:
        fix_ogg_tags(tmp_dir, discInfo)
        fix_mp3_tags(tmp_dir, discInfo)

#   os.remove(wav)

    rename_tmp_dir(tmp_dir, discInfo)
