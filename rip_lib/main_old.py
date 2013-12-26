import rip_lib.disc_info as disc_info
import rip_lib.cddb as cddb

def main():
    discInfo = disc_info.DiscInfo()
    discInfo.read_disk()
    print(discInfo)
    metadata = cddb.get_track_info(discInfo)
    if metadata:
        discInfo.add_cddb_metadata(metadata)
    discInfo.print_details()
