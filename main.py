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
from map import *


def at_player_by_uid(uid):
    return '[at,uid=' + str(uid) + ']'


class Bot(object):

    def __init__(self):
        self.kanaLink = 'https://kana.byha.top:444/'

        config = json.load(open("config.json", 'r'))
        self.username = config['username']  # 用户名
        self.password = config['password']  # 密码
        self.roomId = config['roomID']  # 房间号
        self.secretId = config['secretId']
        self.secretKey = config['secretKey']

        self.default_user_remain_win_time = 10

        self.isSecret = False
        self.isAutoReady = True
        self.mp = Map()  # 地图
        self.selectedMap = '1'
        self.ondefend = False
        self.user_count = 1
        self.user_in_room = []
        self.user_in_game = []

        self.tips = [r'在<a href="/post/16903">/post/16903</a>查看统计数据']

        # 以下是每日更新的数据
        self.user_remain_win_time = {}  # 每个玩家的单挑剩余次数
        self.game_count = []  # 每种对局的次数（用于数据分析）

    def send_key_to_table(self, key):
        """发送按键"""
        ac = ActionChains(self.driver)
        ac.send_keys(key).perform()

    def enter_room(self):
        """进入房间"""
        self.driver.get(
            'https://kana.byha.top:444/checkmate/room/' + self.roomId)
        if self.isSecret:
            settingBtn = self.driver.find_element_by_class_name(
                'form-check-input')
            ac = ActionChains(self.driver)
            ac.click(settingBtn).perform()
        print('Bot已就位！')
        self.url = self.driver.current_url

    def get_map(self):
        """获取地图"""
        try:
            s = self.driver.find_element_by_id("m").get_attribute("innerHTML")
        except:
            return
        stype = []
        stmp = []
        cnt = 0
        while True:
            tmp = re.search(r'class="[\s\S]*?"', s)
            if tmp:
                g = tmp.group()
                g = g[7:len(g) - 1]
                stype.append(" " + g + " ")
                p = s.find(g)
                s = s[p + len(g):len(s)]
                cnt += 1
            else:
                break
            tmp = re.search(r'>.*?<', s)
            g = tmp.group()
            g = g[1:len(g) - 1]
            stmp.append(g)
        self.mp.resize(int(cnt ** 0.5))
        if self.mp.size not in [9, 10, 19, 20]:
            return
        for i in range(1, self.mp.size + 1):
            for j in range(1, self.mp.size + 1):
                p = stype[0]
                stype.pop(0)
                if p.find(" city ") != -1:
                    self.mp.mp[i][j].type = 'city'
                elif p.find(' empty-city ') != -1:
                    self.mp.mp[i][j].type = 'empty-city'
                elif p.find(" crown ") != -1:
                    self.mp.mp[i][j].type = 'general'
                elif p.find(' mountain ') != -1 or p.find(' obstacle ') != -1 or p.find(' gas ') != -1:
                    self.mp.mp[i][j].type = 'mountain'
                elif p.find(' null ') != -1 and p.find(' grey ') == -1:
                    self.mp.mp[i][j].type = 'land'
                elif p.find(' null ') != -1 and p.find(' grey ') != -1:
                    self.mp.mp[i][j].type = 'empty'
                else:
                    self.mp.mp[i][j].type = 'unknown'
                if p.find(' own ') != -1:
                    self.mp.mp[i][j].belong = 1
                else:
                    self.mp.mp[i][j].belong = 0
                p = stmp[0]
                stmp.pop(0)
                try:
                    self.mp.mp[i][j].tmp = int(p)
                except:
                    self.mp.mp[i][j].tmp = 0
        return

    def select_land(self, x, y):  # 选择土地
        try:
            self.driver.find_element_by_id(
                'td-' + str((x - 1) * self.mp.size + y)).click()
            self.curx = x
            self.cury = y
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

        cap_correction = {'丫': 'Y', '了': '3'}  # 手动纠错

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

    def moveTo(self, x, y):  # 移动
        path, cost = self.mp.findPath(self.curx, self.cury, x, y)
        if path:
            path.pop(0)
            cx = self.curx
            cy = self.cury
            while path:
                px = path[0][0]
                py = path[0][1]
                if cx < px and cy == py:
                    self.movements.append('S')
                elif cx > px and cy == py:
                    self.movements.append('W')
                elif cx == px and cy > py:
                    self.movements.append('A')
                else:
                    self.movements.append('D')
                cx = px
                cy = py
                path.pop(0)
        return

    def flushMovements(self):  # 更新移动
        tmp = self.mp.mp[self.homex][self.homey].tmp
        self.send_key_to_table(self.movements[0])
        if self.mp.mp[self.curx][self.cury].belong != 1:
            self.movements = []
            return
        if self.movements[0] == 'W':
            self.curx -= 1
        elif self.movements[0] == 'S':
            self.curx += 1
        elif self.movements[0] == 'A':
            self.cury -= 1
        else:
            self.cury += 1
        self.movements.pop(0)
        self.get_map()
        self.updateMap()
        trytime = 0
        while self.mp.mp[self.homex][self.homey].tmp == tmp and trytime <= 80:
            self.get_map()
            trytime += 1
        return

    def pre(self):  # 预处理地图
        tmp = self.mp.findMatch(lambda a: a.type == 'general' and a.belong == 1)
        if len(tmp) != 1:
            return 1
        self.homex = tmp[0][0]
        self.homey = tmp[0][1]
        self.curx = self.homex
        self.cury = self.homey
        self.movements = []
        self.homes = []
        self.vis = []
        self.ispre = True  # 是否预处理
        self.useless = []
        self.preland = []
        self.user_in_game = []

        a = self.driver.find_element_by_id('info-content').get_attribute('innerHTML')
        while True:  # 读取领地-兵力排行榜
            p1 = a.find(':')
            p2 = a.find(';')
            if p1 == -1 or p2 == -1:
                break
            color = a[p1 + 2:p2]
            a = a[p2 + 1:]
            p1 = a.find('>')
            p2 = a.find('<')
            username = a[p1 + 1:p2]
            self.user_in_game.append(username)
        ans = ''
        for username in self.user_in_room:
            if username not in self.user_in_game:
                ans += username + ','
        if ans != '':
            self.send_message('玩家' + ans + '未参战')
        return 0

    def send_message(self, msg):  # 发送消息
        if len(msg) > 95:
            self.send_message(msg[0:95])
            self.send_message(msg[95:len(msg)])
        try:
            messageBox = self.driver.find_element_by_id("msg-sender")
            ac = ActionChains(self.driver)
            ac.send_keys_to_element(messageBox, msg)
            ac.send_keys(Keys.ENTER).perform()
        except:
            pass
        return

    def updateMap(self):  # 分析地图
        tmp = self.mp.findMatch(lambda a: a.type == 'general' and a.belong != 1)
        if tmp:
            for i in tmp:
                if i not in self.homes:  # 找家
                    self.homes.append(i)
        tmp = self.mp.findMatch(lambda a: a.type != 'unknown')
        for i in tmp:
            if i not in self.vis:  # 已经可见的土地无需探索
                self.vis.append(i)
        if not self.preland:
            self.preland = self.mp.findMatch(lambda a: a.type == 'empty' or a.belong == 1)
        else:
            enemy = self.mp.findMatch(lambda a: a.belong != 1)
            for i in enemy:
                if i in self.preland and i not in self.useless:  # 之前是空地或己方土地，现在是敌方土地，无需探索
                    self.useless.append(i)
            self.preland = []
        return

    def botMove(self):  # 主循环，每回合执行一次
        self.get_map()
        if not self.ispre:
            if self.pre() == 1:
                return
        if self.movements:
            self.flushMovements()
            return
        if [self.curx, self.cury] in self.homes and self.mp.mp[self.curx][self.cury].belong == 1:  # 已经占领的家移除
            self.homes.remove([self.curx, self.cury])
        if [self.curx, self.cury] not in self.vis:
            self.vis.append([self.curx, self.cury])
        self.updateMap()
        mx = self.mp.findMax(lambda a: a.belong == 1)
        if self.mp.mp[mx[0]][mx[1]].tmp <= 5:
            return
        if self.homes:  # 智能掏家
            if self.mp.mp[mx[0]][mx[1]].tmp > 30 and self.mp.mp[mx[0]][mx[1]].type == 'general':
                tmp = self.mp.findMax(lambda a: a.type != 'general' and a.belong == 1)
                if self.mp.mp[tmp[0]][tmp[1]].tmp * 3 > self.mp.mp[mx[0]][mx[1]].tmp:
                    mx = tmp
            self.select_land(mx[0], mx[1])
            tmp = random.choice(self.homes)
            self.moveTo(tmp[0], tmp[1])
            return
        tmp = self.mp.findMatchByRange(self.homex, self.homey, 1,
                                       lambda a: a.belong != 1 and (a.type == 'land' or a.type == 'city'))
        if tmp and self.mp.mp[mx[0]][mx[1]].tmp > 30:  # 智能守家
            mx = self.mp.findMax(lambda a: a.type != 'general' and a.belong == 1)
            self.select_land(mx[0], mx[1])
            tmp = random.choice(tmp)
            self.moveTo(tmp[0], tmp[1])
            self.ondefend = True
            return
        if self.ondefend and dist(self.curx, self.cury, self.homex, self.homey) <= 2:
            self.moveTo(self.homex, self.homey)
            self.ondefend = False
            return
        self.ondefend = False
        tmp = self.mp.findMatch(lambda a: a.type == 'unknown')
        random.shuffle(tmp)
        role = lambda a: len(self.mp.findMatchByRange(a[0], a[1], 4, lambda b: b.type == 'land' and b.belong != 1 and (
                a not in self.useless)))
        tmp.sort(key=role, reverse=True)
        for i in tmp:
            if [i[0], i[1]] not in self.vis:
                target = i
                break
        owned = self.mp.findMatch(lambda a: a.belong == 1 and a.tmp >= self.mp.mp[target[0]][target[1]].tmp)
        if not owned:
            owned = [[self.homex, self.homey]]
        random.shuffle(owned)
        mindist = 10000
        ans = []
        for i in owned:
            p = dist(i[0], i[1], target[0], target[1])
            if p < self.mp.mp[i[0]][i[1]].tmp and p < mindist:
                path, cost = self.mp.findPath(self.curx, self.cury, target[0], target[1])
                if self.mp.mp[i[0]][i[1]].tmp >= cost:
                    mindist = p
                    ans = i
        if ans:  # 探索
            if ans[0] == self.homex and ans[1] == self.homey:
                self.send_key_to_table('Z')
            self.select_land(ans[0], ans[1])
            self.moveTo(target[0], target[1])
        return

    def getUserInRoom(self):
        a = str(api.APIGET('https://kana.byha.top:444/checkmate/room', {}))
        ans = ''
        uname = []
        while True:
            g = re.search(r'<th>[\s\S]*?</th>', a)
            if g:
                tmp = g.group()
                if tmp.find(self.username) != -1 and tmp.find(r'/checkmate/room/') == -1:
                    ans = tmp[4:len(tmp) - 5]
                    break
                a = a[a.find(tmp) + 1:]
            else:
                break
        while True:
            pos = ans.find(';')
            if pos == -1 or len(uname) == 8:
                break
            uname.append(ans[:pos])
            ans = ans[pos + 1:]
        if not uname:
            return self.user_in_room
        else:
            return uname

    def get_user_in_room(self):
        """获取房间中的玩家"""
        self.user_in_room = []
        while True:
            tmp = self.user_in_room
            sleep(1)
            if not self.on:
                return
            self.user_in_room = self.getUserInRoom()
            for i in tmp:
                if i not in self.user_in_room:
                    self.send_message(i + '离开了房间')
            # for i in self.user_in_room: # 由于目前Kana的相同IP特性，该功能无意义
            #     if i not in tmp:
            #         self.sendMessage(i + '进入了房间')

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

    def Main(self):
        self.driver = webdriver.Firefox()  # 浏览器
        # self.driver = webdriver.Chrome()
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
                return
            if self.driver.current_url != self.url:
                self.enter_room()
                sleep(10)
                continue
            ac = ActionChains(self.driver)
            ac.send_keys(Keys.CONTROL).perform()  # 防踢
            self.user_count = len(self.user_in_room)
            try:
                if self.driver.find_element_by_id("game-status").get_attribute('innerHTML') != "游戏中":
                    if flag:
                        flag = False
                    sleep(0.2)
                    self.ispre = False
                else:
                    free_time = 0
                    self.botMove()
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
            if free_time % 480 == 10 and not self.isSecret:
                self.send_message("【提示】" + random.choice(self.tips))
            try:
                winner = self.driver.find_element_by_id('swal2-content').get_attribute('innerText')
                winner = winner[0:winner.find("赢了")]
                if winner != '':
                    ac = ActionChains(self.driver)
                    ac.send_keys(Keys.ENTER).perform()
                    self.game_count[len(self.user_in_game)] += 1
                    current_win_time = self.user_remain_win_time.get(winner, self.default_user_remain_win_time)
                    self.user_remain_win_time[winner] = current_win_time - 1
                    self.send_message('剩余单挑次数' + str(current_win_time - 1) + '次')
            except:
                pass
            try:
                checkBox = self.driver.find_element_by_class_name('form-check-input')  # 防私密
                if (checkBox.is_selected() and not self.isSecret) or (not (checkBox.is_selected()) and self.isSecret):
                    checkBox.click()
                randomBtn = self.driver.find_element_by_css_selector('[data="' + self.selectedMap + '"]')
                randomBtn.click()
            except:
                pass
            ban = False
            if self.user_count == 1:
                ban = True
            elif self.user_count == 2:
                for username in self.user_in_room:
                    if self.user_remain_win_time.get(username, self.default_user_remain_win_time) <= 0:
                        ban = True
                        break
            try:
                if self.isAutoReady and self.driver.find_element_by_id('ready').get_attribute(
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
