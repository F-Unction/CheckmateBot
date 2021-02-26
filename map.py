from queue import PriorityQueue


def dist(xx1, yy1, xx2, yy2):
    return abs(xx1 - xx2) + abs(yy1 - yy2)


dir = [[-1, 0], [0, 1], [1, 0], [0, -1]]


class Node:
    def __init__(self, tmp=0, belong=0, type='land'):
        self.tmp = tmp
        self.belong = belong  # 1 ...
        self.type = type  # land city general unknown mountain empty empty-city


def distRouteNode(a, b):
    return dist(a[0], a[1], b[0], b[1])


class Map:
    def resize(self, size):
        self.size = size
        self.mp = [[Node() for _ in range(self.size + 1)] for _ in range(self.size + 1)]

    def __init__(self):
        self.resize(20)

    def getNeighbours(self, a):  # 获取邻居
        tmp = []
        for i in dir:
            px = a[0] + i[0]
            py = a[1] + i[1]
            if 1 <= px <= self.size and 1 <= py <= self.size and self.mp[px][py].type != 'mountain':
                tmp.append((px, py))
        return tmp

    def getCost(self, a):  # 获取通过这块土地的花费
        if self.mp[a[0]][a[1]].belong == 1:
            return 1
        else:
            return max(self.mp[a[0]][a[1]].tmp, 1)

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
        return path, cost_so_far[goal]

    def findPath(self, sx, sy, ex, ey):  # 查找路径
        if self.mp[sx][sy].type == 'mountain' or self.mp[ex][ey].type == 'mountain':
            return []
        path, cost = self.AStar((sx, sy), (ex, ey))
        return path, cost

    def findMatch(self, flt):  # 查找所有满足flt的格子
        tmp = []
        for i in range(1, self.size):
            for j in range(1, self.size):
                if flt(self.mp[i][j]):
                    tmp.append([i, j])
        return tmp

    def findMax(self, flt):  # 查找满足flt的格子中兵力最大的
        x = self.findMatch(flt)
        maxx = 0
        ans = []
        for i in x:
            if self.mp[i[0]][i[1]].tmp > maxx:
                maxx = self.mp[i[0]][i[1]].tmp
                ans = i
        return ans

    def findMatchByRange(self, x, y, rg, flt):  # 在(x, y)的rg范围内查找所有满足flt的格子
        tmp = []
        for i in range(x - rg, x + rg + 1):
            for j in range(y - rg, y + rg + 1):
                if 1 <= i <= self.size and 1 <= j <= self.size and flt(self.mp[i][j]):
                    tmp.append([i, j])
        return tmp
