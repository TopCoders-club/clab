import multiprocessing
import time
import yaml
import logging
from distutils.dir_util import copy_tree
import random
import string

def get_random_string(length):
    return ''.join(random.choice(string.ascii_lowercase) for i in range(length))

# colab project template
class colabApp:
    def __init__(self, config_file='colab.yaml'):
        self.child_process = None
        self.should_run = True
        self.logger = logging.getLogger('colabApp')

        self.config = yaml.load(open(config_file, 'r'), Loader=yaml.FullLoader)
        if self.config['debug']:
            logging.basicConfig(level=logging.DEBUG)
        else:
            logging.basicConfig(level=logging.INFO)

    def start(self):
        raise NotImplementedError

    def stop(self):
        raise NotImplementedError

    def run(self):
        self.child_process = multiprocessing.Process(target=self.start)
        end_time = time.time() + int(self.config['running_time'])*60
        self.logger.debug(f'Set to terminate at {end_time}')
        self.child_process.start()
        self.logger.debug(f'Started')

        while True:
            if not self.should_run:
                self.logger.debug(f'Terminating')
                self.child_process.terminate()
                while self.child_process.is_alive():
                    time.sleep(1)
                self.logger.debug(f'Terminated. Running exit code')
                self.stop()
                break
        
            if time.time() >= end_time:
                self.should_run = False
                self.logger.debug(f'Endtime reached')
                continue
            else:
                # TODO: Ping server here
                self.logger.debug(f'Sleep for 60s')
                time.sleep(60)

        if self.config['backup']:
            new_folder = get_random_string(7)
            self.logger.debug(f'Finished execution. Backing up to drive in folder {new_folder}.')
            copy_tree('/root/app', f'/content/drive/My Drive/clab_backup/{new_folder}')
            self.logger.debug(f'Backed up. Terminating.')
        else:
            self.logger.debug(f'Finished execution. Terminating.')