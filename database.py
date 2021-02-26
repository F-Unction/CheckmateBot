import json


class DataBase(object):
    def __init__(self):
        self.data = {}

    def getByKey(self, uname, key):
        if uname in self.data and key in self.data[uname]:
            return self.data[uname][key]
        else:
            return 0

    def addByKey(self, uname, x, key):
        if uname in self.data and key in self.data[uname]:
            self.data[uname][key] += x
            return
        elif uname not in self.data:
            self.data[uname] = {}
        self.data[uname][key] = x
        return

    def setByKey(self, uname, x, key):
        if uname not in self.data:
            self.data[uname] = {}
        self.data[uname][key] = x

    def readData(self):
        self.data = json.load(open("data.json", 'r'))
        return

    def saveData(self):
        json.dump(self.data, open("data.json", "w"))

    def getUserNameList(self):
        return list(self.data.keys())
