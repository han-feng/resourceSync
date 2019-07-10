#!/usr/bin/python
import os
import time
import pandas as pd
import stat
import shutil
import pathlib
from urllib import parse
from subprocess import Popen
from concurrent.futures import ThreadPoolExecutor

timeOut = 5 * 60
svnBaseDir = "svnRepos/"
gitBaseDir = "gitRepos/"
cwd = os.getcwd()
startTime = time.time()


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


def run(cmd):  # 运行长时间任务，超时终止
    t = time.time() - startTime
    # print("...", t, cmd)
    if t > timeOut:
        print("...... 超时退出 >>", t, cmd)
        return 10
    p = Popen(cmd)
    while p.poll() == None:
        if time.time() - startTime > timeOut:
            p.terminate()
            print("...... 超时退出 >>", t, cmd)
            return 15
        time.sleep(1)
    return p.returncode


def svncreate(name, path, url):
    if os.path.exists(path):
        return -1
    print(">>", name, "创建镜像库")
    if not os.path.exists(svnBaseDir):
        os.makedirs(svnBaseDir)
    pathUrl = path2url(path)
    status = os.system("svnadmin create " + svnBaseDir + name)
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
    status = svncreate(name, path, url)
    if status > 0:
        print("...", name, "建库失败", status)
        return status
    print(">>", name, "开始同步")
    pathUrl = path2url(path)
    status = run(["svnsync", "sync", pathUrl])
    # print("...", name, "status", status)
    if status >= 10:
        print("...", name, "异常退出", status)
        return status
    if status > 0:
        os.system("svn propdel svn:sync-lock --revprop -r0 " + pathUrl)
        time.sleep(1)
        status = run(["svnsync", "sync", pathUrl])
        if status > 0:
            print("...", name, "异常退出", status)
            return status

    print("...", name, "同步成功")
    return 0


def svn(executor):
    dataset = pd.read_csv("svn.csv")
    svnRepos = dataset.iloc[:, :2].values
    for svnRepo in svnRepos:
        reponame = svnRepo[0].strip()
        if reponame.startswith("#"):
            continue
        path = getAbsPath(svnBaseDir + reponame)
        url = svnRepo[1].strip()
        if time.time() - startTime > timeOut:
            print("...... 超时退出 >>", reponame)
            break
        executor.submit(svnsync, reponame, path, url)


def gitcreate(name, path, url):
    if os.path.exists(path):
        return -1
    print(">>", name, "创建镜像库")
    status = os.system("git clone --mirror " + url + " " + path)
    if status == 0:
        print("...", name, "创建成功")
    else:
        deletefile(path)
        print("...", name, "创建失败")
    return status


def gitsync(name, path, url):
    status = gitcreate(name, path, url)
    if status > 0:
        print("...", name, "建库失败", status)
        return status
    print(">>", name, "开始同步")
    status = run(["git", "--git-dir=" + path, "remote", "update"])
    if status > 0:
        print("...", name, "异常退出", status)
        return status
    print("...", name, "同步成功")
    return 0


def git(executor):
    dataset = pd.read_csv("git.csv")
    gitRepos = dataset.iloc[:, :2].values
    for gitRepo in gitRepos:
        reponame = gitRepo[0].strip()
        if reponame.startswith("#"):
            continue
        path = gitBaseDir + reponame + ".git"
        url = gitRepo[1].strip()
        if time.time() - startTime > timeOut:
            print("...... 超时退出 >>", reponame)
            break
        executor.submit(gitsync, reponame, path, url)


# main
executor = ThreadPoolExecutor(8)

svn(executor)
git(executor)
