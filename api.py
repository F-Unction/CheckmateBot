import requests
import json

cookie = ''


def post(baseurl, data):
    headers = {'Cookie': cookie}
    res = requests.post(baseurl, data=data, headers=headers)
    res.encoding = 'utf-8'
    return res.text


def get(baseurl, params):
    headers = {'Cookie': cookie}
    res = requests.get(baseurl, params=params, headers=headers)
    res.encoding = 'utf-8'
    return res.text


# User
def get_user_post_by_uid(uid, page):
    res = json.loads(post('https://kana.byha.top:444/api/user/post', {'uid': uid, 'page': page}))
    return res['dat']


def get_user_level_by_uid(uid):
    res = json.loads(post('https://kana.byha.top:444/api/user/level', {'uid': uid}))
    return res['msg']


def get_user_level_by_exp(exp):
    if exp >= 28800:
        return 6
    elif exp >= 10800:
        return 5
    elif exp >= 4500:
        return 4
    elif exp >= 1500:
        return 3
    elif exp >= 200:
        return 2
    elif exp >= 100:
        return 1
    else:
        return 0


def get_user_exp_by_uid(uid):
    res = json.loads(post('https://kana.byha.top:444/api/user/exp', {'uid': uid}))
    return res['msg']


def get_user_comment_amount_by_uid(uid):
    res = json.loads(get('https://kana.byha.top:444/api/user/commentAmount', {'uid': uid}))
    return res['msg']


def get_user_post_amount_by_uid(uid):
    res = json.loads(get('https://kana.byha.top:444/api/user/postAmount', {'uid': uid}))
    return res['msg']


def get_user_info_by_uid(uid):
    res = json.loads(get('https://kana.byha.top:444/api/user/info', {'uid': uid}))
    return res['msg']


def get_uid_by_username(uname):
    res = json.loads(get('https://kana.byha.top:444/api/user/name2id', {'uname': uname}))
    return res['msg']


# page(index)
def get_post_by_page(page):
    res = json.loads(post('https://kana.byha.top:444/api/page', {'page': page}))
    return res['dat']


# send_post
def send_post(content):
    res = json.loads(post('https://kana.byha.top:444/api/post', {'content': content, 'type': 0}))
    return res['msg']


def update_post(pid, content):
    res = json.loads(post('https://kana.byha.top:444/api/updatepost', {'content': content, 'pid': pid}))
    return res['msg']


# comment
def get_comment_by_pid(pid, page):
    res = json.loads(get('https://kana.byha.top:444/api/comment', {'pid': pid, 'parent': 0, 'page': page}))
    return res['dat']


def send_comment_by_pid(pid, comment):
    res = json.loads(post('https://kana.byha.top:444/api/comment', {'pid': pid, 'parent': 0, 'comment': comment}))
    return res['msg']


def get_comment_amount_by_pid(pid):
    res = json.loads(get('https://kana.byha.top:444/api/commentAmount', {'pid': pid, 'parent': 0}))
    return res['dat']


def get_source_post_by_pid(pid):
    res = json.loads(post('https://kana.byha.top:444/api/getSourcePost', {'pid': pid}))
    return res['msg']


def delete_post_by_pid(pid):
    res = json.loads(post('https://kana.byha.top:444/api/deletepost', {'pid': pid}))
    return res['msg']


# admin
def get_battle_by_page(page):
    return get('https://kana.byha.top:444/admin/battle', {'page': page})
