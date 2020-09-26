from __future__ import print_function, unicode_literals
from PyInquirer import prompt, print_json
import yaml

config_file = '../colab.yaml'

def get_ngrok_id():
    with open(config_file) as f:
        try:
            data = yaml.load(f, Loader=yaml.FullLoader)
        except Exception as e:
            print(f"[!] Error: {e}")
            exit()
    ques1 = [
        {
            'type' : 'input',
            'name' : 'ques1',
            'message' : '[+] Initial Setup: \n Please create ngrok account at https://ngrok.com and paste it here: '
        }
    ]
    ques2 = [
        {
            'type': "list",
            'name' : 'ques2',
            'message' : 'Select a option to continue',
            'choices': [
            'Continue with previos setup',
            'Reset ngrok id'
            ]
        }
    ]
    if data['ngrok_auth'] == 'None':
        ans = prompt(ques1)
        if len(ans['ques1']) >= 10:
            data['ngrok_auth'] = ans['ques1']
            with open(config_file, 'w') as f:
                f.write( yaml.dump(data, default_flow_style=False))
            deploy(data["ngrok_auth"])
        else:
            print("[!] Invalid Input")
    else:
        ans = prompt(ques2)
        if ans['ques2'] == "Continue with previos setup":
            deploy(data["ngrok_auth"])
        else:
            data['ngrok_auth'] = 'None'
            with open(config_file, 'w') as f:
                f.write( yaml.dump(data, default_flow_style=False))
            get_ngrok_id()

def deploy(ngrok_auth):
    print(f"""Please follow the following process to connect to colab:
        1: open https://colab.research.google.com/#create=true  (Login if not)
        2: copy the below code to the row and run

        from google.colab import drive
        drive.mount('/content/drive')
        from colabConnect import colabConnect
        colabConnect.setup(ngrok_region="us",ngrok_key={ngrok_auth})

        3: After it complete execution: You should get an url at the end
        """)
    config_url = input("Enter the url from colab: ")
    print(input("press enter to start deploy of code to server"))
    deploy_server()

def deploy_server():
    pass

get_ngrok_id()