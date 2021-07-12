import base64
import datetime
import json
import random
import re
import threading
from time import sleep

from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait
from tencentcloud.common import credential
from tencentcloud.common.exception.tencent_cloud_sdk_exception import TencentCloudSDKException
from tencentcloud.common.profile.client_profile import ClientProfile
from tencentcloud.common.profile.http_profile import HttpProfile
from tencentcloud.ocr.v20181119 import ocr_client, models

import api
import room
import game


def at_player_by_uid(uid):
    return '[at,uid=' + str(uid) + ']'


class Bot(object):

    def __init__(self):
        self.kanaLink = 'https://kana.byha.top:444/'

        config = json.load(open("config.json", 'r'))
        self.username = config['username']  # 用户名
        self.password = config['password']  # 密码
        self.room_id = config['roomID']  # 房间号
        self.secretId = config['secretId']
        self.secretKey = config['secretKey']

        self.default_user_remain_win_time = 10
        self.tips = [r'在<a href="/post/16903">/post/16903</a>查看统计数据']

        # 以下是每日更新的数据
        self.user_remain_win_time = {}  # 每个玩家的单挑剩余次数
        self.game_count = []  # 每种对局的次数
        self.user_score = {}  # 每个玩家的分数

    def send_key_to_table(self, key):
        """发送按键"""
        ac = ActionChains(self.driver)
        ac.send_keys(key).perform()

    def enter_room(self):
        """进入房间"""
        self.driver.get(
            'https://kana.byha.top:444/checkmate/room/' + self.room.id)
        if self.room.secret:
            settingBtn = self.driver.find_element_by_class_name(
                'form-check-input')
            ac = ActionChains(self.driver)
            ac.click(settingBtn).perform()
        print('Bot已就位！')
        self.url = self.driver.current_url

    def select_land(self, x, y):  # 选择土地
        try:
            self.driver.find_element_by_id(
                'td-' + str((x - 1) * self.game.mp.size + y)).click()
            self.game.curx = x
            self.game.cury = y
            return
        except:
            return

    def logout(self):  # 登出
        print('正在登出…')
        self.driver.get('https://kana.byha.top:444/logout')
        self.driver.switch_to.default_content()
        sleep(5)
        self.driver.find_element_by_id('submitButton').click()
        return

    def del_element(self, a):
        """删除页面中元素"""
        self.driver.execute_script("""
                                   var element = arguments[0];
                                     element.parentNode.removeChild(element);
                                     """, a)
        return

    def login(self):
        """登录"""
        print('正在登录…')
        self.driver.get(self.kanaLink)
        self.del_element(self.driver.find_element_by_class_name('redirect'))
        usernameBox = self.driver.find_element_by_name('username')
        passwordBox = self.driver.find_element_by_name('pwd')

        ac = ActionChains(self.driver)
        ac.send_keys_to_element(usernameBox, self.username)
        ac.send_keys_to_element(passwordBox, self.password).perform()

        cap_correction = {'丫': 'Y', '了': '3', '尺': 'R'}  # 手动纠错

        while True:
            if self.driver.current_url == self.kanaLink:
                break
            self.driver.execute_script('document.getElementById("submitButton").style.display = "none"')
            self.driver.execute_script('document.getElementById("cap").childNodes[1].style.width="150%"')
            frame = self.driver.find_element_by_xpath('/html/body/div[2]/div/form/div[1]/object')
            self.driver.switch_to.frame(frame)
            try:
                a = self.driver.find_element_by_css_selector('[fill="none"]')
                self.del_element(a)
            except:
                sleep(1)
                continue

            self.driver.switch_to.default_content()

            cap = -1
            self.driver.get_screenshot_as_file('a.png')

            try:
                cred = credential.Credential(self.secretId, self.secretKey)
                httpProfile = HttpProfile()
                httpProfile.endpoint = 'ocr.tencentcloudapi.com'

                clientProfile = ClientProfile()
                clientProfile.httpProfile = httpProfile
                client = ocr_client.OcrClient(cred, 'ap-shanghai', clientProfile)

                req = models.GeneralBasicOCRRequest()
                params = {
                    'ImageBase64': base64.b64encode(open('a.png', 'rb').read()).decode()
                }
                req.from_json_string(json.dumps(params))

                resp = client.GeneralBasicOCR(req)
                a = json.loads(resp.to_json_string())

            except TencentCloudSDKException as err:
                print(err)
            self.driver.execute_script('document.getElementById("cap").childNodes[1].style.width="100%"')
            for i in a['TextDetections']:
                tmp = i['DetectedText']
                s = ''
                for j in tmp:
                    if j != '(' and j != ')':  # 去除诡异括号
                        s += j
                    if j in cap_correction:
                        s += cap_correction[j]
                tmp = s
                if re.match(r'\w\w\w\w', tmp) and len(tmp) == 4:
                    cap = tmp
                    break
            print(cap)
            ac = ActionChains(self.driver)
            ac.send_keys_to_element(self.driver.find_element_by_name("cap"), cap).perform()
            self.driver.execute_script('document.getElementById("submitButton").style.display = ""')
            self.driver.find_element_by_id("submitButton").click()
            try:
                WebDriverWait(self.driver, 10).until(EC.url_to_be(self.kanaLink))
                break
            except TimeoutException:
                pass
        print("登录成功！")
        return

    def flush_movements(self):  # 更新移动
        tmp = self.game.mp.mp[self.game.homex][self.game.homey].tmp
        curm = self.game.movements[0]
        while isinstance(curm, list):
            self.select_land(curm[0], curm[1])
            self.game.movements.pop(0)
            if not self.game.movements:
                return
            curm = self.game.movements[0]
        self.send_key_to_table(curm)
        if self.game.movements[0] == 'W':
            self.game.curx -= 1
        elif self.game.movements[0] == 'S':
            self.game.curx += 1
        elif self.game.movements[0] == 'A':
            self.game.cury -= 1
        elif self.game.movements[0] == 'D':
            self.game.cury += 1
        self.game.movements.pop(0)
        self.game.get_map()
        self.game.update_map()
        trytime = 0
        while self.game.mp.mp[self.game.homex][self.game.homey].tmp == tmp and trytime <= 80:
            self.game.get_map()
            trytime += 1
        # if self.game.mp.mp[self.game.curx][self.game.cury].belong != 1:
        #     self.game.movements = []

        return

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

    def get_user_in_room(self):
        """获取房间中的玩家"""
        while True:
            sleep(5)
            if not self.on:
                return
            try:
                self.room.get_user_in_room(api)
            except room.UserLeaveRoom as e:
                self.send_message(e.username + '离开了房间')
            except room.UserEnterRoom:
                pass

    def analyze(self):
        """数据分析"""
        analyze_data = {}
        uid = 1
        max_uid = 1
        while True:
            info = api.GetUserInfoByUid(uid)
            if info == '数据库错误':
                if uid <= 3800:
                    uid += 1
                    continue
                else:
                    break
            exp = api.GetUserExpByUid(uid)
            analyze_data[uid] = {}
            analyze_data[uid]['info'] = info
            analyze_data[uid]['exp'] = exp
            analyze_data[uid]['username'] = info['username']
            max_uid = uid
            uid += 1
        ans = ''
        cur_time = datetime.datetime.now()
        ans += '更新于' + str(cur_time.year) + '.' + str(cur_time.month) + '.' + str(cur_time.day) + ',' + str(
            cur_time.hour) + ':' + str(cur_time.minute) + ':' + str(cur_time.second) + '\n\n'
        uid_keys = list(analyze_data.keys())
        for i in range(len(uid_keys)):
            uid_keys[i] = int(uid_keys[i])
        tot = 0
        for uid in uid_keys:
            if uid != 1:
                tot += int(analyze_data[uid].get('exp', 0))
        ans += '### 经验值分布统计（排除admin）\n\n'
        ans += '用户经验总和：' + str(tot) + '\n\n'
        role = lambda a: a[1]
        k = []
        for i in range(1, max_uid // 1000 + 2):
            l = max((i - 1) * 1000 + 1, 2)
            r = min(i * 1000, max_uid)
            if l > max_uid:
                break
            tot = 0
            max_exp = 0
            max_user = 0
            for j in range(l, r + 1):
                if j in uid_keys:
                    exp = int(analyze_data[j].get('exp', 0))
                    tot += exp
                    k.append([j, exp])
                    if exp > max_exp:
                        max_user = j
                        max_exp = exp
            ans += str(l) + '~' + str(r) + '总和：' + str(tot) + '，最大值' + at_player_by_uid(max_user) + '（' + str(
                max_exp) + '经验）\n\n'
        k.sort(key=role, reverse=True)
        ans += '经验排行榜前50名：\n\n'
        for i in range(50):
            ans += '#' + str(i + 1) + '：' + at_player_by_uid(k[i][0]) + '，' + str(k[i][1]) + '经验\n\n'
        ans += '### 今日数据\n\n'
        for i in range(2, 9):
            ans += str(i) + '人局，' + str(self.game_count[i]) + '场\n\n'
        ans += '单挑排行榜：（按剩余单挑次数排列）\n\n'
        k = []
        for i in uid_keys:
            cur_uname = analyze_data[i].get('username', 'undefined')
            cur_win_time = self.user_remain_win_time.get(cur_uname, self.default_user_remain_win_time)
            if cur_win_time < self.default_user_remain_win_time:
                k.append([i, cur_win_time])
        k.sort(key=role)
        for i in range(len(k)):
            ans += '#' + str(i + 1) + '：' + at_player_by_uid(k[i][0]) + '，剩余' + str(k[i][1]) + '次\n\n'
        ans += '分数排行榜\n\n'
        k = []
        for i in uid_keys:
            cur_uname = analyze_data[i].get('username', 'undefined')
            cur_score = self.user_score.get(cur_uname, 0)
            if cur_score > 0:
                k.append([i, cur_score])
        k.sort(key=role, reverse=True)
        for i in range(len(k)):
            ans += '#' + str(i + 1) + '：' + at_player_by_uid(k[i][0]) + '，' + str(k[i][1]) + '分\n\n'
        ans += '### 波特家族统计\n\n'
        cnt = 0
        for i in uid_keys:
            cur_uname = analyze_data[i].get('username', 'undefined')
            if cur_uname.lower().find('bot') != -1:
                ans += at_player_by_uid(i) + ' '
                cnt += 1
        ans += '\n\n共' + str(cnt) + '个'
        api.UpdatePost(16903, ans)

    def clear_data(self):
        """清除每日数据"""
        self.user_remain_win_time = {}
        self.game_count = [0, 0, 0, 0, 0, 0, 0, 0, 0]
        self.user_score = {}

    def Main(self):
        self.driver = webdriver.Firefox()  # 浏览器
        # self.driver = webdriver.Chrome()
        self.game = game.Game(self.driver)
        self.room = room.Room(self.driver, self.username)
        self.room.id = self.room_id
        self.login()
        self.enter_room()
        self.on = True
        self.clear_data()
        flag = False
        ban = False
        free_time = 0
        tmp = self.driver.get_cookies()
        for i in tmp:
            if i['name'] == 'client_session':
                api.cookie = 'client_session=' + i['value']
                break
        print(api.cookie)
        threading.Thread(target=self.get_user_in_room, name="detect").start()
        while True:
            cur_time = datetime.datetime.now()
            if cur_time.hour not in range(8, 23):
                self.on = False
                self.driver.get('https://kana.byha.top:444/')
                self.analyze()
                self.logout()
                self.driver.close()
                del self.driver
                del self.room
                del self.game
                return
            if self.driver.current_url != self.url:
                self.enter_room()
                sleep(10)
                continue
            ac = ActionChains(self.driver)
            ac.send_keys(Keys.CONTROL).perform()  # 防踢
            try:
                if self.driver.find_element_by_id("game-status").get_attribute('innerHTML') != "游戏中":
                    if flag:
                        flag = False
                    sleep(0.2)
                    self.game.is_pre = False
                else:
                    free_time = 0
                    try:
                        self.game.bot_move()
                    except game.FlushMovements:
                        self.flush_movements()
                    continue
                flag = True
            except:
                continue
            try:
                speed = int(
                    self.driver.find_element_by_id('settings-gamespeed-input-display').get_attribute('innerText'))
                if speed != '4':
                    for _ in range(4 - speed):
                        ActionChains(self.driver).send_keys_to_element(
                            self.driver.find_elements_by_class_name('custom-range')[0],
                            Keys.RIGHT).perform()
            except:
                pass
            free_time += 1
            if free_time % 480 == 10 and not self.room.secret:
                self.send_message("【提示】" + random.choice(self.tips))
            if free_time % 1000 == 999 and not self.room.secret:
                self.driver.refresh()  # 闲时自动刷新，防卡
            try:
                winner = self.driver.find_element_by_id('swal2-content').get_attribute('innerText')
                winner = winner[0:winner.find("赢了")]
                if winner != '':
                    ac = ActionChains(self.driver)
                    ac.send_keys(Keys.ENTER).perform()
                    game_size = len(self.game.players)
                    self.game_count[game_size] += 1
                    if game_size == 2 and winner != self.username:
                        current_win_time = self.user_remain_win_time.get(winner, self.default_user_remain_win_time)
                        self.user_remain_win_time[winner] = current_win_time - 1
                        self.send_message('剩余单挑次数' + str(current_win_time - 1) + '次')
                    if game_size > 2:
                        current_score = self.user_score.get(winner, 0)
                        addition = 2 ** (game_size - 3)
                        self.user_score[winner] = current_score + addition
                        self.send_message(
                            '赢家' + winner + '目前' + str(self.user_score[winner]) + '分（+' + str(addition) + '）')
            except:
                pass
            try:
                checkBox = self.driver.find_element_by_class_name('form-check-input')  # 防私密
                if (checkBox.is_selected() and not self.room.secret) or (
                        not (checkBox.is_selected()) and self.room.secret):
                    checkBox.click()
                randomBtn = self.driver.find_element_by_css_selector('[data="' + self.room.selected_map + '"]')
                randomBtn.click()
            except:
                pass
            ban = False
            self.room.update_room_info()
            if self.room.available_user_count > self.room.total_user_count:
                continue
            if self.room.available_user_count == 1:
                ban = True
            elif self.room.available_user_count == 2:
                for username in self.room.users:
                    if self.user_remain_win_time.get(username, self.default_user_remain_win_time) <= 0:
                        ban = True
                        break
            try:
                if self.room.auto_ready and self.driver.find_element_by_id('ready').get_attribute(
                        'innerHTML') == '准备' and not ban:
                    ac = ActionChains(self.driver)
                    ac.click(self.driver.find_element_by_id('ready')).perform()
                if self.driver.find_element_by_id('ready').get_attribute(
                        'innerHTML') == '取消准备' and ban:
                    ac = ActionChains(self.driver)
                    ac.click(self.driver.find_element_by_id('ready')).perform()
            except:
                pass


def main():
    a = Bot()
    while True:
        cur_time = datetime.datetime.now()
        if cur_time.hour in range(8, 23):
            a.Main()
        sleep(60)


if __name__ == '__main__':
    main()
