import subprocess
import base64
import struct
import os


VORBIS_COMMENT_EXE = "vorbiscomment"
IMAGE_IDENTIFY_EXE = "identify"
OGG_ENC_EXE = "oggenc"


def identify(filename):
    #tmp_rip/cover.jpg JPEG 1000x1000 1000x1000+0+0 8-bit sRGB 332KB 0.000u 0:00.000
    args = [
        IMAGE_IDENTIFY_EXE, filename,
    ]
    data = subprocess.check_output(args)
    tokens = data[len(filename):].split()
    mimetype = {
        b"JPEG": "image/jpeg"
    }[tokens[0]]
    width, height = tokens[1].split(b'x')
    width = int(width)
    height = int(height)
    assert tokens[3].endswith(b"-bit")
    bits = int(tokens[3][:-4])
    if tokens[4] == b"sRGB":
        bits *= 3
    return mimetype, width, height, bits


def create_metadata_block_picture(image_file):
    with open(image_file, "rb") as in_fp:
        image = in_fp.read()

    mimetype, width, height, bit_depth = identify(image_file)
    #metadata_block_picture format
    #See: https://xiph.org/flac/format.html#metadata_block_picture

    mimetype = mimetype.encode("ascii")
    description = "coverart".encode("utf-8")
    colour_count = 0 # Only applicable to gifs

    parts = []
    parts.append(struct.pack("II", 3, len(mimetype)))
    parts.append(mimetype)
    parts.append(struct.pack("I", len(description)))
    parts.append(description)
    parts.append(struct.pack("IIII", width , height, bit_depth, colour_count))
    parts.append(struct.pack("I", len(image)))
    parts.append(image)
    data = b"".join(parts)
    return base64.b64encode(data)


def rm_file(temp_file):
    if os.path.exists(temp_file):
        os.unlink(temp_file)
        

def add_coverart(ogg_file, image_file):
    temp = "temp.com"
    rm_file(temp)
    with open(temp, "w") as out_fp:
        out_fp.write("metadata_block_picture=")
        out_fp.write(create_metadata_block_picture(image_file).decode("utf-8"))
    try:
        args = [
            VORBIS_COMMENT_EXE,
            "-a",
            "--raw",
            "-c", temp,
            ogg_file
        ]
        subprocess.check_call(args)
    finally:
        rm_file(temp)


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


def oggenc(wav_file, ogg_file, performer, album_title, track_title, idx):
    """Encode a OGG file from the wav file, if idx <= 0 then this is the
    complete album"""
    temp_file = "temp.ogg"
    args = [
        OGG_ENC_EXE,
        "-q", "7", "--utf8",
        "-a", performer,
        "-l", album_title,
        "-t", track_title,
    ]
    if idx > 0:
        args += [
            "-N", str(idx)
        ]
    args += [
        "-o", temp_file, wav_file
    ]
    execute(args, temp_file, ogg_file)
 

if __name__ == "__main__":
    print(create_metadata_block_picture("tmp_rip/cover.jpg"))
