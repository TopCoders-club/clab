from __future__ import print_function, unicode_literals
from PyInquirer import prompt, print_json
import yaml
import webbrowser
import subprocess
import paramiko
import os

class ColabSFTPClient(paramiko.SFTPClient):
    def put_dir(self, source, target):
        for item in os.listdir(source):
            if os.path.isfile(os.path.join(source, item)):
                self.put(os.path.join(source, item), '%s/%s' % (target, item))
            else:
                self.mkdir('%s/%s' % (target, item), ignore_existing=True)
                self.put_dir(os.path.join(source, item), '%s/%s' % (target, item))

    def mkdir(self, path, mode=511, ignore_existing=False):
        try:
            super(ColabSFTPClient, self).mkdir(path, mode)
        except IOError:
            if ignore_existing:
                pass
            else:
                raise

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
        1: open https://colab.research.google.com/#create=true (if it does not open automatically)
        2: Change the runtime type to gpu or tpu (optional)
        3: copy the below code to the row and run

        from google.colab import drive
        drive.mount('/content/drive')
        from colabConnect import colabConnect
        colabConnect.setup(ngrok_region="us",ngrok_key={ngrok_auth})

        4: After it complete execution: You should get an url at the end
        """)
    webbrowser.open('https://colab.research.google.com/#create=true', new=2)
    config_url = input("Enter the url from colab: ")
    print(input("press enter to start deploy of code to server"))
    deploy_server()


def deploy_server():
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

get_ngrok_id()