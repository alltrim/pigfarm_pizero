# coding=cp1251
import logging

class Config(object):

    def __init__(self, filename):
        self.__filename = filename
        self.__vals = {}

    def load(self):
        self.__vals = {}
        try:
            with open(self.__filename, "r") as file:
                lines = file.readlines() 
            for line in lines:
                key_val = line.split("=", 1)
                if len(key_val) == 2:
                    key = key_val[0].strip()
                    val = key_val[1].strip()
                    self.__vals[key] = val
        except Exception as ex:
            logging.info(ex)

    def save(self):
        with open(self.__filename, "w") as file:
            for key, val in self.__vals.items():
                file.write(key)
                file.write("=")
                file.write(val)
                file.write("\n")

    def set(self, key, val):
        self.__vals[key] = str(val)

    def getInt(self, key, default=None):
        val = self.__vals.get(key, default)
        try:
            val = int(val)
        except Exception as ex:
            pass
        return val

    def getStr(self, key, default=None):
        val = self.__vals.get(key, default)
        return val

    def __repr__(self):
        s = ""
        for key, val in self.__vals.items():
                s += (key + "=" + val + "\n")
        return s   



