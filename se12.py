# coding=cp1251

from se12worker import Se12Worker
from fddetect import FdDetector
from wtreceipt import WtReceipt
import time
import datetime
import os
import config
from DS1307 import DS1307Class

import logging
logging.basicConfig(level=logging.DEBUG, filename="/home/pi/app/se12.log", format="%(asctime)s\t[%(levelname)s]\t%(message)s")

class Se12Proc():
    # Constructor
    def __init__(self):
        # Инициализация
        self._step = "STARTUP"
        self._message = ""
        self._fail = False
        
        self._config = config.Config("/home/pi/app/se12.config")
        self._config.load()

        # RTC
        self._rtc = DS1307Class()
        os.system("sudo date -s '" + self._rtc.read_srt_sys_date() + "' > /dev/null")

        # Рабочие потоки
        self._worker = Se12Worker(self.onSe12Data, self.onSe12Idle)
        self._worker.daemon = True
        self._fddetector = FdDetector(self.onFdStateChange)
        self._fddetector.daemon = True

        # Состояние флешки
        self._fdstate = None
        self._fdupdate = False

        # Таймеры
        self._dtcheck = None

        # Сессия
        self.weight = 0.0
        self.tare = 0.0
        self.qty = 0

        self.lastId = self._config.getInt("last_id", 0)
        self.currentId = self._config.getInt("current_id", 0)
        self.receipt = WtReceipt()



    
    # Program start
    def run(self):
        self._worker.start()
        self._fddetector.start()
        while True:
            time.sleep(1)
        # Program end

    def onSe12Data(self, worker, actions):
        logging.info(actions)
        logging.info(self._step)

        for act in actions:
            action = act['Action']
            value = act['Value']

            if action == "Login":
                self.onLogin(worker, value)
                break

            if action == "F1":
                self.onF1Code(worker, value)
                break

            if action == "F3":
                self.onF3Code(worker, value)
                break

            if action == "F4":
                self.onF4Code(worker, value)
                break

            if action == "SendTare":
                self.onTare(worker, value)

            if action == "SendWeight":
                self.onWeight(worker, value)

            if action == "SendKeys":
                self.onSendKeys(worker, value)

        # next action
        logging.info(self._step)

        # draw
        self.draw(worker)
        #End onSe12Data 


    def onSe12Idle(self, worker):
        self.checkFdStateUpdate(worker)

        if self._step == "DATETIMECHECK":
            if self._dtcheck is None:
                self._dtcheck = datetime.datetime.now().timestamp()
            else:
                dT = datetime.datetime.now().timestamp() - self._dtcheck
                if dT > 10:
                    self._dtcheck = datetime.datetime.now().timestamp()
                    self.drawDateTimeCheck(worker)
        else:
            self._dtcheck = None


    def onFdStateChange(self, state):
        #logging.info("DF state: %s" % state)
        if not self._fdstate == None:
            self._fdupdate = True
        self._fdstate = state

    def checkFdStateUpdate(self, worker):
        if self._fdupdate:
            self._fdupdate = False
            if self._step == "MAINMENU":
                if self._fdstate:
                    self.message(worker, "Під'єднано\nUSB Flash drive")
                else:
                    self.message(worker, "Від'єднано\nUSB Flash drive")
                self.drawMainMenu(worker)  

    def saveReceiptsToFd(self, worker):
        worker.display("Записую...")
        if WtReceipt.store():
            self.message(worker, "Дані записано\nна диск", 5)
        else:
            self.alert(worker, "Підчас запису на\nдиск виникла помилка\nЗврніться до систе-\nмного адміністратора", 5)
        WtReceipt.umount()


    # При первом запуске
    def onStartup(self, worker):
        disp  = " ЗАВАНТАЖЕННЯ v1.0\n\n(C) 2018 FOP Lynnyk\ntel+38(067)614-05-33"
        worker.display(disp)
        worker.buzz(True)
        worker.delay(3)

    # Login
    def onLogin(self, worker, value: str):
        if not value == "":
            self._step = value
        
        if self._step == "STARTUP":
            self._step = "DATETIMECHECK"

        self.onStartup(worker)


    # Key pressed
    def onSendKeys(self, worker, keys):
        if len(keys) == 0:
            return    
        key = keys[-1]
        if self._step == "DATETIMECHECK":
            if key == "E":
                self.prepareMainMenu(worker)
            elif key == "A":
                self._step = "DATETIMESET"
        elif self._step == "DATETIMEINPUT":
            if key == "c":
                self._step = "DATETIMESET"
        elif self._step == "MAINMENU":
            if key == "A":
                self.newReceipt(worker)
            elif key == "D":
                self.saveReceiptsToFd(worker)
            elif key == "f":
                self._step = "SERVICEMENU"
        elif self._step == "SERVICEMENU":
            if key == "c":
                self._step = "MAINMENU"
        elif self._step == "RECEIPT":
            self.onKeyReceipt(worker, key)
        elif self._step == "RECEIPTPREPAREDELETE":
            self.onKeyReceipt(worker, key)   
        elif self._step == "RECEIPTPREPARECLOSE":
            self.onKeyReceipt(worker, key)

    # F1 code
    def onF1Code(self, worker, code):
        if self._step == "DATETIMEINPUT":
            self.setupDateTime(worker, code)
        elif self._step == "MAINMENU":
            pass

    # F3 code
    def onF3Code(self, worker, code):
        if self._step == "MAINMENU":
            self.printCopy(worker, code)

    # F4 code
    def onF4Code(self, worker, code):
        if self._step == "RECEIPT":
            self.setupQty(worker, code)       

    # Tare
    def onTare(self, worker, val):
        try:
            self.tare = float(val)
        except Exception as ex:
            self.tare = 0.0

    # Weight
    def onWeight(self, worker, val):
        try:
            self.weight = float(val)
        except Exception as ex:
            self.weight = 0.0
        
        if self._step == "RECEIPT":
            self.receiptAddCheck(worker)
        elif self._step == "MAINMENU":
            self.receiptPrintLabel(worker)    



    # Draw display
    def draw(self, worker):
        if self._step == "MAINMENU":
            self.drawMainMenu(worker)
        elif self._step == "SERVICEMENU":
            self.drawServiceMenu(worker)
        elif self._step == "DATETIMECHECK":
            self.drawDateTimeCheck(worker)
        elif self._step == "DATETIMESET":
            self.drawDateTimeSet(worker)
        elif self._step == "DATETIMEUPDATE":
            self.drawDateTimeUpdate(worker)
        elif self._step == "RECEIPT":
            self.drawReceipt(worker)
        elif self._step == "RECEIPTPREPAREDELETE":
            self.drawReceiptPrepareDelete(worker)
        elif self._step == "RECEIPTPREPARECLOSE":
            self.drawReceiptPrepareClose(worker)
    
    def alert(self, worker, message, duration=3):
        disp = message
        worker.display(disp)
        worker.buzz(True)
        worker.delay(duration)
        self.draw(worker)

    def message(self, worker, message, duration=1):
        disp = message
        worker.display(disp)
        worker.buzz(False)
        worker.delay(duration)
        self.draw(worker)


    # Date and Time setup
    def drawDateTimeCheck(self, worker):
        disp  = "  ПОЧАТОК РОБОТИ\n"
        disp += "системна дата та час\n"
        disp += "" + datetime.datetime.now().strftime("%d.%m.%Y %H:%M") + "\n"
        disp += "F1-Змінити  F5-Добре"
        worker.display(disp)
        worker.keyboardConfig("0900010006000001")

    def drawDateTimeSet(self, worker):
        disp  = "  ПОЧАТОК РОБОТИ\n"
        disp += "введіть дату та час\n"
        disp += "у форматі РРММДДггхх\n"
        disp += "        [Enter][Clr]"
        worker.display(disp)
        worker.keyboardConfig("2900010006000001")
        worker.keyPress("1A")
        self._step = "DATETIMEINPUT"

    def setupDateTime(self, worker, dtstring):
        self._fail = False
        self._step = "DATETIMEUPDATE"
        if len(dtstring) != 10:
            self._fail = True
            return
        try:
            Y = int(dtstring[0:2])
            M = int(dtstring[2:4])
            D = int(dtstring[4:6])
            H = int(dtstring[6:8])
            N = int(dtstring[8:10])
            if Y<18 or Y>99:
                self._fail = True
                return
            if M<1 or M>12:
                self._fail = True
                return
            if M in [1,3,5,7,8,10,12]:
                if D<1 or D>31:
                    self._fail = True
                    return
            if M in [4,6,9,11]:
                if D<1 or D>30:
                    self._fail = True
                    return
            if M == 2:
                if (Y%4==0 and Y%100!=0) or (Y%400==0):
                    if D<1 or D>29:
                        self._fail = True
                        return
                else:
                    if D<1 or D>28:
                        self._fail = True
                        return
            if H<0 or H>23:
                self._fail = True
                return
            if N<0 or N>59:
                self._fail = True
                return       

            res = os.system(f"sudo date -s '20{Y:02d}-{M:02d}-{D:02d} {H:02d}:{N:02d}:00' > /dev/null")
            if res != 0:
                self._fail = True
                return
            self._rtc.write_now()         
        except Exception as e:
            self._fail = True

    def drawDateTimeUpdate(self, worker):
        if self._fail:
            self._fail = False
            disp  = "ПОМИЛКА\nСпробуйте ще раз"
            worker.display(disp)
            worker.keyboardConfig("0900010006000001")
            worker.buzz(True)
            worker.delay(3)
            self._step = "DATETIMESET"
            self.draw(worker)
        else:
            disp  = "OK"
            worker.display(disp)
            worker.keyboardConfig("0900010006000001")
            worker.delay(1)
            self._step = "DATETIMECHECK"
            self.draw(worker)



    # Main menu
    def drawMainMenu(self, worker):
        disp  = "F1:Нова квитанція\n"
        disp += "F3:Дублікат квитанції\n"
        if self._fdstate:
            disp += "F4:Записати на флешку\n"
        else:
            disp += "\n"
        disp += "Menu:Сервісне меню"
        worker.display(disp)
        worker.keyboardConfig("0920010006000001")    

    def prepareMainMenu(self, worker):
        if self.currentId == 0:
            self._step = "MAINMENU"
        else:
            self.loadReceipt(worker)

    def printCopy(self, worker, code):
        try:
            id = int(code)
        except Exception as ex:
            self.alert(worker, "Помилка", 3)
            return
        
        self.receipt.new(id)
        if self.receipt.load() or self.receipt.loadArchive():
            self.receiptPrintLabel(worker)
            self.message(worker, "Готово", 1)
        else:
            self.alert(worker, "Квитанцію з номером\n{0:0=6d} не знайдено".format(id), 5)
        
        self.receipt = WtReceipt()
        self.prepareMainMenu(worker)

    # Receipt
    def newReceipt(self, worker):
        self._step = "RECEIPT"
        self.currentId = self.lastId + 1
        self.qty = 0
        self.weight = 0.0
        self.tare = 0.0
        self.receipt.new(self.currentId)
        self._config.set("current_id", self.currentId)
        self._config.save()
        
    def loadReceipt(self, worker):
        self._step = "RECEIPT"
        self.qty = 0
        self.weight = 0.0
        self.tare = 0.0
        self.receipt.new(self.currentId)
        self.receipt.load()
    
    def setupQty(self, worker, code):
        try:
            qty = int(code)
        except Exception as ex:
            qty = 0
        self.qty = qty

    def onKeyReceipt(self, worker, key):
        if self._step == "RECEIPT":
            if key == "k":
                self._step = "RECEIPTPREPAREDELETE"
            elif key == "E":
                self._step = "RECEIPTPREPARECLOSE"
        elif self._step == "RECEIPTPREPAREDELETE":
            if key == "1":
                self.receiptDeleteCheck(worker)
            else:
                self._step = "RECEIPT"
                self.alert(worker, "Дані не видалено", 3)
        elif self._step == "RECEIPTPREPARECLOSE":
            if key == "1":
                self.receiptClose(worker)
            else:
                self._step = "RECEIPT"
                self.alert(worker, "Не друкую", 3) 


    def receiptAddCheck(self, worker):
        if self.qty == 0:
            self.alert(worker, "Не вказано кількість")
            return
        self.receipt.append(self.qty, self.weight, self.tare)
        self.receipt.save()
        msg = "Зареєстровано:\n{0:d}/{1:.1f}".format(self.qty, self.weight)
        self.message(worker, msg, 3)

    def receiptDeleteCheck(self, worker):
        self._step = "RECEIPT"
        if self.receipt.delete():
            self.receipt.save()
            self.message(worker, "Дані видалено", 3)
        else:
            self.alert(worker, "Дані не видалено", 3)

    def receiptClose(self, worker):
        self._step = "RECEIPT"
        self.receiptPrintLabel(worker)
        self.receipt.save()
        self.lastId = self.currentId
        self.currentId = 0
        self._config.set("last_id", self.lastId)
        self._config.set("current_id", self.currentId)
        self._config.save() 

        self.prepareMainMenu(worker)
        self.message(worker, "Готово.", 1)  


    def drawReceipt(self, worker):
        totalQty = self.receipt.TotalQty
        totalWt = self.receipt.TotalWeight
        
        disp  = "Квитанція {0:0=6d}\n".format(self.currentId)
        disp += "Разом: {0:d}/{1:.1f}\n".format(totalQty, totalWt)
        disp += "Кількість: {0:d} <F4>\n".format(self.qty)
        disp += "F5: Друк квитанції"

        worker.display(disp)
        worker.keyboardConfig("0902010006000001")

    def drawReceiptPrepareDelete(self, worker):
        disp  = "Видалити останнє\nзважування?\n\n  1-Так   0-Ні"
        worker.display(disp)
        worker.keyboardConfig("0900010006000001")

    def drawReceiptPrepareClose(self, worker):
        disp  = "Закінчити зважування\nДрукувати квитанцію?\n\n  1-Так   0-Ні"
        worker.display(disp)
        worker.keyboardConfig("0900010006000001") 

    def receiptPrintLabel(self, worker):
        disp = "Друк..."
        worker.display(disp)
        
        h = 120 + (self.receipt.Len * 5)

        label  = "^XSET,CODEPAGE,16\n^G0\n^E0\n^W100\n^Q{0:d},0,30\n^L\n".format(h)
        label += "AF,0,0,1,1,0,0,GOODVALLEY\n"
        label += "AC,360,20,1,1,0,0,Категорія зважування СВИНІ\n"
        label += "AC,0,60,1,1,0,0,Ферма ____________________________________________\n"
        label += "AC,0,110,1,1,0,0,Авто/причіп ________________________________________\n"
        label += "AC,0,160,1,1,0,0,Водій _____________________________  _______________\n"
        label += "AA,600,195,1,1,0,0,/підпис/\n"
        label += "AB,0,220,1,1,0,0,----------------------- заповнюється відповідальним менеджером -----------------------\n"
        label += "AC,0,260,1,1,0,0,Покупець __________________________________________\n"
        label += "AC,0,310,1,1,0,0,Продукція/категорія _________________________________\n"
        label += "AC,0,360,1,1,0,0,Кількість: ________________ Вага: ____________________\n"
        label += "AC,0,410,1,1,0,0,Ціна, грн: ________________ Дата: ____________________\n"
        label += "AC,0,460,1,1,0,0,___________________________  _____________________\n"
        label += "AA,150,495,1,1,0,0,/менеджер/\n"
        label += "AA,550,495,1,1,0,0,/підпис/\n"
        worker.printLabel(label)

        label  = "AB,0,520,1,1,0,0,------------------ інформація по вантажівці (стайня - вага - рампа) ------------------\n"
        label += "AC,0,560,1,1,0,0,Вантажівка ________________________________________\n"
        label += "AC,0,610,1,1,0,0,Водій ____________________________________________\n"
        label += "AB,0,670,1,1,0,0,---------------------------------- вагова квитанція ----------------------------------\n"
        
        label += "AC,0,710,1,1,0,0,ф.Тустань {0:%d.%m.%Y %H:%M}      партія\n".format(datetime.datetime.now())
        label += "AC,500,710,2,1,0,0,{0:0=6d}\n".format(self.receipt.id)

        y = 760
        i = 1
        for item in self.receipt.items():
            if len(label) > 800:
                worker.printLabel(label)
                label = ""
            dt, qty, wt, tr = item.item()
            label += "AD,0,{0:d},1,1,0,0,{1: =3d}. {2:%d.%m.%Y %H:%M}; голів {3: =3d}; маса {4: =9.3f} кг\n".format(y, i, dt, qty, wt)
            i += 1
            y += 40  

        if len(label) > 800:
            worker.printLabel(label)
            label = ""

        y += 20
        label += "AD,0,{0:d},1,1,0,0,Загальна кількість голів: {1:d}\n".format(y, self.receipt.TotalQty)

        y += 40
        label += "AD,0,{0:d},1,1,0,0,Загальна маса: {1:.3f} кг\n".format(y, self.receipt.TotalWeight)

        y += 40
        label += "AD,0,{0:d},1,1,0,0,Середня маса однієї голови: {1:.3f} кг\n".format(y, self.receipt.AverageWeigt)

        y += 60
        label += "AC,0,{0:d},1,1,0,0,Оператор ваги  ____________________________\n".format(y)

        label += "E\n"
        worker.printLabel(label)    

    def ___receiptPrintLabel(self, worker):
        disp = "Друк..."
        worker.display(disp)
        
        h = 35 + (self.receipt.Len * 5)

        label  = "^Q{0:d},0,30\n^W60\n^G0\n^E0\n~R255\n^R25\n~Q+0\n^XSET,CODEPAGE,16\n^L\n".format(h)
        
        #label += "AC,0,10,1,1,0,0,Дата {0:%d.%m.%Y %H:%M}\n".format(datetime.datetime.now())
        label += "AC,0,10,1,1,0,0,Категорія зважування СВИНІ\n"
        label += "AC,0,50,1,1,0,0,Партія {0:0=6d}\n".format(self.receipt.id)

        y = 110
        i = 1
        for item in self.receipt.items():
            if len(label) > 800:
                worker.printLabel(label)
                label = ""
            dt, qty, wt, tr = item.item()
            label += "AA,0,{0:d},1,2,0,0,{1: =3d}. {2:%d.%m.%y %H:%M}; голів {3: =3d}; маса {4: =8.3f} кг\n".format(y, i, dt, qty, wt)
            i += 1
            y += 40  

        if len(label) > 800:
            worker.printLabel(label)
            label = ""

        y += 30
        label += "AB,0,{0:d},1,1,0,0,Загальна кількість голів: {1:d}\n".format(y, self.receipt.TotalQty)

        y += 30
        label += "AB,0,{0:d},1,1,0,0,Загальна маса: {1:.3f} кг\n".format(y, self.receipt.TotalWeight)

        y += 30
        label += "AB,0,{0:d},1,1,0,0,Середня маса однієї голови: {1:.3f} кг\n".format(y, self.receipt.AverageWeigt)

        y += 60
        label += "AA,0,{0:d},1,1,0,0,Оператор ваги  ____________________________\n".format(y)

        label += "E\n"
        worker.printLabel(label)

    # Service menu
    def drawServiceMenu(self, worker):
        disp = "IP: "
        try:
            ipv4 = os.popen('ip addr show eth0').read().split("inet ")[1].split("/")[0]
            disp += ipv4
            disp += "\nSSH:22, FTP:21\nLogin   : pi\nPassword: raspberry"
        except:
            disp += "Not connected"
        worker.display(disp)
        worker.keyboardConfig("0900010006000001")


#-----------------------------------------------------
if __name__ == "__main__":
    proc = Se12Proc()
    proc.run()
