import os
import sys

from pysbml4j import Sbml4j
from pysbml4j import Configuration

import logging
from logging.config import fileConfig
import configparser

configFolder = "/config"
fileConfig('{}/config.ini'.format(configFolder))
logger = logging.getLogger()
logging.getLogger("chardet.charsetprober").disabled = True

def main(sysArgs):
    logger.debug("This is the default script.")
    logger.debug("Place your file named 'script.py'")
    logger.debug("in the folder that is mounted to the")
    logger.debug("'/code'-folder inside the container.")
    logger.debug("'Place your configuration file named 'config.ini'")
    logger.debug("in the filder that is mounted to the")
    logger.debug("'/config'-folder inside the container")



if __name__ == "__main__":

    main(sys.argv)
