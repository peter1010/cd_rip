#!/bin/env python

import os

#---------------------
def extractStr(line) :
    idx = line.find('\'')
    if idx < 0 :
	raise RuntimeError
    str = line[idx+1:-2].strip()
    if len(str) == 0 :
	return "-"
    return str

#----------------------------------------------------
def replaceChars(line, chars = "\\\'\" (){}[]<>/"):
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


#---------------------------
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

    return line[:max]

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

#---------------------
def processTags(inf) :
    inf_in = file(inf,"r")

    for line in inf_in :
	if line.startswith("Albumtitle=") :
	    albumTitle = extractStr(line)
	if line.startswith("Performer=") :
	    performer = extractStr(line)
	if line.startswith("Tracktitle=") :
	    trackTitle = extractStr(line)
    inf_in.close()

    dirName = replaceChars(removeChars(albumTitle))
    albumTitle = escapeChars(shrink(removeChars(albumTitle),100))

    # For complied Albums, sometimes the artist is 
    # in the track title
    print "TrackTitle is '%s'" % trackTitle
    if performer.lower().find("various") >= 0 :
        if  trackTitle.find('-') >= 0:
            performer, trackTitle = trackTitle.split('-',1)
        elif  trackTitle.find('/') >= 0:
            performer, trackTitle = trackTitle.split('/',1)

    performer = escapeChars(shrink(removeChars(performer)))
    trackTitle = escapeChars(shrink(removeChars(trackTitle)))

    return dirName, albumTitle, performer, trackTitle


#-----------------------------
def getTrackNumbers(files) :
    numbers = []
    for fileName in files :
        if fileName.endswith(".inf") :
            idx1 = len(fileName)-4
            idx2 = fileName.find("_")
            if idx2 > 0 :
                numStr = fileName[idx2+1:idx1]
                numbers.append(numStr)
    numbers.sort()
    return numbers

