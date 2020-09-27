from __future__ import print_function, unicode_literals
from PyInquirer import prompt, print_json
import yaml
import webbrowser
import subprocess
import paramiko
from fabric import Connection
from invoke import Responder
import os, os.path
import string
import random
import sys
import hashlib
import argparse
import select
from halo import Halo

class bcolors:
    HEADER = "\033[95m"
    OKBLUE = "\033[94m"
    OKGREEN = "\033[92m"
    WARNING = "\033[93m"
    FAIL = "\033[91m"
    ENDC = "\033[0m"
    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"

class ColabSFTPClient(paramiko.SFTPClient):
    def put_dir(self, source, target):
        for item in os.listdir(source):
            if os.path.isfile(os.path.join(source, item)):
                self.put(os.path.join(source, item), "%s/%s" % (target, item))
            else:
                self.mkdir("%s/%s" % (target, item), ignore_existing=True)
                self.put_dir(os.path.join(source, item), "%s/%s" % (target, item))

    def mkdir(self, path, mode=511, ignore_existing=False):
        try:
            super(ColabSFTPClient, self).mkdir(path, mode)
        except IOError:
            if ignore_existing:
                pass
            else:
                raise


config_file = "colab.yaml"


def id_generator(size=6, chars=string.ascii_uppercase + string.digits):
    return "".join(random.choice(chars) for _ in range(size))

def get_ngrok_id():
    spinner = Halo(text="Loading", spinner="dots")
    spinner.start()
    if not os.path.isfile(config_file):
        with open(config_file, "w+") as f:
            try:
                data = {}
                data["debug"] = (True,)
                data["entry_file"] = "main.py"
                data["ngrok_auth"] = "None"
                data["running_time"] = 2
                data["secret_key"] = "None"
                data["vncserver"] = False
                data["backup"] = False
                f.write(yaml.dump(data, default_flow_style=False))
            except Exception as e:
                print(f"{bcolors.FAIL}Error: {e}{bcolors.ENDC}")
                exit()

    with open(config_file) as f:
        try:
            data = yaml.load(f, Loader=yaml.FullLoader)
        except Exception as e:
            print(f"{bcolors.FAIL}Error: {e} {bcolors.ENDC}")
            exit()
    ques1 = [
        {
            "type": "input",
            "name": "ques1",
            "message": "Initial Setup: \n Please create ngrok account at https://ngrok.com and paste it here: ",
        }
    ]
    ques2 = [
        {
            "type": "list",
            "name": "ques2",
            "message": "Select a option to continue",
            "choices": ["Continue with previous setup", "Reset ngrok id"],
        }
    ]
    ques3 = [
        {
            "type": "list",
            "name": "ques3",
            "message": "Do you need VNC server? ",
            "choices": ["yes", "no"],
        }
    ]

    ques4 = [
        {
            "type": "list",
            "name": "ques4",
            "message": "Do you want automatic backups to Google Drive? ",
            "choices": ["yes", "no"],
        }
    ]

    spinner.succeed()
    if data["ngrok_auth"] == "None":
        ans = prompt(ques1)
        if len(ans["ques1"]) >= 10:
            data["ngrok_auth"] = ans["ques1"]
            data["secret_key"] = id_generator(10)
            ans = prompt(ques3)
            if ans["ques3"] == "yes":
                data["vncserver"] = True
            else:
                data["vncserver"] = False
            ans = prompt(ques4)
            if ans["ques4"] == "yes":
                data["backup"] = True
            else:
                data["backup"] = False
            with open(config_file, "w") as f:
                f.write(yaml.dump(data, default_flow_style=False))
                print(f"{bcolors.OKBLUE}Setup Complete{bcolors.ENDC}")
        else:
            print("[!] Invalid Input")
    else:
        ans = prompt(ques2)
        if ans["ques2"] == "Continue with previous setup":
            print(f"{bcolors.OKBLUE}Setup Complete{bcolors.ENDC}")
        else:
            data["ngrok_auth"] = "None"
            with open(config_file, "w") as f:
                f.write(yaml.dump(data, default_flow_style=False))
            get_ngrok_id()


def deploy():
    with open(config_file) as f:
        try:
            data = yaml.load(f, Loader=yaml.FullLoader)
        except Exception as e:
            get_ngrok_id()
            print(f"{bcolors.FAIL}Error: {e} {bcolors.ENDC}")
            exit()
    ngrok_auth = data["ngrok_auth"]
    secret_key = data["secret_key"]
    drive = """
from google.colab import drive
drive.mount('/content/drive')"""
    print(
        f"""{bcolors.OKBLUE}Please follow the following process to connect to colab:{bcolors.ENDC}
1: open https://colab.research.google.com/#create=true (if it does not open automatically)
2: Change the runtime type to gpu or tpu (optional)
3: copy the below code to the row and run
{bcolors.WARNING}
!pip install git+https://github.com/TopCoders-club/clab.git{drive if data['backup'] else ""}
import colabConnect
colabConnect.setup(ngrok_region="us",ngrok_key="{ngrok_auth}",secret_key="{secret_key}",vncserver={data['vncserver']})
{bcolors.ENDC}
4: After it complete execution: You should get an url at the end"""
    )
    webbrowser.open("https://colab.research.google.com/#create=true", new=2)
    deploy_server(
        hashlib.sha1(secret_key.encode("utf-8")).hexdigest()[:10], data["entry_file"]
    )


def deploy_server(passwd, entry_file):
    # push code to colab and run the colab start and stop
    print(passwd)
    try:
        url = input("Enter the url generated in colab: ")
        hostname, port = url.split(":")
        port = int(port)
    except Exception as e:
        print("Error: " + str(e))
        exit(1)
    try:
        spinner = Halo(text="Deploying", spinner="dots")
        spinner.start()
        transport = paramiko.Transport((hostname, port))
        transport.connect(None, "root", passwd)
        sftp = ColabSFTPClient.from_transport(transport)
        sftp.mkdir("/root/app", ignore_existing=True)
        sftp.put_dir(os.getcwd(), "/root/app")
        sftp.close()
        spinner.succeed("Deployed")
    except Exception as e:
        spinner.fail("Something went wrong when deploying.")
        print(str(e))
        exit(1)
    try:
        with Connection(
            host=hostname, port=port, user="root", connect_kwargs={"password": passwd}
        ) as c:
            sudopass = Responder(
                pattern=r"\[sudo\] password for colab:",
                response=f"{passwd}\n",
            )
            spinner = Halo(text="Installing requirments", spinner="dots")
            spinner.start()
            c.run(
                "cd app && sudo pip3 install --ignore-installed -r requirements.txt",
                pty=True,
                watchers=[sudopass],
                hide="out",
            )
            spinner.succeed("Installed requirements")
            spinner = Halo(text="Running", spinner="dots")
            spinner.start()
            spinner.succeed()
            c.run(f"cd app && sudo python3 {entry_file}", pty=True, watchers=[sudopass])
    except Exception as e:
        spinner.fail("Something went wrong when running.")
        print(str(e))
        exit(1)


def upload_server(localfile, remotepath, username, password, host):
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


def download_server(remotepath, localfile, username, password, host):
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


def main():
    parser = argparse.ArgumentParser(description="Commands")
    parser.add_argument(
        "type",
        help="init: Initiate ngrok and secret key\n deploy: Deploy your code to colab instance",
    )
    args = parser.parse_args()
    if args.type == "init":
        get_ngrok_id()
    elif args.type == "deploy":
        deploy()
    else:
        print(
            f"{bcolors.WARNING}Please Enter a valid command. For help, use -h{bcolors.ENDC}"
        )


if __name__ == "__main__":
    main()
