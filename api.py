import requests
import json

cookie = ''


def APIPOST(baseurl, data):
    headers = {'Cookie': cookie}
    res = requests.post(baseurl, data=data, headers=headers)
    res.encoding = 'utf-8'
    return res.text


def APIGET(baseurl, params):
    headers = {'Cookie': cookie}
    res = requests.get(baseurl, params=params, headers=headers)
    res.encoding = 'utf-8'
    return res.text


# User
def GetUserPostByUid(uid, page):
    res = json.loads(APIPOST('https://kana.byha.top:444/api/user/post', {'uid': uid, 'page': page}))
    return res['dat']


def GetUserLevelByUid(uid):
    res = json.loads(APIPOST('https://kana.byha.top:444/api/user/level', {'uid': uid}))
    return res['msg']


def GetUserExpByUid(uid):
    res = json.loads(APIPOST('https://kana.byha.top:444/api/user/exp', {'uid': uid}))
    return res['msg']


def GetUserCommentAmountByUid(uid):
    res = json.loads(APIGET('https://kana.byha.top:444/api/user/commentAmount', {'uid': uid}))
    return res['msg']


def GetUserPostAmountByUid(uid):
    res = json.loads(APIGET('https://kana.byha.top:444/api/user/postAmount', {'uid': uid}))
    return res['msg']


def GetUserInfoByUid(uid):
    res = json.loads(APIGET('https://kana.byha.top:444/api/user/info', {'uid': uid}))
    return res['msg']


def GetUidByUsername(uname):
    res = json.loads(APIGET('https://kana.byha.top:444/api/user/name2id', {'uname': uname}))
    return res['msg']


# page(index)
def GetPostByPage(page):
    res = json.loads(APIPOST('https://kana.byha.top:444/api/page', {'page': page}))
    return res['dat']


# sendpost
def SendPost(content):
    res = json.loads(APIPOST('https://kana.byha.top:444/api/post', {'content': content, 'type': 0}))
    return res['msg']


def UpdatePost(pid, content):
    res = json.loads(APIPOST('https://kana.byha.top:444/api/updatepost', {'content': content, 'pid': pid}))
    return res['msg']


# comment
def GetCommentByPostid(pid, page):
    res = json.loads(APIGET('https://kana.byha.top:444/api/comment', {'pid': pid, 'parent': 0, 'page': page}))
    return res['dat']


def SendCommentByPostid(pid, comment):
    res = json.loads(APIPOST('https://kana.byha.top:444/api/comment', {'pid': pid, 'parent': 0, 'comment': comment}))
    return res['msg']


def GetCommentAmountByPostid(pid):
    res = json.loads(APIGET('https://kana.byha.top:444/api/commentAmount', {'pid': pid, 'parent': 0}))
    return res['dat']


def GetSourcePostByPostid(pid):
    res = json.loads(APIPOST('https://kana.byha.top:444/api/getSourcePost', {'pid': pid}))
    return res['msg']


def DeletePostByPostid(pid):
    res = json.loads(APIPOST('https://kana.byha.top:444/api/deletepost', {'pid': pid}))
    return res['msg']


# admin
def GetBattleByPage(page):
    return APIGET('https://kana.byha.top:444/admin/battle', {'page': page})
