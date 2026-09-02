# _*_ coding:utf-8 _*_
__author__ = 'dino.j'

import subprocess

def requirements():
    with open("requirements.txt", "w") as f:
        subprocess.run(["pip", "freeze"], stdout=f)

if __name__ == "__main__":
    requirements()