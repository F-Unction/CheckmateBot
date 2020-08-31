import random
import re
import threading
import time
import copy
from time import sleep

from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait


class Bot(object):
    """
    https://kana.byha.top:444/post/6735
    https://www.luogu.com.cn/paste/nbyi7ds9
    """

    def __init__(self, username, password, roomId, isSecret=False, isAutoReady=True):
        self.kanaLink = "https://kana.byha.top:444/"
        self.driver = webdriver.Chrome()    # 浏览器
        # self.driver = webdriver.Firefox()
        self.username = username    # 用户名
        self.password = password    # 密码
        self.roomId = roomId    # 房间号
        self.isSecret = isSecret    # 是否为私密房间
        self.isAutoReady = isAutoReady    # 是否主动准备
        self.mpType = [[0 for i in range(25)] for j in range(25)]  # 属性地图
        self.mpTmp = [[0 for i in range(25)] for j in range(25)]  # 兵力地图
        self.mpBelong = [[0 for i in range(25)] for j in range(25)]  # 颜色地图
        self.di = [[-1, 0], [0, 1], [1, 0], [0, -1]]  # 方向
        self.q = []
        self.error = False
        self.vis = [[False for i in range(25)] for j in range(25)]  # 是否走过
        self.sx = self.sy = 0  # 家的位置
        self.homes = []  # 敌人的家
        self.size = 20
        self.tmpQ = []
        self.tmpVis = [[False for i in range(25)] for j in range(25)]
        self.route = []  # 进攻路线
        self.endTag = False
        self.ansLen = 100000

    def SendKeyToTable(self, key):
        ac = ActionChains(self.driver)
        ac.send_keys(key).perform()

    # https://blog.csdn.net/weixin_42107267/article/details/93198343
    def isElementExist(self, element):
        try:
            self.driver.find_element_by_id(element)
            return True

        except:
            return False

    def getMap(self):  # 获得地图
        self.mpType = [[0 for i in range(25)] for j in range(25)]
        self.mpTmp = [[0 for i in range(25)] for j in range(25)]
        self.mpBelong = [[0 for i in range(25)] for j in range(25)]
        s = self.driver.find_element_by_id("m").get_attribute("innerHTML")
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
        self.size = int(cnt ** 0.5)
        if not(self.size == 9 or self.size == 10 or self.size == 19 or self.size == 20):
            return
        for i in range(self.size):
            for j in range(self.size):
                p = stype[0]
                stype.pop(0)
                if p.find(" city ") != -1 or p.find(" empty-city ") != -1:
                    self.mpType[i + 1][j + 1] = 5
                elif p.find(" crown ") != -1:
                    self.mpType[i + 1][j + 1] = 2
                elif p.find(" mountain ") != -1 or p.find(" obstacle ") != -1:
                    self.mpType[i + 1][j + 1] = 1
                elif p.find(" gas ") != -1:
                    self.mpType[i + 1][j + 1] = 1
                elif p.find(" null ") != -1 and p.find(" grey ") != -1:
                    self.mpType[i + 1][j + 1] = 0
                elif p.find(" null ") != -1 and p.find(" grey ") == -1:
                    self.mpType[i + 1][j + 1] = 3
                else:
                    self.mpType[i + 1][j + 1] = -1
                if p.find(" own ") != -1:
                    self.mpBelong[i + 1][j + 1] = 1
                else:
                    self.mpBelong[i + 1][j + 1] = 2
                p = stmp[0]
                stmp.pop(0)
                try:
                    self.mpTmp[i + 1][j + 1] = int(p)
                except:
                    self.mpTmp[i + 1][j + 1] = 0
                # print(self.mpType[i + 1][j + 1])
                # print(self.mpBelong[i + 1][j + 1])
                # print(self.mpTmp[i + 1][j + 1])
        return

    def selectLand(self, x, y):  # 选择土地
        try:
            self.driver.find_element_by_id(
                "td-" + str((x - 1) * self.size + y)).click()
            return
        except:
            return

    def Login(self):
        """
            登录，如果出现异常则在5S后退出
            :return:
        """
        print("正在登录…")
        self.driver.get(self.kanaLink)
        usernameBox = self.driver.find_element_by_name("username")
        passwordBox = self.driver.find_element_by_name("pwd")
        ac = ActionChains(self.driver)

        # 输入账号密码并登录
        ac.send_keys_to_element(usernameBox, self.username)
        ac.send_keys_to_element(passwordBox, self.password)
        sleep(10)  # 等待用户手动输入验证码
        ac.click(self.driver.find_element_by_id("submitButton")).perform()

        try:
            WebDriverWait(self.driver, 8).until(EC.url_to_be(self.kanaLink))
            print("登录成功！")
        except TimeoutException:
            print("网络连接出现问题或账密错误！\n程序将在5秒后退出")
            sleep(5)
            self.driver.close()
            del self

    def EnterRoom(self):
        """
        进入指定房间
        :return:
        """
        self.driver.get(
            "https://kana.byha.top:444/checkmate/room/" + self.roomId)
        if self.isSecret:
            settingBtn = self.driver.find_element_by_class_name(
                "form-check-input")
            ac = ActionChains(self.driver)
            ac.click(settingBtn).perform()
        print("Bot已就位！")

    def Ready(self):
        """
        准备开始，如果300秒未开始，程序退出
        :return:
        """
        # sleep(1)
        try:
            self.userCount = int(
                self.driver.find_element_by_id("total-user").text)
        except ValueError:
            self.userCount = 3
        ac = ActionChains(self.driver)
        ac.click(self.driver.find_element_by_id("ready")).perform()

        try:
            WebDriverWait(self.driver, 300).until(
                EC.visibility_of_element_located((By.TAG_NAME, "tbody")))
        except TimeoutException:
            print("房间内无人开始，过一会再试试吧")
            sleep(5)
            self.Kill()

    def Kill(self):
        self.driver.close()
        del self

    def Pr(self, c):
        self.SendKeyToTable(c)
        # print(c)
        return

    def isOutside(self, x, y):
        for i in range(4):
            px = x + self.di[i][0]
            py = y + self.di[i][1]
            if px >= 1 and px <= self.size and py >= 1 and py <= self.size and self.mpBelong[px][py] == 2:
                return True
        return False

    def changeTarget(self):
        insideAnsTmp = self.mpTmp[self.sx][self.sy]
        insideAnsX = self.sx
        insideAnsY = self.sy
        outsideAnsTmp = 0
        outsideAnsX = 0
        outsideAnsY = 0
        for p in range(self.size):
            for q in range(self.size):
                i = p + 1
                j = q + 1
                if self.mpBelong[i][j] == 1:
                    if self.isOutside(i, j):
                        if self.mpTmp[i][j] > outsideAnsTmp:
                            outsideAnsTmp = self.mpTmp[i][j]
                            outsideAnsX = i
                            outsideAnsY = j
                    else:
                        if self.mpTmp[i][j] > insideAnsTmp:
                            insideAnsTmp = self.mpTmp[i][j]
                            insideAnsX = i
                            insideAnsY = j
        if outsideAnsTmp * 5 >= insideAnsTmp:
            self.sx = outsideAnsX
            self.sy = outsideAnsY
        else:
            self.sx = insideAnsX
            self.sy = insideAnsY
        self.q.append([self.sx, self.sy])
        if random.randint(0, 1) == 1:
            self.vis = [[False for i in range(25)] for j in range(25)]
        self.vis[self.sx][self.sy] = True
        self.selectLand(self.sx, self.sy)
        return

    def dfsRoute(self, x, y, ex, ey, cnt):
        if x == ex and y == ey and cnt < self.ansLen:
            self.ansLen = cnt
            self.route = copy.deepcopy(self.tmpQ)
            # print("finished")
            # print(self.tmpQ)
            # print(cnt)
            return
        if cnt >= self.ansLen:
            return
        tmpI = [0, 1, 2, 3]
        random.shuffle(tmpI)
        for i in tmpI:
            if self.endTag:
                return
            px = x + self.di[i][0]
            py = y + self.di[i][1]
            if px >= 1 and px <= self.size and py >= 1 and py <= self.size and (not self.tmpVis[px][py]) and self.mpType[px][py] != 1:
                self.tmpVis[px][py] = True
                self.tmpQ.append([i, x, y])
                #print(i, x, y)
                self.dfsRoute(px, py, ex, ey, cnt + 1)
                self.tmpQ.remove([i, x, y])
                if random.randint(0, 10) >= 2:
                    self.tmpVis[px][py] = False
        return

    def Attack(self, x, y, ex, ey):
        self.tmpQ = copy.deepcopy([])
        self.route = []
        self.endTag = False
        self.tmpVis = [[False for i in range(25)] for j in range(25)]
        self.tmpVis[x][y] = True
        self.ansLen = 10000
        #print("attack, ", ex, ey)
        self.dfsRoute(x, y, ex, ey, 0)
        #print(self.route, self.ansLen)
        if len(self.route) < 1:
            return
        for p in self.route:
            i = p[0]
            self.getMap()
            if x < 1 or y < 1 or x > self.size or y > self.size or self.mpBelong[x][y] == 2 or self.mpTmp[x][y] < 2:
                return
            if i == 0:
                self.Pr('W')
                x -= 1
            elif i == 1:
                self.Pr('D')
                y += 1
            elif i == 2:
                self.Pr('S')
                x += 1
            else:
                self.Pr('A')
                y -= 1
            sleep(0.25)
        return

    def botMove(self):
        sleep(0.25)
        x = 0
        y = 0
        tryTime = 0
        self.getMap()
        while True:
            if len(self.q) == 0:
                self.changeTarget()
            x = self.q[0][0]
            y = self.q[0][1]
            tryTime += 1
            self.q.pop(0)
            if not(self.mpTmp[x][y] <= 1 and self.mpType[x][y] != 2 and tryTime <= 10):
                break
        if tryTime > 10:
            return
        if self.mpTmp[x][y] <= 1:
            return
        if self.mpBelong[x][y] == 2:
            return
        if self.mpType[x][y] == 2 and self.mpBelong[x][y] == 1:
            self.Pr('Z')
        for i in range(self.size):
            for j in range(self.size):
                if self.mpType[i + 1][j + 1] == 2 and self.mpBelong[i + 1][j + 1] == 2 and (not ([i + 1, j + 1] in self.homes)):
                    self.homes.append([i + 1, j + 1])
        if [x, y] in self.homes:
            self.homes.remove([x, y])
        if len(self.homes) > 0 and random.randint(1, 10) == 1 and self.mpTmp[x][y] > 30:
            g = random.randint(0, len(self.homes) - 1)
            self.Attack(x, y, self.homes[g][0], self.homes[g][1])
            return
        ansTmp = 0
        ansI = -1
        tmpI = [0, 1, 2, 3]
        random.shuffle(tmpI)
        for i in tmpI:
            px = x + self.di[i][0]
            py = y + self.di[i][1]
            if px >= 1 and px <= self.size and py >= 1 and py <= self.size and self.mpType[px][py] != 1 and (not self.vis[px][py]) and (self.mpType[px][py] != 5 or self.mpTmp[x][y] > self.mpTmp[px][py]):
                currentTmp = 0
                if self.mpBelong[px][py] == 2:
                    if self.mpType[px][py] == 2:
                        currentTmp = 10
                    elif self.mpType[px][py] == 5:
                        currentTmp = 8
                    elif self.mpType[px][py] == 3:
                        currentTmp = 5
                    else:
                        currentTmp = 3
                else:
                    currentTmp = 1
                if currentTmp > ansTmp:
                    ansTmp = currentTmp
                    ansI = i
        if ansI == -1:
            return
        px = x + self.di[ansI][0]
        py = y + self.di[ansI][1]
        self.vis[px][py] = True
        self.q.append([px, py])
        if ansI == 0:
            self.Pr('W')
        elif ansI == 1:
            self.Pr('D')
        elif ansI == 2:
            self.Pr('S')
        else:
            self.Pr('A')
        self.botMove()
        return

    def Main(self):
        self.Login()
        self.EnterRoom()
        self.table = self.driver.find_element_by_tag_name("tbody")
        while True:
            if self.isAutoReady:
                self.Ready()
            self.Pr('F')  # 防踢
            self.getMap()
            self.sx = 0
            self.sy = 0
            for i in range(self.size):
                for j in range(self.size):
                    if self.mpBelong[i + 1][j + 1] == 1 and self.mpType[i + 1][j + 1] == 2:
                        self.sx = i + 1
                        self.sy = j + 1
            if self.sx == 0 or self.sy == 0:
                continue
            self.changeTarget()
            self.botMove()
        return


print("输入用户名：")
t1 = input()
print("输入密码：")
t2 = input()
print("输入房间号：")
t3 = input()
a = Bot(t1, t2, t3)
a.Main()
