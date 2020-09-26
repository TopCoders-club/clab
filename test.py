# from colabConnect import colabConnect

# colabConnect.setup(ngrok_region="us",ngrok_key="1i2aqgu5vbEXfHagdy5ub8XO2v3_5PaZrPCdWR6naYLqwKoMp")



import paramiko

ssh = paramiko.SSHClient() 
ssh.load_host_keys(os.path.expanduser(os.path.join("~", ".ssh", "known_hosts")))
ssh.connect("213.108.7.113", username="jrs", password="fuckyouju")
sftp = ssh.open_sftp()
sftp.put("./colab.yaml", "/home/jrs/colab.yaml")
sftp.close()
ssh.close()

# import scp

# client = scp.Client(host="213.108.7.113", user="jrs", password="fuckyouju")
# client.transfer('colab.yaml', '/home/jrs/colab.yaml')
