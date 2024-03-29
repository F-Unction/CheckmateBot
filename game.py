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
        self.home_x = 0
        self.home_y = 0
        self.cur_x = 0
        self.cur_y = 0
        self.movements = []
        self.homes = []
        self.vis = []
        self.is_pre = False  # 是否预处理
        self.useless = []
        self.land_before = []
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
                    self.mp.mp[i][j].amount = int(p)
                except ValueError:
                    self.mp.mp[i][j].amount = 0
                if self.mp.mp[i][j].belong != 1:
                    self.mp.mp[i][j].cost = max(self.mp.mp[i][j].amount, 2)
                else:
                    self.mp.mp[i][j].cost = 1

    def pre(self):  # 预处理地图
        tmp = self.mp.find_match(lambda a: a.type == 'general' and a.belong == 1)
        if len(tmp) != 1:
            return 1
        self.home_x = tmp[0][0]
        self.home_y = tmp[0][1]
        self.cur_x = self.home_x
        self.cur_y = self.home_y
        self.movements = []
        self.homes = []
        self.vis = []
        self.is_pre = True
        self.useless = []
        self.land_before = []
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

    def short_move(self, cx, cy, px, py):
        """直接从(cx, cy)移动到相邻的(px, py)"""
        if cx < px and cy == py:
            return 'S'
        elif cx > px and cy == py:
            return 'W'
        elif cx == px and cy > py:
            return 'A'
        else:
            return 'D'

    def move_to(self, x, y, cur_x=0, cur_y=0):  # 移动
        if cur_x == 0 and cur_y == 0:
            cur_x = self.cur_x
            cur_y = self.cur_y
        path, cost = self.mp.find_path(cur_x, cur_y, x, y)
        ans = copy.deepcopy(path)
        if path:
            path.pop(0)
            cx = cur_x
            cy = cur_y
            self.movements.append([cx, cy])
            while path:
                px = path[0][0]
                py = path[0][1]
                self.movements.append(self.short_move(cx, cy, px, py))
                cx = px
                cy = py
                path.pop(0)
        return ans

    def update_map(self):  # 分析地图
        tmp = self.mp.find_match(lambda a: a.type == 'general' and a.belong != 1)
        if tmp:
            for i in tmp:
                if i not in self.homes:  # 找家
                    self.homes.append(i)
        tmp = self.mp.find_match(lambda a: a.type != 'unknown')
        for i in tmp:
            if i not in self.vis:  # 已经可见的土地无需探索
                self.vis.append(i)
        if not self.land_before:
            self.land_before = self.mp.find_match(lambda a: a.type == 'empty' or a.belong == 1)
        else:
            enemy = self.mp.find_match(lambda a: a.belong != 1)
            for i in enemy:
                if i in self.land_before and i not in self.useless:  # 之前是空地或己方土地，现在是敌方土地，无需探索
                    self.useless.append(i)
            self.land_before = []
        return

    def gather_army_to(self, x, y, method='rectangle'):  # 向(x, y)聚兵
        if method == 'ring':
            levels = [[] for _ in range(21)]
            all_land = self.mp.find_match(lambda a: a.belong == 1 and a.amount > 2 and a.type == 'land')
            if not all_land:
                return
            amount = []
            for i in all_land:
                amount.append(self.mp.mp[i[0]][i[1]].amount)
            amount.sort()
            avg_amount = amount[len(amount) // 2]
            for i in range(1, self.mp.size + 1):
                for j in range(1, self.mp.size + 1):
                    if self.mp.mp[i][j].belong == 1:
                        if self.mp.mp[i][j].amount >= avg_amount:
                            levels[max(abs(i - x), abs(j - y))].append([(i, j), self.mp.mp[i][j].amount])
                        else:
                            self.mp.mp[i][j].cost = 2.1
            role = lambda a: a[1]
            max_level = 0
            for i in range(21):
                if levels[i]:
                    levels[i].sort(key=role, reverse=True)
                    max_level = i
            for i in range(max_level, -1, -1):
                for j in levels[i]:
                    if self.move_to(x, y, j[0][0], j[0][1]):
                        return
        if method == 'tree':
            available = []
            all_land = self.mp.find_match(lambda a: a.belong == 1 and a.amount > 2 and a.type == 'land')
            if not all_land:
                return
            amount = []
            for i in all_land:
                amount.append(self.mp.mp[i[0]][i[1]].amount)
            amount.sort()
            avg_amount = amount[len(amount) // 2]
            for i in range(1, self.mp.size + 1):
                for j in range(1, self.mp.size + 1):
                    if self.mp.mp[i][j].belong == 1:
                        if self.mp.mp[i][j].amount >= avg_amount:
                            cnt = 0
                            neighbours = self.mp.get_neighbours([i, j])
                            for k in neighbours:
                                if self.mp.mp[k[0]][k[1]].belong == 1:
                                    cnt += 1
                                if cnt > 1:
                                    break
                            if cnt == 1:
                                available.append([i, j])
                        else:
                            self.mp.mp[i][j].cost = 2.1
                    else:
                        self.mp.mp[i][j].cost = 1000000
            max_amount = 0
            ans = []
            for i in available:
                path, cost = self.mp.find_path(i[0], i[1], x, y)
                cnt = 0
                for j in path:
                    if self.mp.mp[j[0]][j[1]].belong == 1:
                        cnt += self.mp.mp[j[0]][j[1]].amount
                    else:
                        cnt -= self.mp.mp[j[0]][j[1]].amount
                if cnt > max_amount:
                    max_amount = cnt
                    ans = i
            if not ans:
                return
            self.move_to(x, y, ans[0], ans[1])
        if method == 'rectangle':
            a = [[-9999999 for i in range(self.mp.size + 2)] for j in range(self.mp.size + 2)]
            for i in range(1, self.mp.size + 1):
                for j in range(1, self.mp.size + 1):
                    if self.mp.mp[i][j].belong == 1:
                        a[i][j] = self.mp.mp[i][j].amount - 1
            ans_top_left = (0, 0)
            ans_bottom_right = (0, 0)
            best_sum = 0
            for start_row in range(1, self.mp.size + 1):  # 最大子矩阵和
                tmp = [0 for _ in range(self.mp.size + 2)]
                for end_row in range(start_row, self.mp.size + 1):
                    cur_sum = 0
                    best_col = 1
                    for end_col in range(1, self.mp.size + 1):
                        tmp[end_col] += a[end_row][end_col]
                        if cur_sum >= 0:
                            cur_sum += tmp[end_col]
                        else:
                            cur_sum = tmp[end_col]
                            best_col = end_col
                        if cur_sum > best_sum:
                            ans_top_left = (start_row, best_col)
                            ans_bottom_right = (end_row, end_col)
                            best_sum = cur_sum
            ans_top_right = (ans_top_left[0], ans_bottom_right[1])
            ans_bottom_left = (ans_bottom_right[0], ans_top_left[1])
            ans = [ans_top_left, ans_top_right, ans_bottom_left, ans_bottom_right]
            print(ans, best_sum)
            tmp = []
            target_node = (x, y)
            for i in ans:
                tmp.append([i, dist_node(i, target_node)])
            role = lambda p: p[1]
            tmp.sort(key=role)
            end_node = tmp[0][0]
            flag = ((ans_bottom_left[0] - ans_top_left[0]) % 2) == 1  # 奇同偶异
            start_node = (0, 0)
            if end_node == ans_top_left:
                if flag:
                    start_node = ans_bottom_left
                else:
                    start_node = ans_bottom_right
            if end_node == ans_top_right:
                if flag:
                    start_node = ans_bottom_right
                else:
                    start_node = ans_bottom_left
            if end_node == ans_bottom_left:
                if flag:
                    start_node = ans_top_left
                else:
                    start_node = ans_top_right
            if end_node == ans_bottom_right:
                if flag:
                    start_node = ans_top_right
                else:
                    start_node = ans_top_left
            cx = start_node[0]
            cy = start_node[1]
            self.movements.append(start_node)
            if start_node == ans_top_left or start_node == ans_bottom_left:
                cur_dir = True  # 是否向右
            else:
                cur_dir = False
            if start_node[0] < end_node[0]:
                dx = 1  # 每次改变的x
            else:
                dx = -1
            min_y = min(ans_top_left[1], ans_top_right[1])
            max_y = max(ans_top_left[1], ans_top_right[1])
            while cx != end_node[0] or cy != end_node[1]:  # 蛇形遍历
                print(cx, cy)
                px = cx
                py = cy
                if cur_dir:
                    py += 1
                else:
                    py -= 1
                if py < min_y:
                    px += dx
                    py = min_y
                    cur_dir = not cur_dir
                if py > max_y:
                    px += dx
                    py = max_y
                    cur_dir = not cur_dir
                self.movements.append(self.short_move(cx, cy, px, py))
                cx = px
                cy = py
            self.move_to(x, y, end_node[0], end_node[1])

    def get_target(self):  # 寻找一个可行的扩张目标
        tmp = self.mp.find_match(lambda a: a.type == 'unknown')
        target = []
        random.shuffle(tmp)
        role = lambda a: len(
            self.mp.find_match_by_range(a[0], a[1], 4, lambda b: b.type == 'land' and b.belong != 1 and (
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
            self.cur_x = x
            self.cur_y = y
            return
        except:
            return

    def send_key_to_table(self, key):
        """发送按键"""
        ac = ActionChains(self.driver)
        ac.send_keys(key).perform()

    def flush_movements(self):  # 更新移动
        tmp = self.mp.mp[self.home_x][self.home_y].amount
        cur_movement = self.movements[0]
        while isinstance(cur_movement, list) or isinstance(cur_movement, tuple):
            self.select_land(cur_movement[0], cur_movement[1])
            self.movements.pop(0)
            if not self.movements:
                return
            cur_movement = self.movements[0]
        self.send_key_to_table(cur_movement)
        if self.movements[0] == 'W':
            self.cur_x -= 1
        elif self.movements[0] == 'S':
            self.cur_x += 1
        elif self.movements[0] == 'A':
            self.cur_y -= 1
        elif self.movements[0] == 'D':
            self.cur_y += 1
        self.movements.pop(0)
        self.get_map()
        self.update_map()
        try_time = 0
        while self.mp.mp[self.home_x][self.home_y].amount == tmp and try_time <= 80:
            self.get_map()
            try_time += 1
        return

    def bot_move(self):  # 主循环，每回合执行一次
        self.get_map()
        if not self.is_pre:
            if self.pre() == 1:
                return
        if self.movements:
            self.flush_movements()
            return
        if [self.cur_x, self.cur_y] not in self.vis:
            self.vis.append([self.cur_x, self.cur_y])
        self.update_map()
        mx = self.mp.find_max(lambda a: a.belong == 1)
        if self.mp.mp[mx[0]][mx[1]].amount < 2:
            return
        if self.homes:  # 智能掏家
            tmp = random.choice(self.homes)
            if self.mp.mp[tmp[0]][tmp[1]].belong == 1:  # 已经占领的家移除
                self.homes.remove(tmp)
                return
            self.gather_army_to(tmp[0], tmp[1])
            return
        tmp = self.mp.find_match_by_range(self.home_x, self.home_y, 1,
                                          lambda a: a.belong != 1 and (a.type == 'land' or a.type == 'city'))
        if tmp and self.mp.mp[mx[0]][mx[1]].amount > 30:  # 智能守家
            tmp = random.choice(tmp)
            self.mp.mp[self.home_x][self.home_y].cost = 10000
            self.move_to(tmp[0], tmp[1], mx[0], mx[1])
            self.defending = True
            return
        if self.defending and dist(self.cur_x, self.cur_y, self.home_x, self.home_y) <= 2:
            self.move_to(self.home_x, self.home_y)
            self.gather_army_to(self.home_x, self.home_y)
            self.defending = False
            return
        self.defending = False
        target = self.get_target()
        owned = self.mp.find_match(lambda a: a.belong == 1 and a.amount >= self.mp.mp[target[0]][target[1]].amount)
        if not owned:
            owned = [[self.home_x, self.home_y]]
        random.shuffle(owned)
        min_dist = 10000
        ans = []
        for i in owned:
            p = dist(i[0], i[1], target[0], target[1])
            if p < self.mp.mp[i[0]][i[1]].amount and p < min_dist:
                path, cost = self.mp.find_path(self.cur_x, self.cur_y, target[0], target[1])
                if self.mp.mp[i[0]][i[1]].amount >= cost:
                    min_dist = p
                    ans = i
        if ans:  # 探索
            if ans[0] == self.home_x and ans[1] == self.home_y:
                self.movements.append('Z')
            self.move_to(target[0], target[1], ans[0], ans[1])
        return
