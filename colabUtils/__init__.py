import multiprocessing
import time
import yaml

# colab project template
class colabApp:
    def __init__(self, config_file='colab.yaml'):
        child_process = None
        should_run = True

        config = yaml.full_load(open(config_file, 'r'))
        raise NotImplementedError

    def start(self):
        raise NotImplementedError

    def stop(self):
        raise NotImplementedError

    def run(self):
        child_process = multiprocessing.Process(target=self.start())
        child_process.start()

        while True:
            if not self.should_run:
                child_process.terminate()
                while child_process.is_alive():
                    time.sleep(1)
                self.stop()
                break
        
            # Timer code goes here
            # NOTE: set variable should_run to False to terminate process.

        