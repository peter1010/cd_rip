import os
import sys
import subprocess
import pickle

import rip_lib.disc_info as disc_info
import rip_lib.cddb as cddb

DEVICE="/dev/sr0"

def yesOrNo():
    while 1:
        answer = input("?")  
        answer = answer.lower()
        if answer.startswith('y'):
            return True
        elif answer.startswith('n'):
            return False
        else :
            print( "Please type 'y' or 'n'")


def extractStr(line):
    if len(line) == 0:
        return "-"
    return line


def replaceChars(line, chars = "\\\'\" (){}[]<>"):
    line = line.strip()
    for char in chars :
        idx = 0
        while idx >= 0 :
            idx = line.find(char, idx)
            if idx >= 0 :
                line = line[:idx] + "_" + line[idx+1:]
                idx = idx+1
    while 1 :
        idx = line.find("__")
        if idx >= 0 :
            line = line[:idx] + line[idx+1:]
        else :
            break

    return line.strip()


def shrink(line, max = 30) :
    if len(line) <= max :
        return line

    while len(line) > max :
        if line.lower().startswith('the ') :
            line = line[4:]
        elif line.lower().endswith(' the'):
            line = line[:-4]
        else :
            idx = line.lower().find(' the ')
            if idx >= 0 :
                line = line[:idx] + " " + line[idx+5:]
            else :
                break

    return line[:30]

#----------------------------------------------------
def removeChars(line, chars = "!?;,."):
    line = line.strip()
    for char in chars :
        idx = 0
        while idx >= 0 :
            idx = line.find(char, idx)
            if idx >= 0 :
                line = line[:idx] + line[idx+1:]
                idx = idx+1
    return line.strip()

#----------------------
def escapeChars(line, chars = "#`\\\'\" ()&|[]{}<>;") :
    line = line.strip()
    for char in chars :
        idx = 0
        while idx >= 0 :
            idx = line.find(char, idx)
            if idx >= 0 :
                line = line[:idx] + "\\" + line[idx:]
                idx = idx+2
    return line.strip()


def processTags(discInfo, idx):
    albumTitle = extractStr(discInfo.title)
    performer = extractStr(discInfo.tracks[idx-1].artist)
    trackTitle = extractStr(discInfo.tracks[idx-1].title)
    return albumTitle, performer, trackTitle


def load_pickle():
    pkl_fd = open(os.path.join("tmp-rip","pickle.info"), "rb")
    discInfo = pickle.load(pkl_fd)
    pkl_fd.close()
    return discInfo


def save_pickle(discInfo):
    discInfo.print_details()
    pkl_fd = open(os.path.join("tmp-rip","pickle.info"), "wb")
    discInfo = pickle.dump(discInfo, pkl_fd)
    pkl_fd.close()


def main():
    try:
        os.mkdir("tmp-rip")
    except FileExistsError:
        pass

    discInfo = disc_info.DiscInfo()
    if not discInfo.read_disk(DEVICE):
        pkl_fd = open(os.path.join("tmp-rip","pickle.info"), "rb")
        discInfo = pickle.load(pkl_fd)
        pkl_fd.close()
    print(discInfo)
    metadata = cddb.get_track_info(discInfo)
    if metadata:
        discInfo.add_cddb_metadata(metadata)
    save_pickle(discInfo)


    files = os.listdir("tmp-rip")
    entries = [ x for x in files if x.endswith(".wav")]
    if len(entries) < discInfo.num_tracks:

# -x = maximum quality
# -B = bulk

        args = ["cdparanoia", "-d", DEVICE, "-B"]
        curdir = os.getcwd()
        try:
            os.chdir("tmp-rip")
            info = subprocess.check_output(args)
        except FileNotFoundError:
            print("Check %s is installed\n" % args[0])
            sys.exit(-1)
        finally:
            os.chdir(curdir)
 
    print( "Convert to OGG?")
    doOgg = yesOrNo()  

    print( "Convert to MP3?")
    doMp3 = yesOrNo()  

    if not doOgg or not doMp3 :
        print( "Update tags?")
        doTags = yesOrNo()  


    for i in range(1,100) :
        wav = os.path.join("tmp-rip", "track%02d.cdda.wav" % i)
        mp3 = os.path.join("tmp-rip", "track%02d.mp3" % i)
        ogg = os.path.join("tmp-rip", "track%02d.ogg" % i)

        albumTitle, performer, trackTitle = processTags(discInfo, i)
        print( albumTitle)
        print( performer)
        print( trackTitle)

        if doOgg :
            args = ["oggenc", "-q", "7", "--utf8", 
                    "-a", performer, 
                    "-t", trackTitle,
                    "-l", albumTitle,
                    "-N", str(i),
                    "-o", ogg, wav]

            print(args)
            subprocess.call(args)

        elif doTags :
            args = ["metaflac", "--remove-all-tags",
                    "--set-tag=album=%s" % albumTitle,
                    "--set-tag=performer=%s" % performer,
                    "--set-tag=trackInfo=%s" % trackTitle,
                    "--set-tag=trackNo=%i" % i, ogg]
            print(args)
            subprocess.call(args)	
        
        if doMp3 :
            args = ["lame", "-V", "5", 
                    "--tt", trackTitle,
                    "--ta", performer,
                    "--tl", albumTitle,
                    "--tn", str(i), 
                    wav, mp3]
            print(args)
            subprocess.call(args)	
        elif doTags :
            cmd = "id3tag -s%s -a%s -A%s -t%d %s" \
                 % (trackTitle, performer, albumTitle, i, mp3)
            print( cmd)
            os.system(cmd)	

#   os.remove(wav)

    try :
        os.remove("audio.cddb")
        os.remove("audio.cdindex")
    except OSError :
        pass
    
    print( "Rename tmp-rip?")
    dirName = replaceChars(removeChars(extractStr(discInfo.title)))
    if yesOrNo() :
        os.rename("tmp-rip", dirName)	

