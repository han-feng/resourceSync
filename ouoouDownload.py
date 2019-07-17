#!/usr/bin/python
# python 3.7
# OU中文网小说下载工具
# 命令行参数说明：
#   参数一：小说编号中的数字部分
#   参数二：从1开始的整数，第几篇文

import os
import sys
import time
import json
import zipfile
# requirements: requests bs4 lxml
import requests
from bs4 import BeautifulSoup


def get_text(srcUrl):
    # 获取文章内容
    strhtml = requests.get(srcUrl)
    soup = BeautifulSoup(strhtml.text, 'lxml')
    content = soup.select("#wrapper>div.box_con>div.bookname>h1")[
        0].get_text().strip()
    content += "\n\n"
    content += soup.select("#content")[0].get_text()
    return content


def make_dirs(dirPath):
    if not os.path.exists(dirPath):
        os.makedirs(dirPath)


if len(sys.argv) >= 3:
    sid = sys.argv[1]
    ss = sys.argv[2]
    print("ouoouDownload '%s' '%s'" % (sid, ss))
    id = int(sid)
    start = int(ss)-1
    if start < 0:
        start = 0
else:
    id = 33054
    start = 649

baseUrl = "http://www.ouoou.com"
indexUrl = baseUrl + "/ou_%d/" % id
strhtml = requests.get(indexUrl)

soup = BeautifulSoup(strhtml.text, 'lxml')
title = soup.select("#info>h1")[0].get_text().strip()
data = soup.select("#list>dl>dd>a")
total = len(data)
print("备份《%s》（ou_%d）：共%d篇，从第%d篇开始" % (title, id, total, start+1))

baseOutDir = "ouoou/"
outDir = "%s%d/" % (baseOutDir, id)
cacheDir = baseOutDir + "cache/"

make_dirs(outDir)
make_dirs(cacheDir)

fileIndex = {}
fileName = "%s%d+" % (title, start+1)
fileId = "%d-%d" % (id, start+1)
fileIndex[fileId] = {"parent": str(id), "fileName": fileName,
                     "createTime": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())}
txtFilePath = outDir + fileName + ".txt"
zipFilePath = outDir + fileName + ".zip"

# 新建输出文件
with open(txtFilePath, "w", encoding='utf-8') as file:
    for item in data[start:]:
        result = {
            'title': item.get("title"),
            # 'text': item.get_text(),
            'link': baseUrl + item.get("href")
        }
        url = baseUrl + item.get("href")
        text = get_text(url)
        file.write("\n")
        file.write(text)
        file.write("\n")

# 压缩输出文件
with zipfile.ZipFile(zipFilePath, "w") as f:
    f.write(txtFilePath, fileName + ".txt", compress_type=zipfile.ZIP_DEFLATED)

# 更新索引文件
indexJsonFile = cacheDir + "index.json"
indexHtmlFile = baseOutDir + "index.html"
if os.path.exists(indexJsonFile):
    try:
        with open(indexJsonFile, "r", encoding='utf-8') as f:
            data = json.load(f)
    except:
        data = {}
else:
    data = {}

data.update(fileIndex)
with open(indexJsonFile, "w", encoding='utf-8') as f:
    json.dump(data, f)

links = "  <ul>\n"
for item in data.values():
    t = item["createTime"]
    txt = item["fileName"] + ".txt"
    dir = item["parent"] + "/"
    links += '    <li><a href="%s%s">%s (%s)</a></li>\n' % (dir, txt, txt, t)
    zip = item["fileName"] + ".zip"
    links += '    <li><a href="%s%s">%s (%s)</a></li>\n' % (dir, zip, zip, t)
links += "  </ul>"

lines = '''
<html>
<head>
  <meta charset="utf-8">
  <meta http-equiv="X-UA-Compatible" content="IE=edge">
  <meta name="viewport" content="width=device-width,minimum-scale=1.0,maximum-scale=1.0,user-scalable=no"/>
</head>
<body>
%s
</body>
</html>
''' % links

with open(indexHtmlFile, "w", encoding='utf-8') as f:
    f.write(lines)
