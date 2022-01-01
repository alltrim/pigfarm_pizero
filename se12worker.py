# coding=cp1251

import serial
import socket
import time
import re
import config
from threading import Thread
import logging

class Se12Worker(Thread):
     # Constructor
    def __init__(self, callback, idle=None):
        Thread.__init__(self)
        #self._addr = b"01"
        
        con = config.Config("/home/pi/app/connection.config")
        con.load()

        conAddr = con.getInt("addr", 1)
        conType = con.getStr("type", "serial")

        self._addr = bytes("{0:0=2d}".format(conAddr), encoding="cp1251")

        if conType == "serial":
            port = con.getStr("serial_port", "/dev/serial0")
            baudrate = con.getInt("serial_baudrate", 57600)
            self._ser = Se12Serial(port, baudrate)
        else: #conType == "socket"
            host = con.getStr("socket_ip", "127.0.0.1")
            port = con.getInt("socket_port", 1001)
            self._ser = Se12Socket(host, port) 
        
        self._callback = callback
        self._idle = idle
        self._isRunning = False


    def run(self):
        if not self._isRunning :
            self._isRunning = True
            #self._greenLed.setValue(1)
            self.worker()

    def abort(self):
        self._isRunning = False
        #self._greenLed.setValue(0)
        self.join(5)
        if self.isAlive:
            return False
        return True

    def worker(self):
        logging.info("se12: Worker start")
        
        loginReq = True
        startupReq = True
        keyConfigReq = True

        while self._isRunning:
            actions = []
            
            res, statusRegister = self.readStatusRegister()
            if res:
                if statusRegister[0] == "B":
                    keyConfigReq = True
                    loginReq = True
                    startupReq = True
                    logging.info("se12: Module is On")

            if keyConfigReq:
                self.keyboardConfig()
                keyConfigReq = False

            if loginReq:
                act = {'Action': "Login", 'Value': "STARTUP" if startupReq else "" }
                actions.append(act)
                loginReq = False
                startupReq = False    

            res, bufferStatusRegister = self.readBufferStateRegister()
            if res:
                #self._greenLed.setValue(1)
                
                # Weight confirmed
                if bufferStatusRegister[12] == "1":
                    # Tare
                    res, tare = self.getTare()
                    if res:
                        act = {'Action': "SendTare", 'Value': tare}
                        actions.append(act)
                    # Weight
                    res, weight = self.getWeight()
                    if res:
                        act = {'Action': "SendWeight", 'Value': weight}
                        actions.append(act)
                
                # Key pressed
                if bufferStatusRegister[2] == "1":
                    res, keys = self.getKeyboardBuffer()
                    if res:
                        act = {'Action': "SendKeys", 'Value': keys}
                        actions.append(act)
                        if keys.endswith("c"):
                            keyConfigReq = True
                        elif keys.endswith("o"):
                            logging.info("se12: Module is Off")

                # Code F1 entered
                if bufferStatusRegister[4] == "1":
                    res, code = self.getF1Code()
                    if res:
                        act = {'Action': "F1", 'Value': code}
                        actions.append(act)
                # Code F2 entered
                if bufferStatusRegister[6] == "1":
                    res, code = self.getF2Code()
                    if res:
                        act = {'Action': "F2", 'Value': code}
                        actions.append(act)  
                # Code F3 entered
                if bufferStatusRegister[10] == "1":
                    res, code = self.getF3Code()
                    if res:
                        act = {'Action': "F3", 'Value': code}
                        actions.append(act)
                # Code F4 entered
                if bufferStatusRegister[5] == "1":
                    res, code = self.getF4Code()
                    if res:
                        act = {'Action': "F4", 'Value': code}
                        actions.append(act)
                # Code F5 entered
                if bufferStatusRegister[3] == "1":
                    res, code = self.getF5Code()
                    if res:
                        act = {'Action': "F5", 'Value': code}
                        actions.append(act) 
            else:
                #self._greenLed.setValue(0)
                #logging.info("se12: Status register read Fail")
                pass
            
            if len(actions) > 0:
                self._callback(self, actions)
            else:
                if self._idle:
                    self._idle(self)    
            
        
        #self._greenLed.setValue(0)
        logging.info("se12: Worker stop")
             

    def delay(self, sec):
        time.sleep(sec)

    def readUntil(self, terminator):
        resp = b""
        while True:
            b = self._ser.read(1)
            if len(b) == 0 or b == terminator:
                return str(resp, encoding="cp1251")
            resp += b

    def readStatusRegister(self):
        result = False
        data = ""
        req = b"\x02" + self._addr + b"\x0D{\x80}"
        time.sleep(0.05)
        self._ser.write(req)
        resp = self.readUntil(b"\0")
        #logging.info(resp)
        if re.match(r"^.{5}$", resp):
            result = True
            data = resp
        return result, data

    def readBufferStateRegister(self):
        result = False
        data = ""
        req = b"\x02" + self._addr + b"\x0D{\x81}"
        time.sleep(0.2)
        self._ser.write(req)
        resp = self.readUntil(b"\0")
        #logging.info(resp)
        if re.match(r"^[01]{16}$", resp):
            result = True
            data = resp
        return result, data
    
    def getWeight(self):
        result = False
        data = 0.0
        req = b"\x02" + self._addr + b"\x0D{\x8C}"
        time.sleep(0.05)
        self._ser.write(req)
        resp = self.readUntil(b"\0")
        #logging.info(resp)
        r = re.match(r"^[NS]{0,1}([ +-][ 0-9.]{7}) [ k][g]$", resp)
        if r:
            result = True
            w = r.group(1).replace(r" ", r"")
            data = float(w)   
        return result, data

    def getTare(self):
        result = False
        data = 0.0
        req = b"\x02" + self._addr + b"\x0D{\x8D}"
        time.sleep(0.05)
        self._ser.write(req)
        resp = self.readUntil(b"\0")
        r = re.match(r"^([ +-][ 0-9.]{7}) [ k][g]$", resp)
        if r:
            result = True
            w = r.group(1).replace(r" ", r"")
            data = float(w)   
        return result, data

    def getKeyboardBuffer(self):
        req = b"\x02" + self._addr + b"\x0D{\x82}"
        time.sleep(0.05)
        self._ser.write(req)
        resp = self.readUntil(b"\0")
        result = True
        data = resp   
        return result, data

    def getF1Code(self):
        req = b"\x02" + self._addr + b"\x0D{\x84}"
        time.sleep(0.05)
        self._ser.write(req)
        resp = self.readUntil(b"\0")
        result = True
        data = resp   
        return result, data

    def getF2Code(self):
        req = b"\x02" + self._addr + b"\x0D{\x86}"
        time.sleep(0.05)
        self._ser.write(req)
        resp = self.readUntil(b"\0")
        result = True
        data = resp   
        return result, data

    def getF3Code(self):
        req = b"\x02" + self._addr + b"\x0D{\x8A}"
        time.sleep(0.05)
        self._ser.write(req)
        resp = self.readUntil(b"\0")
        result = True
        data = resp   
        return result, data

    def getF4Code(self):
        req = b"\x02" + self._addr + b"\x0D{\x85}"
        time.sleep(0.05)
        self._ser.write(req)
        resp = self.readUntil(b"\0")
        result = True
        data = resp   
        return result, data

    def getF5Code(self):
        req = b"\x02" + self._addr + b"\x0D{\x83}"
        time.sleep(0.05)
        self._ser.write(req)
        resp = self.readUntil(b"\0")
        result = True
        data = resp   
        return result, data

    def display(self, text):
        result = False 
        data = ""
        lines = str(text).splitlines(False)
        for ln in lines:
            line = ln + "                    "
            data += line[0:20]
        if len(data) < 80:
            data += "                                                                                "
        data = data[0:80]
        time.sleep(0.2)
        self._ser.write(b"\x02")
        self._ser.write(self._addr)
        self._ser.write(b"\x0D{\xF0\x3F")
        self._ser.write(bytes(data, encoding="cp1251"))
        self._ser.write(b"}")
        resp = self.readUntil(b"}")
        if re.match(r"^OK$", resp):
            result = True
        return result

    def printLabel(self, label):
        result = False
        data = label
        time.sleep(0.2)
        self._ser.write(b"\x02")
        self._ser.write(self._addr)
        self._ser.write(b"\x0D{\xE0")
        self._ser.write(bytes(data, encoding="cp1251"))
        self._ser.write(b"\x00}")
        time.sleep(1.2)
        resp = self.readUntil(b"}")
        if re.match(r"^OK$", resp):
            result = True
        return result

    def buzz(self, blink=False):
        result = False
        data = b"B" if blink else b"b"
        time.sleep(0.2)
        self._ser.write(b"\x02")
        self._ser.write(self._addr)
        self._ser.write(b"\x0D{\xF9")
        self._ser.write(data)
        self._ser.write(b"}")
        resp = self.readUntil(b"}")
        if re.match(r"^OK$", resp):
            result = True
        return result

    # | F1 | F2 | F3 | F4 | F5 | PRINT | F | M+ | MR | CE | left | right | arrow up | down | PROGRAM | OFF |
    def keyboardConfig(self, config="0900010006000001"):
        result = False
        data = bytes(config, encoding="cp1251")
        time.sleep(0.2)
        self._ser.write(b"\x02")
        self._ser.write(self._addr)
        self._ser.write(b"\x0D{\xF6")
        self._ser.write(data)
        self._ser.write(b"}")
        resp = self.readUntil(b"}")
        if re.match(r"^OK$", resp):
            logging.info("se12: Keyboard config '%s'" % config)
            result = True
        return result

    def keyPress(self, keycode="FF"):
        result = False
        data = bytes(keycode, encoding="cp1251")
        time.sleep(0.2)
        self._ser.write(b"\x02")
        self._ser.write(self._addr)
        self._ser.write(b"\x0D{\xF9C")
        self._ser.write(data)
        self._ser.write(b"}")
        resp = self.readUntil(b"}")
        if re.match(r"^OK$", resp):
            logging.info("se12: Key press '%s'" % keycode)
            result = True
        return result  

class Se12Serial():
    def __init__(self, port, baudrate):
        self._ser = serial.Serial(port, baudrate, timeout=0.5)

    def read(self, size=1):
        return self._ser.read(size)

    def write(self, data):
        return self._ser.write(data)

class Se12Socket():
    def __init__(self, host, port):
        self._sock = socket.socket()
        self._sock.settimeout(0.5)
        self._sock.connect((host, port))

        #self._orangeLed = onionGpio.OnionGpio(18)
        #self._orangeLed.setOutputDirection(0)

    def read(self, size=1):
        #self._orangeLed.setValue(1)
        try:
            res = self._sock.recv(size)
        except Exception as ex:
            res = b""
        #self._orangeLed.setValue(0)
        return res

    def write(self, data):
        #self._orangeLed.setValue(1)
        try:
            res = self._sock.send(data)
        except Exception as ex:
            res = 0
        #self._orangeLed.setValue(0)
        return res
    


# 00 - klawisz 0,           10 - klawisz CE,
# 01 - klawisz 1,           11 - klawisz F,
# 02 - klawisz 2,           12 - klawisz PRINT,
# 03 - klawisz 3,           13 - klawisz M+,
# 04 - klawisz 4,           14 - klawisz PROGRAM,
# 05 - klawisz 5,           15 - klawisz ?0?,
# 06 - klawisz 6,           16 - klawisz CLR,
# 07 - klawisz 7,           17 - klawisz T/on,
# 08 - klawisz 8,           18 - klawisz MR,
# 09 - klawisz 9,           19 - klawisz OFF,
# 0A - klawisz przecinka,   1A - klawisz F1,
# 0B - klawisz ENTER,       1B - klawisz F2,
# 0C - klawisz ?,           1C - klawisz F3,
# 0D - klawisz ?,           1D - klawisz F4,
# 0E - klawisz ?,           1E - klawisz F5,
# 0F - klawisz ?,           FF - brak klawisza.

# 0- klawisz 0,             k - klawisz CE,
# 1- klawisz 1,             f - klawisz F,
# 2- klawisz 2,             P - klawisz PRINT,
# 3- klawisz 3,             m - klawisz M+,
# 4- klawisz 4,             s - klawisz PROGRAM,
# 5- klawisz 5,             z - klawisz ?0?,
# 6- klawisz 6,             c - klawisz CLR,
# 7- klawisz 7,             t - klawisz T/on,
# 8- klawisz 8,             r - klawisz MR,
# 9- klawisz 9,             o - klawisz OFF,
# , - klawisz przecinka,    A - klawisz F1,
# e - klawisz ENTER,        B - klawisz F2,
# g- klawisz ?,             C - klawisz F3,
# d- klawisz ?,             D - klawisz F4,
# p- klawisz ?,             E - klawisz F5,
# l - klawisz ?.