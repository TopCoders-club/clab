from __future__ import print_function, unicode_literals
from PyInquirer import prompt, print_json
import yaml
import webbrowser
import subprocess
import paramiko
import os
import string
import random
import sys

config_file = '../colab.yaml'

def id_generator(size=6, chars=string.ascii_uppercase + string.digits):
    return ''.join(random.choice(chars) for _ in range(size))

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
            data['secret_key'] = id_generator(10)
            with open(config_file, 'w') as f:
                f.write( yaml.dump(data, default_flow_style=False))
            deploy(data["ngrok_auth"],data['secret_key'])
        else:
            print("[!] Invalid Input")
    else:
        ans = prompt(ques2)
        if ans['ques2'] == "Continue with previos setup":
            deploy(data["ngrok_auth"],data['secret_key'])
        else:
            data['ngrok_auth'] = 'None'
            with open(config_file, 'w') as f:
                f.write( yaml.dump(data, default_flow_style=False))
            get_ngrok_id()

def deploy(ngrok_auth,secret_key):
    print(f"""Please follow the following process to connect to colab:
        1: open https://colab.research.google.com/#create=true (if it does not open automatically)
        2: Change the runtime type to gpu or tpu (optional)
        3: copy the below code to the row and run

        from google.colab import drive
        drive.mount('/content/drive')
        from colabConnect import colabConnect
        colabConnect.setup(ngrok_region="us",ngrok_key="{ngrok_auth}",secret_key="{secret_key}")

        4: After it complete execution: You should get an url at the end
        """)
    webbrowser.open('https://colab.research.google.com/#create=true', new=2)
    config_url = input("Enter the url from colab: ")
    print(input("press enter to start deploy of code to server"))
    deploy_server()


def deploy_server():
    #push code to colab and run the colab start and stop
    pass

def upload_server(localfile,remotepath,username,password,host):
    try:
        ssh = paramiko.SSHClient() 
        ssh.connect(host, username=username, password=password)
        ssh.load_host_keys(os.path.expanduser(os.path.join("~", ".ssh", "known_hosts")))
        sftp = ssh.open_sftp()
        sftp.put(localfile, remotepath)
        sftp.close()
        ssh.close()
        return True
    except:
        return False

def download_server(remotepath,localfile,username,password,host):
    try:
        ssh = paramiko.SSHClient() 
        ssh.connect(host, username=username, password=password)
        ssh.load_host_keys(os.path.expanduser(os.path.join("~", ".ssh", "known_hosts")))
        sftp = ssh.open_sftp()
        sftp.get(remotepath, localfile)
        sftp.close()
        ssh.close()
        return True
    except:
        return False

arg1 = sys.argv[1]

if arg1 == "init":
    get_ngrok_id()
elif arg2 == "deploy":
    deploy_server()
else:
    print("Enter Valid input")