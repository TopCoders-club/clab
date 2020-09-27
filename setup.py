from setuptools import setup, find_packages

setup(
    name = "clab",
    version = "0.1",
    packages=find_packages(),
    url = "https://github.com/dvlp-jrs/shellhacks2020",
    author = "topcoders-club",
    install_requires = ["fabric", "PyInquirer", "pyyaml", "pyngrok", "halo"],
    entry_points = {
        'console_scripts': ['clab=colabUtils.interface:main'],
    }
)
