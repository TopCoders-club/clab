from __future__ import print_function, unicode_literals
from PyInquirer import prompt, print_json
import yaml
import webbrowser
import subprocess
import paramiko
from fabric import Connection
from invoke import Responder
import os
import string
import random
import sys
import hashlib
import coloredlogs, logging
import argparse
import select

logger = logging.getLogger(__name__)
coloredlogs.install(fmt="%(levelname)s %(message)s",level='DEBUG', logger=logger)

class ColabSFTPClient(paramiko.SFTPClient):
    def put_dir(self, source, target):
        ''' Uploads the contents of the source directory to the target path. The
            target directory needs to exists. All subdirectories in source are 
            created under target.
        '''
        for item in os.listdir(source):
            if os.path.isfile(os.path.join(source, item)):
                self.put(os.path.join(source, item), '%s/%s' % (target, item))
            else:
                self.mkdir('%s/%s' % (target, item), ignore_existing=True)
                self.put_dir(os.path.join(source, item), '%s/%s' % (target, item))

    def mkdir(self, path, mode=511, ignore_existing=False):
        ''' Augments mkdir by adding an option to not fail if the folder exists  '''
        try:
            super(ColabSFTPClient, self).mkdir(path, mode)
        except IOError:
            if ignore_existing:
                pass
            else:
                raise

config_file = 'colab.yaml'

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
        else:
            print("[!] Invalid Input")
    else:
        ans = prompt(ques2)
        if ans['ques2'] == "Continue with previous setup":
            return
        else:
            data['ngrok_auth'] = 'None'
            with open(config_file, 'w') as f:
                f.write( yaml.dump(data, default_flow_style=False))
            get_ngrok_id()

def deploy():
    with open(config_file) as f:
        try:
            data = yaml.load(f, Loader=yaml.FullLoader)
        except Exception as e:
            get_ngrok_id()
            logger.error(f"[!] Error: {e}")
            exit()
    ngrok_auth = data['ngrok_auth']
    secret_key = data['secret_key']
    logger.info(f"""Please follow the following process to connect to colab:
1: open https://colab.research.google.com/#create=true (if it does not open automatically)
2: Change the runtime type to gpu or tpu (optional)
3: copy the below code to the row and run

!pip install git+https://github.com/dvlp-jrs/shellhacks2020.git
import colabConnect
colabConnect.setup(ngrok_region="us",ngrok_key="{ngrok_auth}",secret_key="{secret_key}",vncserver={data['vncserver']})
4: After it complete execution: You should get an url at the end""")
    #webbrowser.open('https://colab.research.google.com/#create=true', new=2)
    deploy_server(hashlib.sha1(secret_key.encode('utf-8')).hexdigest()[:10], data['entry_file'])


def deploy_server(passwd, entry_file):
    # push code to colab and run the colab start and stop
    url = input("Enter the url generated in colab: ")
    hostname, port = url.split(':')
    port = int(port)
    print("Deploying...")
    passwd = hashlib.sha1(passwd.encode('utf-8')).hexdigest()[:10]
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(hostname, port=port, username='colab', password=passwd)
    sftp = ColabSFTPClient.from_transport(ssh.get_transport())
    sftp.mkdir('/home/colab/app', ignore_existing=True)
    sftp.put_dir(os.getcwd(), '/home/colab/app')
    sftp.close()
    ssh.close()
    print("Running...")
    with Connection(
        host=hostname,
        port=port,
        user='colab',
        connect_kwargs={
            'password': passwd
        }
    ) as c:
        sudopass = Responder(
            pattern=r'\[sudo\] password for colab:',
            response=f'{passwd}\n',
        )
        c.run('cd app')
        c.run('sudo pip3 install -r requirements.txt', pty=True, watchers=[sudopass])
        c.run(f"sudo python3 {entry_file}", pty=True, watchers=[sudopass])
    """
    stdin, stdout, stderr = ssh.exec_command()
    # live output here
    channel = stdout.channel
    stdin.close()                 
    channel.shutdown_write()     
    while not channel.closed:
        readq, _, _ = select.select([channel], [], [])
        for c in readq:
            if c.recv_ready(): 
                sys.stdout.write(channel.recv(len(c.in_buffer)).decode('utf-8'))       # write to fdout
            if c.recv_stderr_ready():   
                sys.stdout.write(channel.recv(len(c.in_buffer)).decode('utf-8'))       # write stderr to fdout
        if channel.exit_status_ready() and not channel.recv_stderr_ready() and not channel.recv_ready(): 
            channel.shutdown_read() 
            channel.close()
            break 
    stdout.close()
    stderr.close()
    return channel.recv_exit_status()"""

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

def main():
    parser = argparse.ArgumentParser(description='Options')
    parser.add_argument('type',help='Options \n init : Initial ngrok and secret key \n deploy : Deploy your code to colab')
    args = parser.parse_args()
    if args.type == "init":
        get_ngrok_id()
    elif args.type == "deploy":
        deploy()
    else:
        logger.error("Please Enter a valid command: for help use -h")

if __name__=='__main__':
    main()
