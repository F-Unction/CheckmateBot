import random
import re
from queue import PriorityQueue
from time import sleep

from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait


def dist(xx1, yy1, xx2, yy2):
    return abs(xx1 - xx2) + abs(yy1 - yy2)


dir = [[-1, 0], [0, 1], [1, 0], [0, -1]]


class Node:
    def __init__(self, tmp=0, belong=0, type='land'):
        self.tmp = tmp
        self.belong = belong  # 1 0
        self.type = type  # land city general unknown mountain empty


def distRouteNode(a, b):
    return dist(a[0], a[1], b[0], b[1])


class Map:
    def resize(self, size):
        self.size = size
        self.mp = [[Node() for _ in range(self.size + 1)] for _ in range(self.size + 1)]

    def __init__(self):
        self.resize(20)

    def getNeighbours(self, a):
        tmp = []
        for i in dir:
            px = a[0] + i[0]
            py = a[1] + i[1]
            if 1 <= px <= self.size and 1 <= py <= self.size and self.mp[px][py].type != 'mountain':
                tmp.append((px, py))
        return tmp

    def getCost(self, a):
        if self.mp[a[0]][a[1]].belong == 0:
            return max(self.mp[a[0]][a[1]].tmp // 10, 2)
        else:
            return 1

    def AStar(self, start, goal):  # https://blog.csdn.net/adamshan/article/details/79945175
        frontier = PriorityQueue()
        frontier.put((0, start))
        came_from = {}
        cost_so_far = {}
        came_from[start] = None
        cost_so_far[start] = 0
        while not frontier.empty():
            current = frontier.get()[1]
            if current == goal:
                break
            for next in self.getNeighbours(current):
                new_cost = cost_so_far[current] + self.getCost(next)
                if next not in cost_so_far or new_cost < cost_so_far[next]:
                    cost_so_far[next] = new_cost
                    priority = new_cost + distRouteNode(goal, next)
                    frontier.put((priority, next))
                    came_from[next] = current
        current = goal
        path = []
        while current != start:
            path.append(current)
            current = came_from[current]
        path.append(start)
        path.reverse()
        return path

    def findPath(self, sx, sy, ex, ey):
        if self.mp[sx][sy].type == 'mountain' or self.mp[ex][ey].type == 'mountain':
            return []
        path = self.AStar((sx, sy), (ex, ey))
        return path

    def findMatch(self, flt):
        tmp = []
        for i in range(1, self.size):
            for j in range(1, self.size):
                if flt(self.mp[i][j]):
                    tmp.append([i, j])
        return tmp

    def findMatchByRange(self, x, y, rg, flt):
        tmp = []
        for i in range(x - rg, x + rg + 1):
            for j in range(y - rg, y + rg + 1):
                if 1 <= i <= self.size and 1 <= j <= self.size and flt(self.mp[i][j]):
                    tmp.append([i, j])
        return tmp

    def getOwnedMax(self):
        maxx = 0
        ansx = 0
        ansy = 0
        for i in range(1, self.size + 1):
            for j in range(1, self.size + 1):
                if self.mp[i][j].belong == 1 and self.mp[i][j].tmp > maxx:
                    maxx = self.mp[i][j].tmp
                    ansx = i
                    ansy = j
        return [ansx, ansy]


class Bot(object):

    def __init__(self, username, password, roomId, isSecret, isAutoReady=True):
        self.kanaLink = "https://kana.byha.top:444/"
        self.driver = webdriver.Chrome()  # 浏览器
        # self.driver = webver.Firefox()
        self.username = username  # 用户名
        self.password = password  # 密码
        self.roomId = roomId  # 房间号
        self.isSecret = isSecret  # 是否为私密房间
        self.isAutoReady = isAutoReady  # 是否主动准备
        self.mp = Map()
        self.selectedMap = '1'

    def SendKeyToTable(self, key):
        ac = ActionChains(self.driver)
        ac.send_keys(key).perform()

    def EnterRoom(self):
        self.driver.get(
            "https://kana.byha.top:444/checkmate/room/" + self.roomId)
        if self.isSecret:
            settingBtn = self.driver.find_element_by_class_name(
                "form-check-input")
            ac = ActionChains(self.driver)
            ac.click(settingBtn).perform()
        print("Bot已就位！")

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
        for i in range(1, self.mp.size + 1):
            for j in range(1, self.mp.size + 1):
                p = stype[0]
                stype.pop(0)
                if p.find(" city ") != -1 or p.find(" empty-city ") != -1:
                    self.mp.mp[i][j].type = 'city'
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
                else:
                    self.mp.mp[i][j].belong = 0
                p = stmp[0]
                stmp.pop(0)
                try:
                    self.mp.mp[i][j].tmp = int(p)
                except:
                    self.mp.mp[i][j].tmp = 0
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

    def Login(self):
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

    def moveTo(self, x, y):
        path = self.mp.findPath(self.curx, self.cury, x, y)
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

    def flushMovements(self):
        tmp = self.mp.mp[self.homex][self.homey].tmp
        self.SendKeyToTable(self.movements[0])
        if self.mp.mp[self.curx][self.cury].belong == 0:
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
        while self.mp.mp[self.homex][self.homey].tmp == tmp and trytime <= 100:
            self.GetMap()
            trytime += 1
        return

    def pre(self):
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
        self.ispre = True
        return 0

    def updateMap(self):
        tmp = self.mp.findMatch(lambda a: a.type == 'general' and a.belong == 0)
        if tmp:
            for i in tmp:
                if i not in self.homes:
                    self.homes.append(i)
        tmp = self.mp.findMatch(lambda a: a.type != 'unknown')
        for i in tmp:
            if i not in self.vis:
                self.vis.append(i)
        return

    def botMove(self):
        self.GetMap()
        if not self.ispre:
            if self.pre() == 1:
                return
        if self.movements:
            self.flushMovements()
            return
        if [self.curx, self.cury] in self.homes and self.mp.mp[self.curx][self.cury].belong == 1:
            self.homes.remove([self.curx, self.cury])
        if [self.curx, self.cury] not in self.vis:
            self.vis.append([self.curx, self.cury])
        self.updateMap()
        mx = self.mp.getOwnedMax()
        if self.mp.mp[mx[0]][mx[1]].tmp <= 5:
            return
        if self.homes:
            self.SelectLand(mx[0], mx[1])
            tmp = random.choice(self.homes)
            self.moveTo(tmp[0], tmp[1])
            return
        tmp = self.mp.findMatch(lambda a: a.type == 'unknown')
        random.shuffle(tmp)
        role = lambda a: len(self.mp.findMatchByRange(a[0], a[1], 4, lambda b: b.type == 'land' and b.belong == 0))
        tmp.sort(key=role, reverse=True)
        for i in tmp:
            if [i[0], i[1]] not in self.vis:
                target = i
                break
        owned = self.mp.findMatch(lambda a: a.belong == 1)
        random.shuffle(owned)
        mindist = 10000
        ans = []
        for i in owned:
            p = dist(i[0], i[1], target[0], target[1])
            if p < self.mp.mp[i[0]][i[1]].tmp and p < mindist:
                mindist = p
                ans = i
        if ans:
            self.SelectLand(ans[0], ans[1])
            self.moveTo(target[0], target[1])
        return

    def Main(self):
        self.Login()
        self.EnterRoom()
        self.table = self.driver.find_element_by_tag_name("tbody")
        flag = False
        while True:
            if self.driver.current_url != "https://kana.byha.top:444/checkmate/room/" + self.roomId:
                self.EnterRoom()
                sleep(10)
                continue
            self.SendKeyToTable('F')  # 防踢
            try:
                if self.driver.find_element_by_id("game-status").get_attribute('innerHTML') != "游戏中":
                    if flag:
                        flag = False
                    sleep(0.2)
                    self.ispre = False
                else:
                    self.botMove()
                    continue
                flag = True
            except:
                continue
            try:
                if self.isAutoReady and self.driver.find_element_by_id("ready").get_attribute('innerHTML') == "准备":
                    ac = ActionChains(self.driver)
                    ac.click(self.driver.find_element_by_id("ready")).perform()
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
        return


a = Bot(input("输入用户名："), input("输入密码："), input("输入房间号："), input("是否私密？(Y/N)") == "Y")
a.Main()
