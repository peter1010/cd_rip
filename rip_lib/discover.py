import os
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

def recursive_search(root):
    possible = 0
    directories = []
    for entry in os.listdir(root):
        if entry in ["pickle.info", "disc.flac", "disc.cue"]:
            possible += 1
        else:
            path = os.path.join(root, entry)
            if os.path.isdir(path):
                directories += recursive_search(path)
    if possible > 2:
        directories += [root]
    elif possible > 0:
        logger.error("Bad folder %s", root)
    return directories


def find_directories(root):
    directories = recursive_search(root)
    return directories
