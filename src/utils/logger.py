import logging
from datetime import datetime
from os.path import exists
import os


def init_dirs():
    if not os.path.exists('./data'):
        os.mkdir('./data')
    if not os.path.exists('./data/sbotify.log'):
        with open('./data/sbotify.log', 'w') as f:
            f.close()
    if not os.path.exists('./data/server.log'):
        with open('./data/server.log', 'w') as f:
            f.close()


class Log:
    def __init__(self, platform: str, log_active: bool = True, print_to_console: bool = True, file='./data/sbotify.log'):
        if not exists(file):
            with open(file, 'w') as log_file:
                log_file.close()

        logging.basicConfig(filename=file, filemode='w',
                            format='%(asctime)s - %(message)s', datefmt='%d-%b-%y %H:%M:%S', level=20)
        self.platform = platform
        self.log_active = log_active
        self.print_to_console = print_to_console

    def req(self, user, request, command):
        if self.log_active:
            logging.info(
                f'{self.platform} - Command: {command}, User: {user}, Request: {request}')
        if self.print_to_console:
            print(f'{datetime.now().replace(microsecond=0)} - {self.platform} - Command: {command}, User: {user}, '
                  f'Request: {request}')

    def error(self, error):
        if self.log_active:
            logging.error(f'{self.platform} Error - {error}')
        if self.print_to_console:
            print(
                f'{datetime.now().replace(microsecond=0)} - {self.platform} Error -  {error}')

    def resp(self, resp):
        if self.log_active:
            logging.info(f'{self.platform} - Bot Response: {resp}')
        if self.print_to_console:
            print(
                f'{datetime.now().replace(microsecond=0)} - {self.platform} - Bot Response: {resp}')

    def info(self, info):
        if self.log_active:
            logging.info(f'{self.platform} - {info}')
        if self.print_to_console:
            print(
                f'{datetime.now().replace(microsecond=0)} - {self.platform} - {info}')

    def critical(self, msg):
        if self.log_active:
            logging.critical(msg)
        if self.print_to_console:
            print(msg)
