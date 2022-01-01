# coding=cp1251

import datetime
import os
import logging

class WtReceipt():
    __USB = "/tmp/mounts/USB-A1/"
    __PATH = "/home/pi/app/receipt/"
    __ARCHIVE = "/home/pi/app/archive/"

    # Constructor
    def __init__(self):
        #self.__USB = "/tmp/mounts/USB-A1/"
        #self.__PATH = "/root/se12/receipt/"
        #self.__ARCHIVE = "/root/se12/archive/"
        if not os.path.exists(WtReceipt.__PATH):
            os.mkdir(WtReceipt.__PATH)
        if not os.path.exists(WtReceipt.__ARCHIVE):
            os.mkdir(WtReceipt.__ARCHIVE)

        self.id = 0
        self.begin = None
        self.end = None
        self.checks = []


    def new(self, id):
        self.id = id
        self.begin = datetime.datetime.now()
        self.end = None
        self.checks = []
    
    def append(self, qty=0, weight=0.0, tare=0.0):
        check = WtCheck(qty, weight, tare)
        self.checks.append(check)

    def delete(self):
        if len(self.checks) == 0:
            return False
        self.checks.pop()
        return True

    def items(self):
        return self.checks

    @property
    def Len(self):
        return len(self.checks)

    @property
    def TotalQty(self):
        total = 0
        for check in self.checks:
            total += check.qty
        return int(total)

    @property
    def TotalWeight(self):
        total = 0.0
        for check in self.checks:
            total += check.weight
        return float(total)

    @property
    def AverageWeigt(self):
        qty = self.TotalQty
        wt  = self.TotalWeight
        if qty == 0:
            return 0.0
        return float(wt) / float(qty)


    def load(self):
        self.checks = []
        filename = WtReceipt.__PATH + "{0:0>6d}.csv".format(self.id)
        try:
            with open(filename, "r") as file:
                lines = file.readlines()
        except Exception as ex:
            logging.info(ex)
            return False
        for line in lines:
            check = WtCheck.read(line)
            if check != None:
                self.checks.append(check)
        return True

    def loadArchive(self):
        self.checks = []
        filename = WtReceipt.__ARCHIVE + "{0:0>6d}.csv".format(self.id)
        try:
            with open(filename, "r") as file:
                lines = file.readlines()
        except Exception as ex:
            logging.info(ex)
            return False
        for line in lines:
            check = WtCheck.read(line)
            if check != None:
                self.checks.append(check)
        return True 

    def save(self):
        filename = WtReceipt.__PATH + "{0:0>6d}.csv".format(self.id)
        try:
            with open(filename, "w") as file:
                for check in self.checks:
                    check.write(file)
        except Exception as ex:
            logging.info(ex)
            return False
        return True

    @staticmethod
    def store():
        if not os.path.exists(WtReceipt.__USB):
            return False
        path = WtReceipt.__USB + "receipt/"
        if not os.path.exists(path):
            try:
                os.mkdir(path)
            except Exception as ex:
                logging.info(ex)
                return False
        try:
            res = os.system("cp -f " + WtReceipt.__PATH + "*.csv " + path)
            if res != 0:
                return False
            os.system("mv -f " + WtReceipt.__PATH + "*.csv " + WtReceipt.__ARCHIVE)
        except Exception as ex:
            logging.info(ex)
            return False
        return True

    @staticmethod
    def umount():
        if not os.path.exists(WtReceipt.__USB):
            return False
        try:
            os.system("umount -f " + WtReceipt.__USB[:-1])   
        except Exception as ex:
            logging.info(ex)
            return False
        return True        


class WtCheck():
    # Constructor
    def __init__(self, qty=0, weight=0.0, tare=0.0, dt=None):
        if dt == None:
            self.datetime = datetime.datetime.now()
        else:
            self.datetime = dt
        self.qty = qty
        self.weight = weight
        self.tare = tare

    def write(self, file):
        rec = "{0:%d.%m.%Y %H:%M:%S};".format(self.datetime)
        file.write(rec)
        rec = "{0:d};{1:.3f};{2:.3f}\r\n".format(self.qty, self.weight, self.tare)
        rec = rec.replace(".", ",")
        file.write(rec)

    @staticmethod
    def read(line):
        if line == "":
            return None
        rec = line.split(";")
        if len(rec) != 4:
            return None
        try:
            dt = datetime.datetime.strptime(rec[0], "%d.%m.%Y %H:%M:%S")
            qty = int(rec[1])
            wt = float(rec[2].replace(",", "."))
            tr = float(rec[3].replace(",", "."))
            check = WtCheck(qty, wt, tr, dt)
            return check
        except Exception as ex:
            logging.info(ex)
            return None

    def item(self):
        return self.datetime, self.qty, self.weight, self.tare

    def trace(self):
        rec = "{0:%d.%m.%Y %H:%M:%S};{1:d};{2:.3f};{3:.3f}".format(self.datetime, self.qty, self.weight, self.tare)
        logging.info(rec)

        
        



