from setuptools import setup, find_packages

setup(
    name = "cola",
    version = "0.1",
    packages=find_packages(),
    url = "https://github.com/dvlp-jrs/shellhack2020",
    author = "code200",
    install_requires = ["paramiko", "PyInquirer", "pyyaml", "pyngrok"],
    entry_points = {
        'console_scripts': ['cola=colabUtils.interface:main'],
    }
)