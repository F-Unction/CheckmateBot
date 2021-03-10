import json


class DataBase(object):
    def __init__(self, filename):
        self.data = {}
        self.filename = filename

    def getByKey(self, item, key=''): # 请注意返回str类型
        item = str(item)
        key = str(key)
        if key == '' and item in self.data:
            return self.data[item]
        if item in self.data and key in self.data[item]:
            return self.data[item][key]
        else:
            return 0

    def addByKey(self, item, x, key):
        item = str(item)
        key = str(key)
        if item in self.data and key in self.data[item]:
            self.data[item][key] += x
            return
        elif item not in self.data:
            self.data[item] = {}
        self.data[item][key] = x
        return

    def setByKey(self, item, x, key):
        item = str(item)
        key = str(key)
        if item not in self.data:
            self.data[item] = {}
        self.data[item][key] = x

    def appendByKey(self, item, x, key):
        item = str(item)
        key = str(key)
        if item in self.data and key in self.data[item]:
            self.data[item][key].append(x)
            return
        elif item not in self.data:
            self.data[item] = {}
        self.data[item][key] = [x]

    def readData(self):
        self.data = json.load(open(self.filename, 'r'))
        return

    def saveData(self):
        json.dump(self.data, open(self.filename, "w"))

    def getItemList(self):
        return list(self.data.keys())

    def deleteByKey(self, item, key=''):
        item = str(item)
        key = str(key)
        if key == '':
            del self.data[item]
        else:
            del self.data[item][key]
        return

    def findMatch(self, flt):  # 查找所有满足flt的数据
        item = self.getItemList()
        ans = []
        for i in item:
            if flt(self.getByKey(i)):
                ans.append(i)
        return ans
