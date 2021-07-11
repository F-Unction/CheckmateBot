import re


class Error(Exception):
    pass


class UserEnterRoom(Error):
    def __init__(self, username):
        self.username = username


class UserLeaveRoom(Error):
    def __init__(self, username):
        self.username = username


class Room(object):
    def __init__(self, driver, username):
        self.driver = driver
        self.id = 'undefined'
        self.username = username
        self.secret = False
        self.auto_ready = True
        self.selected_map = '1'
        self.total_user_count = 1
        self.available_user_count = 1
        self.ready_user_count = 1
        self.users = []

    def get_user_in_room(self, api):
        pre_users = self.users
        html = str(api.APIGET('https://kana.byha.top:444/checkmate/room', {}))
        ans = ''
        self.users = []
        while True:
            g = re.search(r'<th>[\s\S]*?</th>', html)
            if g:
                tmp = g.group()
                if tmp.find(self.username) != -1 and tmp.find(r'/checkmate/room/') == -1:
                    ans = tmp[4:len(tmp) - 5]
                    break
                html = html[html.find(tmp) + 1:]
            else:
                break
        while True:
            pos = ans.find(';')
            if pos == -1 or len(self.users) == 8:
                break
            self.users.append(ans[:pos])
            ans = ans[pos + 1:]
        self.total_user_count = len(self.users)
        for i in pre_users:
            if i not in self.users:
                raise UserLeaveRoom(i)
        for i in self.users:
            if i not in pre_users:
                raise UserEnterRoom(i)

    def update_room_info(self):
        try:
            self.available_user_count = int(self.driver.find_element_by_id('total-user').text)
            self.ready_user_count = int(self.driver.find_element_by_id('ready-user').text)
        except ValueError:
            self.available_user_count = 1
            self.ready_user_count = 1
