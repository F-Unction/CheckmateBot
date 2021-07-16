import copy
import random
import re

from selenium.webdriver.common.action_chains import ActionChains

from map import *


class Error(Exception):
    pass


class MapSizeError(Error):
    def __init__(self, size):
        self.size = size


class Game(object):
    def __init__(self, driver):
        self.driver = driver
        self.mp = Map()
        self.players = []
        self.homex = 0
        self.homey = 0
        self.curx = 0
        self.cury = 0
        self.movements = []
        self.homes = []
        self.vis = []
        self.is_pre = False  # 是否预处理
        self.useless = []
        self.preland = []
        self.players = []
        self.defending = False

    def get_map(self):
        html = self.driver.find_element_by_id("m").get_attribute("innerHTML")
        node_type = []
        node_tmp = []
        cnt = 0
        while True:
            tmp = re.search(r'class="[\s\S]*?"', html)
            if tmp:
                g = tmp.group()
                g = g[7:len(g) - 1]
                node_type.append(" " + g + " ")
                p = html.find(g)
                html = html[p + len(g):len(html)]
                cnt += 1
            else:
                break
            tmp = re.search(r'>.*?<', html)
            g = tmp.group()
            g = g[1:len(g) - 1]
            node_tmp.append(g)
        self.mp.resize(int(cnt ** 0.5))
        if self.mp.size not in [9, 10, 19, 20]:
            raise MapSizeError(self.mp.size)
        for i in range(1, self.mp.size + 1):
            for j in range(1, self.mp.size + 1):
                p = node_type[0]
                node_type.pop(0)
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
                p = node_tmp[0]
                node_tmp.pop(0)
                try:
                    self.mp.mp[i][j].tmp = int(p)
                except ValueError:
                    self.mp.mp[i][j].tmp = 0
                if self.mp.mp[i][j].belong != 1:
                    self.mp.mp[i][j].cost = max(self.mp.mp[i][j].tmp, 2)
                else:
                    self.mp.mp[i][j].cost = 1

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
        self.is_pre = True
        self.useless = []
        self.preland = []
        self.players = []
        self.defending = False

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
            self.players.append(username)
        return 0

    def move_to(self, x, y, curx=0, cury=0):  # 移动
        if curx == 0 and cury == 0:
            curx = self.curx
            cury = self.cury
        path, cost = self.mp.findPath(curx, cury, x, y)
        ans = copy.deepcopy(path)
        if path:
            path.pop(0)
            cx = curx
            cy = cury
            self.movements.append([cx, cy])
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
        return ans

    def update_map(self):  # 分析地图
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

    def gather_army_to(self, x, y):  # 向(x, y)聚兵
        flag = []
        levels = [[] for _ in range(21)]
        all_land = self.mp.findMatch(lambda a: a.belong == 1 and a.tmp > 2 and a.type == 'land')
        if not all_land:
            return
        amount = []
        for i in all_land:
            amount.append(self.mp.mp[i[0]][i[1]].tmp)
        amount.sort()
        avg_amount = amount[len(amount) // 2]
        for i in range(1, self.mp.size + 1):
            for j in range(1, self.mp.size + 1):
                if self.mp.mp[i][j].belong == 1:
                    if self.mp.mp[i][j].tmp >= avg_amount:
                        levels[max(abs(i - x), abs(j - y))].append([(i, j), self.mp.mp[i][j].tmp])
                    else:
                        self.mp.mp[i][j].cost = 2.1
        role = lambda a: a[1]
        maxlevel = 0
        for i in range(21):
            if levels[i]:
                levels[i].sort(key=role, reverse=True)
                maxlevel = i
        for i in range(maxlevel, -1, -1):
            for j in levels[i]:
                if j[0] not in flag:
                    path = self.move_to(x, y, j[0][0], j[0][1])
                    if not path:
                        continue
                    for p in range(1, self.mp.size + 1):
                        for q in range(1, self.mp.size + 1):
                            if self.mp.mp[p][q].belong == 1:
                                self.mp.mp[p][q].cost = 1
                    return

    def get_target(self):  # 寻找一个可行的扩张目标
        tmp = self.mp.findMatch(lambda a: a.type == 'unknown')
        target = []
        random.shuffle(tmp)
        role = lambda a: len(self.mp.findMatchByRange(a[0], a[1], 4, lambda b: b.type == 'land' and b.belong != 1 and (
                b not in self.useless)))
        tmp.sort(key=role, reverse=True)
        for i in tmp:
            if [i[0], i[1]] not in self.vis:
                target = i
                break
        if not target:
            target = random.choice(tmp)
        return target

    def select_land(self, x, y):  # 选择土地
        try:
            self.driver.find_element_by_id(
                'td-' + str((x - 1) * self.mp.size + y)).click()
            self.curx = x
            self.cury = y
            return
        except:
            return

    def send_key_to_table(self, key):
        """发送按键"""
        ac = ActionChains(self.driver)
        ac.send_keys(key).perform()

    def flush_movements(self):  # 更新移动
        tmp = self.mp.mp[self.homex][self.homey].tmp
        curm = self.movements[0]
        while isinstance(curm, list):
            self.select_land(curm[0], curm[1])
            self.movements.pop(0)
            if not self.movements:
                return
            curm = self.movements[0]
        self.send_key_to_table(curm)
        if self.movements[0] == 'W':
            self.curx -= 1
        elif self.movements[0] == 'S':
            self.curx += 1
        elif self.movements[0] == 'A':
            self.cury -= 1
        elif self.movements[0] == 'D':
            self.cury += 1
        self.movements.pop(0)
        self.get_map()
        self.update_map()
        trytime = 0
        while self.mp.mp[self.homex][self.homey].tmp == tmp and trytime <= 80:
            self.get_map()
            trytime += 1
        # if self.mp.mp[self.curx][self.cury].belong != 1:
        #     self.movements = []
        return

    def bot_move(self):  # 主循环，每回合执行一次
        self.get_map()
        if not self.is_pre:
            if self.pre() == 1:
                return
        if self.movements:
            self.flush_movements()
            return
        if [self.curx, self.cury] not in self.vis:
            self.vis.append([self.curx, self.cury])
        self.update_map()
        mx = self.mp.findMax(lambda a: a.belong == 1)
        if self.mp.mp[mx[0]][mx[1]].tmp < 2:
            return
        if self.homes:  # 智能掏家
            tmp = random.choice(self.homes)
            if self.mp.mp[tmp[0]][tmp[1]].belong == 1:  # 已经占领的家移除
                self.homes.remove(tmp)
                return
            self.gather_army_to(tmp[0], tmp[1])
            return
        tmp = self.mp.findMatchByRange(self.homex, self.homey, 1,
                                       lambda a: a.belong != 1 and (a.type == 'land' or a.type == 'city'))
        if tmp and self.mp.mp[mx[0]][mx[1]].tmp > 30:  # 智能守家
            mx = self.mp.findMax(lambda a: a.belong == 1)
            tmp = random.choice(tmp)
            self.move_to(tmp[0], tmp[1], mx[0], mx[1])
            self.defending = True
            return
        if self.defending and dist(self.curx, self.cury, self.homex, self.homey) <= 2:
            self.gather_army_to(self.homex, self.homey)
            self.defending = False
            return
        self.defending = False
        target = self.get_target()
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
                self.movements.append('Z')
            self.move_to(target[0], target[1], ans[0], ans[1])
        return
