import random
import re
from time import sleep
import time
from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.common.keys import Keys
import datetime
from tencentcloud.common import credential
from tencentcloud.common.profile.client_profile import ClientProfile
from tencentcloud.common.profile.http_profile import HttpProfile
from tencentcloud.common.exception.tencent_cloud_sdk_exception import TencentCloudSDKException
from tencentcloud.ocr.v20181119 import ocr_client, models
import base64
import threading

from map import *
from database import *
import api


def reFindMatch(r, t):
    ans = []
    while True:
        tmp = re.search(r, t)
        if tmp:
            g = tmp.group()
            ans.append(g)
            t = t[t.find(g) + 1:]
        else:
            break
    return ans


class Bot(object):

    def __init__(self):
        self.kanaLink = "https://kana.byha.top:444/"

        config = json.load(open("config.json", 'r'))

        self.username = config['username']  # 用户名
        self.password = config['password']  # 密码
        self.roomId = config['roomID']  # 房间号
        self.isSecret = False
        self.isAutoReady = True
        self.mp = Map()  # 地图
        self.data = DataBase('data.json')  # 数据库
        self.battleData = DataBase('battle.json')
        self.isAutoSave = False
        self.selectedMap = '1'
        self.ondefend = False
        self.controller = config['controller']
        self.secretId = config['secretId']
        self.secretKey = config['secretKey']
        self.userCount = 2
        self.colortousername = {}

        self.commands = {'help (command)': '查看命令列表（或命令command的用法）',
                         'query (i)': '查询自己（或玩家i）的用户信息（或查询Bot房回放i的对局信息）',
                         'stats (i)': '获取自己（或玩家i）的统计数据', 'recent (i) [pos]': '查询自己（或玩家i）的最近第pos个Bot房回放'}
        self.aToB = {'help': 'help (command)', 'query': 'query (i)',
                     'stats': 'stats (i)', 'recent': 'recent (i) [pos]'}
        self.tips = [r'在<a href="/post/16903">/post/16903</a>查看统计数据']
        tmp = list(self.commands.keys())
        for x in tmp:
            self.tips.append('命令' + x + ': ' + self.commands[x])

    def SendKeyToTable(self, key):
        ac = ActionChains(self.driver)
        ac.send_keys(key).perform()

    def EnterRoom(self):  # 进入房间
        self.driver.get(
            "https://kana.byha.top:444/checkmate/room/" + self.roomId)
        if self.isSecret:
            settingBtn = self.driver.find_element_by_class_name(
                "form-check-input")
            ac = ActionChains(self.driver)
            ac.click(settingBtn).perform()
        print("Bot已就位！")
        self.url = self.driver.current_url

    def GetMap(self):  # 获得地图
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
        if not (self.mp.size == 9 or self.mp.size == 10 or self.mp.size == 19 or self.mp.size == 20):
            return
        if len(self.colortousername) > 0:
            c = list(self.colortousername.keys())
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
                elif p.find(" mountain ") != -1 or p.find(" obstacle ") != -1 or p.find(" gas ") != -1:
                    self.mp.mp[i][j].type = 'mountain'
                elif p.find(" null ") != -1 and p.find(" grey ") == -1:
                    self.mp.mp[i][j].type = 'land'
                elif p.find(" null ") != -1 and p.find(" grey ") != -1:
                    self.mp.mp[i][j].type = 'empty'
                else:
                    self.mp.mp[i][j].type = 'unknown'
                if p.find(" own ") != -1:
                    self.mp.mp[i][j].belong = 1
                elif self.mp.mp[i][j].type == 'land' or self.mp.mp[i][j].type == 'general' or self.mp.mp[i][
                    j].type == 'city' and len(self.colortousername) > 0:
                    for k in c:
                        if p.find(' ' + k + ' ') != -1:
                            self.mp.mp[i][j].belong = self.colortousername[k]
                            break
                if self.mp.mp[i][j].belong == 0:
                    self.mp.mp[i][j].belong = 'undefined'
                p = stmp[0]
                stmp.pop(0)
                try:
                    self.mp.mp[i][j].tmp = int(p)
                except:
                    self.mp.mp[i][j].tmp = 0
        return

    def GetMessage(self):  # 获取消息
        try:
            s = self.driver.find_element_by_id("msg-container").get_attribute("innerHTML")
        except:
            self.EnterRoom()
            return
        self.msg = []
        while True:
            tmp = re.search(r'<p>[\s\S]*?</p>', s)
            if tmp:
                g = tmp.group()
                g = re.sub(r'&nbsp;', '', g)
                g = g[3:len(g) - 4]
                p = g.find(':')
                self.msg.append([g[0:p], g[p + 2:len(g)]])
                p = s.find(g)
                s = s[p + len(g):len(s)]
            else:
                break
        return

    def SelectLand(self, x, y):  # 选择土地
        try:
            self.driver.find_element_by_id(
                "td-" + str((x - 1) * self.mp.size + y)).click()
            self.curx = x
            self.cury = y
            return
        except:
            return

    def MsgPattern(self, data):
        ans = ''
        for i in data:
            ans += i[0] + ':' + str(i[1]) + '<br>'
        return ans

    def updateRate(self, curuser):
        battle = self.data.getByKey(curuser, 'battle')
        if battle == 0:
            return
        stats = [[0, 0] for _ in range(10)]
        for i in battle:
            stats[self.battleData.getByKey(i, 'playercount')][0] += 1
            if self.battleData.getByKey(i, 'winner') == curuser:
                stats[self.battleData.getByKey(i, 'playercount')][1] += 1
        for i in range(2, 9):
            if stats[i][0] == 0:
                stats[i].append(0.0)
            else:
                stats[i].append(round(stats[i][1] / stats[i][0] * 100.0, 1))
        self.data.setByKey(curuser, stats, 'rate')
        return

    def CommandLine(self):  # 命令行
        while True:
            sleep(0.3)
            if not self.On:
                return
            self.GetMessage()
            cur = self.msg[len(self.msg) - 1]
            tmp = ['']
            tot = 0
            for i in range(0, len(cur[1])):
                if cur[1][i] == ' ' and (i == 0 or cur[1][i - 1] != ' '):
                    tot += 1
                    tmp.append('')
                elif cur[1][i] != ' ':
                    tmp[tot] += cur[1][i]
            if tmp[0] in list(self.aToB.keys()) and self.data.getByKey(cur[0], 'ban') > 0:
                self.sendMessage('您已被封禁，剩余' + str(self.data.getByKey(cur[0], 'ban')) + '天')
                continue
            if tmp[0] == 'help':
                if tot == 0:
                    msg = '<strong>命令列表：</strong><br>'
                    tmp = list(self.aToB.keys())
                    for x in tmp:
                        msg += x + ', '
                    self.sendMessage(msg)
                    self.sendMessage('提示：输入help [command]以查询命令command的用法')
                elif tot == 1:
                    try:
                        x = self.aToB[tmp[1]]
                        self.sendMessage('命令' + x + ': ' + self.commands[x])
                    except:
                        self.sendMessage('未找到该命令')
                else:
                    self.sendMessage('需要0或1个参数，发现' + str(tot) + '个')
            if tmp[0] == 'query':
                uname = ''
                if tot != 0 and tot != 1:
                    self.sendMessage('需要0或1个参数，发现' + str(tot) + '个')
                elif tot == 0:
                    uname = cur[0]
                elif tot == 1:
                    uname = tmp[1]
                if uname in self.battleData.getItemList():
                    self.sendMessage('<br>' + self.MsgPattern([['人数', self.battleData.getByKey(uname, 'playercount')],
                                                               ['赢家', self.battleData.getByKey(uname, 'winner')],
                                                               ['回放距今时间(s)', int(
                                                                   time.time() - self.battleData.getByKey(uname,
                                                                                                          'time'))]]))
                elif uname != '':
                    self.sendMessage('<br>' + self.MsgPattern([['单挑胜利次数', self.data.getByKey(uname, 'wintime')],
                                                               ['剩余封禁天数', self.data.getByKey(uname, 'ban')]]))
            if tmp[0] == 'stats':
                if tot == 0:
                    curuser = cur[0]
                elif tot == 1:
                    curuser = tmp[1]
                else:
                    self.sendMessage('需要0或1个参数，发现' + str(tot) + '个')
                    continue
                self.updateRate(curuser)
                stats = self.data.getByKey(curuser, 'rate')
                if stats == 0:
                    self.sendMessage('No data')
                    continue
                ans = '<br>'
                for i in range(2, 9):
                    ans += str(i) + '人局：' + str(stats[i][0]) + '场， 胜率' + str(stats[i][2]) + '%<br>'
                self.sendMessage(ans)
            if tmp[0] == 'recent':
                if tot == 1:
                    curuser = cur[0]
                    pos = tmp[1]
                elif tot == 2:
                    curuser = tmp[1]
                    pos = tmp[2]
                else:
                    self.sendMessage('需要1或2个参数，发现' + str(tot) + '个')
                    continue
                battle = self.data.getByKey(curuser, 'battle')
                try:
                    pos = int(pos)
                except:
                    self.sendMessage('参数应为整数')
                else:
                    if pos < 1 or pos > len(battle):
                        self.sendMessage('参数不在范围内')
                    else:
                        url = battle[len(battle) - pos]
                        self.sendMessage(r'<a href="/checkmate/replay/' + url + r'">回放</a>')

            if tmp[0] == 'kill':
                if cur[0] == self.controller:
                    self.driver.close()
                    del self
                else:
                    self.sendMessage('权限不足')
            if tmp[0] == 'enter':
                if cur[0] == self.controller:
                    self.roomId = tmp[1]
                    self.EnterRoom()
                else:
                    self.sendMessage('权限不足')
            if tmp[0] == 'setsecret':
                if cur[0] == self.controller:
                    self.isSecret = not self.isSecret
                    self.sendMessage('secret = ' + str(self.isSecret))
                else:
                    self.sendMessage('权限不足')
            if tmp[0] == 'savedata':
                if cur[0] == self.controller:
                    self.data.saveData()
                    self.battleData.saveData()
                    self.sendMessage('saved')
                else:
                    self.sendMessage('权限不足')
            if tmp[0] == 'readdata':
                if cur[0] == self.controller:
                    try:
                        self.data.readData()
                        self.battleData.readData()
                        self.sendMessage('read')
                    except:
                        self.sendMessage('error')
                else:
                    self.sendMessage('权限不足')
            if tmp[0] == 'setdata':
                if cur[0] == self.controller:
                    self.data.setByKey(tmp[1], int(tmp[3]), tmp[2])
                    self.sendMessage(tmp[2] + ' = ' + tmp[3])
                else:
                    self.sendMessage('权限不足')
            if tmp[0] == 'exec':
                if cur[0] == self.controller:
                    exec(cur[1])
                    self.sendMessage('完成')
                else:
                    self.sendMessage('权限不足')
        return

    def Logout(self):  # 登出
        print('正在登出…')
        self.driver.get('https://kana.byha.top:444/logout')
        self.driver.switch_to.default_content()
        sleep(5)
        self.driver.find_element_by_id('submitButton').click()
        return

    def delNode(self, a):
        self.driver.execute_script("""
                                   var element = arguments[0];
                                     element.parentNode.removeChild(element);
                                     """, a)
        return

    def Login(self):  # 登录
        print("正在登录…")
        self.driver.get(self.kanaLink)
        usernameBox = self.driver.find_element_by_name("username")
        passwordBox = self.driver.find_element_by_name("pwd")

        ac = ActionChains(self.driver)
        ac.send_keys_to_element(usernameBox, self.username)
        ac.send_keys_to_element(passwordBox, self.password).perform()
        # self.delNode(self.driver.find_element_by_css_selector('[rel="stylesheet"]'))
        while True:
            if self.driver.current_url == self.kanaLink:
                break
            self.driver.execute_script('document.getElementById("cap").childNodes[1].style.width="150%"')
            frame = self.driver.find_element_by_xpath('/html/body/div[2]/div/form/div[1]/object')
            self.driver.switch_to.frame(frame)
            try:
                a = self.driver.find_element_by_css_selector('[fill="none"]')
                self.delNode(a)
            except:
                sleep(1)
                continue

            self.driver.switch_to.default_content()

            cap = -1
            self.driver.get_screenshot_as_file('a.png')

            try:
                cred = credential.Credential(self.secretId, self.secretKey)
                httpProfile = HttpProfile()
                httpProfile.endpoint = "ocr.tencentcloudapi.com"

                clientProfile = ClientProfile()
                clientProfile.httpProfile = httpProfile
                client = ocr_client.OcrClient(cred, "ap-shanghai", clientProfile)

                req = models.GeneralBasicOCRRequest()
                params = {
                    "ImageBase64": base64.b64encode(open('a.png', 'rb').read()).decode()
                }
                req.from_json_string(json.dumps(params))

                resp = client.GeneralBasicOCR(req)
                a = json.loads(resp.to_json_string())

            except TencentCloudSDKException as err:
                print(err)
            for i in a['TextDetections']:
                tmp = i['DetectedText']
                s = ''
                for j in tmp:
                    if j != '(' and j != ')':  # 去除诡异括号
                        s += j
                tmp = s
                if re.match(r'\w\w\w\w', tmp) and len(tmp) == 4:
                    cap = tmp
                    break
            print(cap)
            ac = ActionChains(self.driver)
            ac.send_keys_to_element(self.driver.find_element_by_name("cap"), cap).perform()
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
        self.SendKeyToTable(self.movements[0])
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
        self.GetMap()
        self.updateMap()
        trytime = 0
        while self.mp.mp[self.homex][self.homey].tmp == tmp and trytime <= 80:
            self.GetMap()
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

        self.colortousername = {}
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
            self.colortousername[color] = username
        return 0

    def sendMessage(self, msg):  # 发送消息
        if len(msg) > 95:
            self.sendMessage(msg[0:95])
            self.sendMessage(msg[95:len(msg)])
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
        self.GetMap()
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
            self.SelectLand(mx[0], mx[1])
            tmp = random.choice(self.homes)
            self.moveTo(tmp[0], tmp[1])
            return
        tmp = self.mp.findMatchByRange(self.homex, self.homey, 1,
                                       lambda a: a.belong != 1 and (a.type == 'land' or a.type == 'city'))
        if tmp and self.mp.mp[mx[0]][mx[1]].tmp > 30:  # 智能守家
            mx = self.mp.findMax(lambda a: a.type != 'general' and a.belong == 1)
            self.SelectLand(mx[0], mx[1])
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
                self.SendKeyToTable('Z')
            self.SelectLand(ans[0], ans[1])
            self.moveTo(target[0], target[1])
        return

    def updateData(self):  # 每日一次
        uname = self.data.getItemList()
        for i in uname:
            wintime = self.data.getByKey(i, 'wintime')
            ban = self.data.getByKey(i, 'ban')
            if wintime > 0:
                self.data.setByKey(i, 0, 'wintime')
            if ban > 0:
                self.data.addByKey(i, -1, 'ban')
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
            return self.userinroom
        else:
            return uname

    def detectUserInRoom(self):
        self.userinroom = []
        while True:
            tmp = self.userinroom
            sleep(0.5)
            if not self.On:
                return
            self.userinroom = self.getUserInRoom()
            for i in tmp:
                if i not in self.userinroom:
                    self.sendMessage(i + '离开了房间')
            for i in self.userinroom:
                if i not in tmp:
                    self.sendMessage(i + '进入了房间')
        return

    def addBattle(self, winner):
        k = reFindMatch(r'ay/[\s\S]*?"', api.GetBattleByPage(1))[0]
        url = k[3:len(k) - 1]
        user = []
        tmp = list(self.colortousername.keys())
        for i in tmp:
            user.append(self.colortousername[i])
        for i in user:
            self.data.appendByKey(i, url, 'battle')
        self.battleData.setByKey(url, time.time(), 'time')
        self.battleData.setByKey(url, len(user), 'playercount')
        self.battleData.setByKey(url, winner, 'winner')
        return

    def Analyze(self):  # 数据分析，每日一次
        analyzeData = DataBase('analyze.json')
        uid = 1
        maxuid = 1
        while True:
            info = api.GetUserInfoByUid(uid)
            if info == '数据库错误':
                if uid <= 3800:
                    uid += 1
                    continue
                else:
                    break
            exp = api.GetUserExpByUid(uid)
            analyzeData.setByKey(uid, info, 'info')
            analyzeData.setByKey(uid, exp, 'exp')
            maxuid = uid
            uid += 1
        analyzeData.saveData()
        ans = ''
        curTime = datetime.datetime.now()
        ans += '更新于' + str(curTime.year) + '.' + str(curTime.month) + '.' + str(curTime.day) + ',' + str(
            curTime.hour) + ':' + str(curTime.minute) + ':' + str(curTime.second) + '\n\n'
        tmp = analyzeData.getItemList()
        for i in range(len(tmp)):
            tmp[i] = int(tmp[i])
        tot = 0
        for uid in tmp:
            if uid != 1:
                tot += int(analyzeData.getByKey(uid, 'exp'))
        ans += '### 经验值分布统计（排除admin）\n\n'
        ans += '用户经验总和：' + str(tot) + '\n\n'
        role = lambda a: a[1]
        k = []
        for i in range(1, maxuid // 1000 + 2):
            l = max((i - 1) * 1000 + 1, 2)
            r = min(i * 1000, maxuid)
            if l > maxuid:
                break
            tot = 0
            maxexp = 0
            maxuser = 'undefined'
            for j in range(l, r + 1):
                if j in tmp:
                    exp = int(analyzeData.getByKey(j, 'exp'))
                    uname = analyzeData.getByKey(j, 'info')['username']
                    tot += exp
                    k.append([uname, exp])
                    if exp > maxexp:
                        maxuser = uname
                        maxexp = exp
            ans += str(l) + '~' + str(r) + '总和：' + str(tot) + '，最大值' + maxuser + '（' + str(maxexp) + '经验）\n\n'
        k.sort(key=role, reverse=True)
        ans += '经验排行榜前50名：\n\n'
        for i in range(50):
            ans += '#' + str(i + 1) + '：' + k[i][0] + '，' + str(k[i][1]) + '经验\n\n'
        tmp = self.data.getItemList()
        k = [[] for _ in range(10)]
        ans += '### 对局胜率统计 [参战>=20局且(6级或有B站认证)才可上榜]\n\n'
        for curuser in tmp:
            self.updateRate(curuser)
            stats = self.data.getByKey(curuser, 'rate')
            if stats == 0:
                continue
            for i in range(3, 9):
                if stats[i][0] >= 20:
                    uid = api.GetUidByUsername(curuser)
                    if analyzeData.getByKey(uid, 'info')['bili_uid'] != 0 or api.GetUserLevelByExp(
                            analyzeData.getByKey(uid, 'exp')) == 6:
                        k[i].append([curuser, stats[i][2]])
        role = lambda a: a[1]
        for i in range(3, 9):
            k[i].sort(key=role, reverse=True)
            ans += str(i) + '人局胜率排行榜前5名：\n\n'
            for j in range(min(5, len(k[i]))):
                ans += '#' + str(j + 1) + '：' + k[i][j][0] + '，胜率' + str(k[i][j][1]) + '%\n\n'
        ans += '### 今日数据\n\n'
        battle = self.battleData.getItemList()
        cnt = [0 for _ in range(10)]
        for j in range(len(battle) - 1, -1, -1):
            curbattle = battle[j]
            if time.time() - int(self.battleData.getByKey(curbattle, 'time')) >= 86400:
                break
            cnt[int(self.battleData.getByKey(curbattle, 'playercount'))] += 1
        for i in range(2, 9):
            ans += str(i) + '人局，' + str(cnt[i]) + '场\n\n'
        api.UpdatePost(16903, ans)
        return

    def Main(self):
        self.driver = webdriver.Chrome()  # 浏览器
        # self.driver = webdriver.Firefox()
        self.Login()
        self.EnterRoom()
        self.On = True
        self.table = self.driver.find_element_by_tag_name("tbody")
        flag = False
        ban = False
        try:
            self.data.readData()
            self.battleData.readData()
        except:
            pass
        freetime = 0
        tmp = self.driver.get_cookies()
        for i in tmp:
            if i['name'] == 'client_session':
                api.cookie = 'client_session=' + i['value']
                break
        print(api.cookie)
        threading.Thread(target=self.CommandLine, name="command").start()
        threading.Thread(target=self.detectUserInRoom, name="detect").start()
        while True:
            curTime = datetime.datetime.now()
            if curTime.hour not in range(8, 23):
                self.On = False
                self.updateData()
                self.driver.get('https://kana.byha.top:444/')
                self.Analyze()
                self.data.saveData()
                self.battleData.saveData()
                self.Logout()
                self.driver.close()
                return
            if self.driver.current_url != self.url:
                self.EnterRoom()
                sleep(10)
                continue
            ac = ActionChains(self.driver)
            ac.send_keys(Keys.CONTROL).perform()  # 防踢
            try:
                if self.driver.find_element_by_id("game-status").get_attribute('innerHTML') != "游戏中":
                    if flag:
                        flag = False
                    sleep(0.2)
                    self.ispre = False
                else:
                    freetime = 0
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
            freetime += 1
            if freetime % 480 == 10 and not self.isSecret:
                self.sendMessage("【提示】" + random.choice(self.tips))
            try:
                tmp = self.driver.find_element_by_id("swal2-content").get_attribute('innerText')
                tmp = tmp[0:tmp.find("赢了")]
                if tmp != '':
                    ac = ActionChains(self.driver)
                    ac.send_keys(Keys.ENTER).perform()
                    if self.data.getByKey(tmp, 'ban') > 0 and self.mp.size in [9, 10]:
                        self.sendMessage('您已被封禁，剩余' + str(self.data.getByKey(tmp, 'ban')) + '天')
                    elif tmp != self.username and self.mp.size in [9, 10]:
                        self.data.addByKey(tmp, 1, 'wintime')
                        if self.data.getByKey(tmp, 'wintime') > 30:
                            self.data.setByKey(tmp, 7, 'ban')
                            self.sendMessage('您已被封禁，剩余' + str(self.data.getByKey(tmp, 'ban')) + '天')
                        else:
                            self.sendMessage('您已单挑' + str(self.data.getByKey(tmp, 'wintime')) + '次')
                    self.addBattle(tmp)
                    self.data.saveData()
                    self.battleData.saveData()
            except:
                pass
            try:
                checkBox = self.driver.find_element_by_class_name("form-check-input")  # 防私密
                if (checkBox.is_selected() and not self.isSecret) or (not (checkBox.is_selected()) and self.isSecret):
                    checkBox.click()
                randomBtn = self.driver.find_element_by_css_selector('[data="' + self.selectedMap + '"]')
                randomBtn.click()
            except:
                pass
            ban = False
            if self.userCount == 1:
                ban = True
            elif self.userCount == 2:
                for i in self.userinroom:
                    if self.data.getByKey(i, 'ban') > 0:
                        ban = True
                        break
            try:
                if self.isAutoReady and self.driver.find_element_by_id("ready").get_attribute(
                        'innerHTML') == "准备" and not ban:
                    ac = ActionChains(self.driver)
                    ac.click(self.driver.find_element_by_id("ready")).perform()
                if self.driver.find_element_by_id("ready").get_attribute(
                        'innerHTML') == "取消准备" and ban:
                    ac = ActionChains(self.driver)
                    ac.click(self.driver.find_element_by_id("ready")).perform()
            except:
                pass
            try:
                self.userCount = int(self.driver.find_element_by_id("total-user").text)
            except:
                pass
        return


a = Bot()
while True:
    curTime = datetime.datetime.now()
    if curTime.hour in range(8, 23):
        a.Main()
    sleep(60)
