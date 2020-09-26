import colabUtils
import time

#user code here
class ExampleApp(colabUtils.colabApp):
    def __init__(self):
        super().__init__()

    def start(self):
        while True:
            time.sleep(2)
            print("Running yooo")

    def stop(self):
        print('I stopped yo')

if __name__=='__main__':
    app = ExampleApp()
    app.run()