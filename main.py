import colabUtils
import time

#user code here
class ExampleApp(colabUtils.colabApp):
    def __init__(self):
        pass

    def start(self):
        while True:
            time.sleep(2)
            print("Running yooo")

    def stop(self):
        pass

app = ExampleApp()
app.run()