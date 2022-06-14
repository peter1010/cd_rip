cd_rip
======

A Python scripts for ripping CDs to mp3 / oggs.

Installation
------------
  * pip install .

Usage
-----

Put CD into drive

type './cd_rip.sh' at the command line

It will:

  * read the CD
  * download the track info from musicbrainz
  * download the coverart
  * Create a CUE sheet
  * Read CD audio and convert to a single FLAC file
  * Ask User what next..
  * Next is convert to mp3 or ogg per track

Problems
--------
When the program runs it generates a file 'log.txt' in the current
working directory. Use that to diagnosis what went wrong or sent to me
