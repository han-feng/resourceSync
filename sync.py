#!/usr/bin/python
import os
import time
import pandas as pd
import stat
import shutil
import pathlib
from urllib import parse
from concurrent.futures import ThreadPoolExecutor

syncBaseDir = "data/"
cwd = os.getcwd()


def getAbsPath(path):
    return os.path.abspath(os.path.join(cwd, path))


def deletefile(filePath):
    if os.path.exists(filePath):
        for fileList in os.walk(filePath):
            for name in fileList[2]:
                os.chmod(os.path.join(fileList[0], name), stat.S_IWRITE)
                os.remove(os.path.join(fileList[0], name))
        shutil.rmtree(filePath)


def path2url(path):
    sr = parse.SplitResult(scheme='file', netloc='',
                           path=path.replace("\\", "/"), query='', fragment='')
    sr = parse.urlunsplit(sr)
    return sr


def svncreate(name, path, url):
    if os.path.exists(path):
        return -1
    print(">>", name, "创建镜像库")
    if not os.path.exists(syncBaseDir):
        os.makedirs(syncBaseDir)
    pathUrl = path2url(path)
    status = os.system("svnadmin create " + syncBaseDir + name)
    if status == 0:
        pathlib.Path(path, "hooks", "pre-revprop-change.bat").touch()
        p = pathlib.Path(path, "hooks", "pre-revprop-change")
        p.write_text("#!/bin/sh\n\nexit 0\n")
        p.chmod(0o777)
        status = os.system("svnsync init " + pathUrl + " " + url)
        if status == 0:
            print("...", name, "创建成功")
            return 0
    deletefile(path)
    return 1


def svnsync(name, path, url):
    if svncreate(name, path, url) > 0:
        return 1
    print(">>", name, "开始同步")
    pathUrl = path2url(path)
    status = os.system("svnsync sync " + pathUrl)
    if status > 0:
        os.system("svn propdel svn:sync-lock --revprop -r0 " + pathUrl)
        time.sleep(1)
        status = os.system("svnsync sync " + pathUrl)
    else:
        print("...", name, "同步成功")
    return 0


dataset = pd.read_csv("svn.csv")
svnRepos = dataset.iloc[:, :2].values
executor = ThreadPoolExecutor(5)
for svnRepo in svnRepos:
    name = svnRepo[0].strip()
    if name.startswith("#"):
        continue
    path = getAbsPath(syncBaseDir + name)
    url = svnRepo[1].strip()
    executor.submit(svnsync, name, path, url)
