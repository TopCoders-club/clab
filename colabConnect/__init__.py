import apt, apt.debfile
import pathlib, stat, shutil, urllib.request, subprocess, getpass, time, tempfile, os
import secrets, json, re
import IPython.utils.io
import ipywidgets
import pyngrok.ngrok, pyngrok.conf
import hashlib
from halo import Halo


class _NoteProgress(
    apt.progress.base.InstallProgress,
    apt.progress.base.AcquireProgress,
    apt.progress.base.OpProgress,
):
    def __init__(self):
        apt.progress.base.InstallProgress.__init__(self)
        self._label = ipywidgets.Label()
        display(self._label)
        self._float_progress = ipywidgets.FloatProgress(
            min=0.0, max=1.0, layout={"border": "1px solid #118800"}
        )
        display(self._float_progress)

    def close(self):
        self._float_progress.close()
        self._label.close()

    def fetch(self, item):
        self._label.value = "fetch: " + item.shortdesc

    def pulse(self, owner):
        self._float_progress.value = self.current_items / self.total_items
        return True

    def status_change(self, pkg, percent, status):
        self._label.value = "%s: %s" % (pkg, status)
        self._float_progress.value = percent / 100.0

    def update(self, percent=None):
        self._float_progress.value = self.percent / 100.0
        self._label.value = self.op + ": " + self.subop

    def done(self, item=None):
        pass


class _MyApt:
    def __init__(self):
        self._progress = _NoteProgress()
        self._cache = apt.Cache(self._progress)

    def close(self):
        self._cache.close()
        self._cache = None
        self._progress.close()
        self._progress = None

    def update_upgrade(self):
        self._cache.update()
        self._cache.open(None)

    def commit(self):
        self._cache.commit(self._progress, self._progress)
        self._cache.clear()

    def installPkg(self, *args):
        for name in args:
            pkg = self._cache[name]
            if pkg.is_installed:
                print(f"{name} is already installed")
            else:
                print(f"Install {name}")
                pkg.mark_install()

    def installDebPackage(self, name):
        apt.debfile.DebPackage(name, self._cache).install()

    def deleteInstalledPkg(self, *args):
        for pkg in self._cache:
            if pkg.is_installed:
                for name in args:
                    if pkg.name.startswith(name):
                        # print(f"Delete {pkg.name}")
                        pkg.mark_delete()


def _download(url, path):
    try:
        with urllib.request.urlopen(url) as response:
            with open(path, "wb") as outfile:
                shutil.copyfileobj(response, outfile)
    except:
        print("Failed to download ", url)
        raise


def _get_gpu_name():
    r = subprocess.run(
        ["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"],
        stdout=subprocess.PIPE,
        universal_newlines=True,
    )
    if r.returncode != 0:
        return None
    return r.stdout.strip()


def _check_gpu_available():
    gpu_name = _get_gpu_name()
    if gpu_name == None:
        print("This is not a runtime with GPU")
    elif gpu_name == "Tesla K80":
        print("Warning! GPU of your assigned virtual machine is Tesla K80.")
        print("You might get better GPU by reseting the runtime.")
    else:
        return True

    return IPython.utils.io.ask_yes_no("Do you want to continue? [y/n]")


def _set_public_key(user, public_key):
    if public_key != None:
        home_dir = pathlib.Path("/root" if user == "root" else "/home/" + user)
        ssh_dir = home_dir / ".ssh"
        ssh_dir.mkdir(mode=0o700, exist_ok=True)
        auth_keys_file = ssh_dir / "authorized_keys"
        auth_keys_file.write_text(public_key)
        auth_keys_file.chmod(0o600)
        if user != "root":
            shutil.chown(ssh_dir, user)
            shutil.chown(auth_keys_file, user)


def _setupSSHDImpl(public_key, tunnel, ngrok_token, ngrok_region, is_VNC, secret_key):
    my_apt = _MyApt()
    my_apt.deleteInstalledPkg(
        "nvidia-dkms", "nvidia-kernel-common", "nvidia-kernel-source"
    )
    my_apt.commit()
    my_apt.update_upgrade()
    my_apt.commit()

    subprocess.run(["unminimize"], input="y\n", check=True, universal_newlines=True)

    my_apt.installPkg("openssh-server")
    my_apt.commit()
    my_apt.close()

    for i in pathlib.Path("/etc/ssh").glob("ssh_host_*_key"):
        i.unlink()
    subprocess.run(["ssh-keygen", "-A"], check=True)

    with open("/etc/ssh/sshd_config", "a") as f:
        f.write("\n\n# Options added by remocolab\n")
        f.write("ClientAliveInterval 120\n")
        if public_key != None:
            f.write("PasswordAuthentication no\n")

    msg = ""
    msg += "ECDSA key fingerprint of host:\n"
    ret = subprocess.run(
        ["ssh-keygen", "-lvf", "/etc/ssh/ssh_host_ecdsa_key.pub"],
        stdout=subprocess.PIPE,
        check=True,
        universal_newlines=True,
    )
    msg += ret.stdout + "\n"

    root_password = hashlib.sha1(secret_key.encode("utf-8")).hexdigest()[:10]
    user_password = hashlib.sha1(root_password.encode("utf-8")).hexdigest()[:10]
    user_name = "colab"
    msg += "\n"
    msg += f"root password: {root_password}\n"
    msg += f"{user_name} password: {user_password}\n"
    msg += "\n"
    subprocess.run(["useradd", "-s", "/bin/bash", "-m", user_name])
    subprocess.run(["adduser", user_name, "sudo"], check=True)
    subprocess.run(["chpasswd"], input=f"root:{root_password}", universal_newlines=True)
    file_data = """PasswordAuthentication yes
PermitUserEnvironment yes
PermitRootLogin yes
Subsystem sftp /usr/lib/openssh/sftp-server"""
    f = open("/etc/ssh/sshd_config", "w")
    f.write(file_data)
    f.close()
    subprocess.run(
        ["chpasswd"], input=f"{user_name}:{user_password}", universal_newlines=True
    )
    subprocess.run(["service", "ssh", "restart"])
    _set_public_key(user_name, public_key)

    ssh_common_options = "-o UserKnownHostsFile=/dev/null -o VisualHostKey=yes"

    if tunnel == "ngrok":
        pyngrok_config = pyngrok.conf.PyngrokConfig(
            auth_token=ngrok_token, region=ngrok_region
        )
        url = pyngrok.ngrok.connect(port=22, proto="tcp", pyngrok_config=pyngrok_config)
        m = re.match("tcp://(.+):(\d+)", url)
        hostname = m.group(1)
        port = m.group(2)
        ssh_common_options += f" -p {port}"

    msg = f"Enter this url in the local cli: {hostname}:{port}"

    return msg


def _setupSSHDMain(
    public_key, tunnel, ngrok_region, check_gpu_available, is_VNC, ngrok_key, secret_key
):

    if check_gpu_available and not _check_gpu_available():
        return (False, "")
    print("---")
    avail_tunnels = {"ngrok", "argotunnel"}
    if tunnel not in avail_tunnels:
        raise RuntimeError("tunnel argument must be one of " + str(avail_tunnels))
    ngrok_token = None

    if tunnel == "ngrok":
        ngrok_token = ngrok_key

    return (
        True,
        _setupSSHDImpl(
            public_key, tunnel, ngrok_token, ngrok_region, is_VNC, secret_key
        ),
    )


def setupSSHD(
    ngrok_region=None, check_gpu_available=False, tunnel="ngrok", public_key=None
):
    s, msg = _setupSSHDMain(
        public_key, tunnel, ngrok_region, check_gpu_available, False
    )
    print(msg)


def _setup_nvidia_gl():
    ret = subprocess.run(
        ["nvidia-smi", "--query-gpu=driver_version", "--format=csv,noheader"],
        stdout=subprocess.PIPE,
        check=True,
        universal_newlines=True,
    )
    nvidia_version = ret.stdout.strip()
    nvidia_url = (
        "https://us.download.nvidia.com/tesla/{0}/NVIDIA-Linux-x86_64-{0}.run".format(
            nvidia_version
        )
    )
    _download(nvidia_url, "nvidia.run")
    pathlib.Path("nvidia.run").chmod(stat.S_IXUSR)
    subprocess.run(
        ["./nvidia.run", "--no-kernel-module", "--ui=none"],
        input="1\n",
        check=True,
        universal_newlines=True,
    )

    # https://virtualgl.org/Documentation/HeadlessNV
    subprocess.run(
        [
            "nvidia-xconfig",
            "-a",
            "--allow-empty-initial-configuration",
            "--virtual=1920x1200",
            "--busid",
            "PCI:0:4:0",
        ],
        check=True,
    )

    with open("/etc/X11/xorg.conf", "r") as f:
        conf = f.read()
        conf = re.sub(
            '(Section "Device".*?)(EndSection)',
            '\\1    MatchSeat      "seat-1"\n\\2',
            conf,
            1,
            re.DOTALL,
        )

    with open("/etc/X11/xorg.conf", "w") as f:
        f.write(conf)

    #!service lightdm stop
    subprocess.run(
        ["/opt/VirtualGL/bin/vglserver_config", "-config", "+s", "+f"], check=True
    )
    # user_name = "colab"
    #!usermod -a -G vglusers $user_name
    #!service lightdm start

    # Run Xorg server
    # VirtualGL and OpenGL application require Xorg running with nvidia driver to get Hardware 3D Acceleration.
    #
    # Without "-seat seat-1" option, Xorg try to open /dev/tty0 but it doesn't exists.
    # You can create /dev/tty0 with "mknod /dev/tty0 c 4 0" but you will get permision denied error.
    subprocess.Popen(
        [
            "Xorg",
            "-seat",
            "seat-1",
            "-allowMouseOpenFail",
            "-novtswitch",
            "-nolisten",
            "tcp",
        ]
    )


def _setupVNC(secret_key):
    libjpeg_ver = "2.0.5"
    virtualGL_ver = "2.6.4"
    turboVNC_ver = "2.2.5"

    libjpeg_url = "https://github.com/demotomohiro/turbovnc/releases/download/2.2.5/libjpeg-turbo-official_{0}_amd64.deb".format(
        libjpeg_ver
    )
    virtualGL_url = "https://github.com/demotomohiro/turbovnc/releases/download/2.2.5/virtualgl_{0}_amd64.deb".format(
        virtualGL_ver
    )
    turboVNC_url = "https://github.com/demotomohiro/turbovnc/releases/download/2.2.5/turbovnc_{0}_amd64.deb".format(
        turboVNC_ver
    )

    _download(libjpeg_url, "libjpeg-turbo.deb")
    _download(virtualGL_url, "virtualgl.deb")
    _download(turboVNC_url, "turbovnc.deb")
    my_apt = _MyApt()
    my_apt.installDebPackage("libjpeg-turbo.deb")
    my_apt.installDebPackage("virtualgl.deb")
    my_apt.installDebPackage("turbovnc.deb")

    my_apt.installPkg("xfce4", "xfce4-terminal")
    my_apt.commit()
    my_apt.close()

    vnc_sec_conf_p = pathlib.Path("/etc/turbovncserver-security.conf")
    vnc_sec_conf_p.write_text(
        """\
no-remote-connections
no-httpd
no-x11-tcp-connections
"""
    )

    gpu_name = _get_gpu_name()
    if gpu_name != None:
        _setup_nvidia_gl()

    vncrun_py = tempfile.gettempdir() / pathlib.Path("vncrun.py")

    vncrun_py.write_text(
        """\
import subprocess, secrets, pathlib, hashlib
vnc_passwd = hashlib.sha1(hashlib.sha1(hashlib.sha1(secret_key.encode('utf-8')).hexdigest().encode('utf-8')).hexdigest().encode('utf-8')).hexdigest()
vnc_viewonly_passwd = hashlib.sha1(hashlib.sha1(hashlib.sha1(hashlib.sha1(secret_key.encode('utf-8')).hexdigest().encode('utf-8')).hexdigest().encode('utf-8')).hexdigest().encode('utf-8')).hexdigest()
print("[!] VNC password: {}".format(vnc_passwd))
print("[!] VNC view only password: {}".format(vnc_viewonly_passwd))
vncpasswd_input = "[!] {0}\\n{1}".format(vnc_passwd, vnc_viewonly_passwd)
vnc_user_dir = pathlib.Path.home().joinpath(".vnc")
vnc_user_dir.mkdir(exist_ok=True)
vnc_user_passwd = vnc_user_dir.joinpath("passwd")
with vnc_user_passwd.open('wb') as f:
  subprocess.run(
    ["/opt/TurboVNC/bin/vncpasswd", "-f"],
    stdout=f,
    input=vncpasswd_input,
    universal_newlines=True)
vnc_user_passwd.chmod(0o600)
subprocess.run(
  ["/opt/TurboVNC/bin/vncserver"],
  cwd = pathlib.Path.home()
)
#Disable screensaver because no one would want it.
(pathlib.Path.home() / ".xscreensaver").write_text("mode: off\\n")
"""
    )
    r = subprocess.run(
        ["su", "-c", "python3 " + str(vncrun_py), "colab"],
        check=True,
        stdout=subprocess.PIPE,
        universal_newlines=True,
    )
    return r.stdout


def setup(
    ngrok_region=None,
    check_gpu_available=True,
    tunnel="ngrok",
    public_key=None,
    ngrok_key=None,
    secret_key=None,
    vncserver=False,
):
    print("[!] Setup process started")
    stat, msg = _setupSSHDMain(
        public_key,
        tunnel,
        ngrok_region,
        check_gpu_available,
        True,
        ngrok_key,
        secret_key,
    )
    if stat:
        if vncserver:
            msg += _setupVNC(secret_key)
    print(msg)
