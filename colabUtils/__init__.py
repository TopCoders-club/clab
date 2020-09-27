import multiprocessing
import time
import yaml
import logging

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
        
        logging.debug(f'Finished execution.')
