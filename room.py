import re
import random

from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys


class Error(Exception):
    pass


class PlayerWinAction(Error):
    def __init__(self, winner):
        self.winner = winner


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
        self.free_time = 0
        self.tips = [r'在<a href="/post/16903">/post/16903</a>查看统计数据']

    def get_user_in_room(self, api):
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

    def update_room_info(self):
        try:
            self.available_user_count = int(self.driver.find_element_by_id('total-user').text)
            self.ready_user_count = int(self.driver.find_element_by_id('ready-user').text)
        except ValueError:
            self.available_user_count = 1
            self.ready_user_count = 1

    def send_message(self, msg):  # 发送消息
        if len(msg) > 95:
            self.send_message(msg[0:95])
            self.send_message(msg[95:len(msg)])
        try:
            message_box = self.driver.find_element_by_id("msg-sender")
            ac = ActionChains(self.driver)
            ac.send_keys_to_element(message_box, msg)
            ac.send_keys(Keys.ENTER).perform()
        except:
            pass
        return

    def do_something_out_of_game(self):
        """主循环，游戏外的操作"""
        self.free_time += 1
        if self.free_time % 480 == 10 and not self.secret:
            self.send_message("【提示】" + random.choice(self.tips))
        if self.free_time % 1000 == 999 and not self.secret:
            self.driver.refresh()  # 闲时自动刷新，防卡
        winner = ''
        try:
            winner = self.driver.find_element_by_id('swal2-content').get_attribute('innerText')
            winner = winner[0:winner.find("赢了")]
        except:
            pass
        if winner != '':
            ac = ActionChains(self.driver)
            ac.send_keys(Keys.ENTER).perform()
            raise PlayerWinAction(winner)
        try:
            speed = int(
                self.driver.find_element_by_id('settings-gamespeed-input-display').get_attribute('innerText'))
            if speed != '4':
                for _ in range(4 - speed):
                    ActionChains(self.driver).send_keys_to_element(
                        self.driver.find_elements_by_class_name('custom-range')[0],
                        Keys.RIGHT).perform()
            check_box = self.driver.find_element_by_class_name('form-check-input')
            if (check_box.is_selected() and not self.secret) or (
                    not (check_box.is_selected()) and self.secret):
                check_box.click()
            random_btn = self.driver.find_element_by_css_selector('[data="' + self.selected_map + '"]')
            random_btn.click()
        except:
            pass
        self.update_room_info()
