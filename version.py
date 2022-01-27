import configparser
import sys
config = configparser.ConfigParser()
config.sections()
config.read('setup.cfg')
sys.stdout.write(config['metadata']['Version'])

