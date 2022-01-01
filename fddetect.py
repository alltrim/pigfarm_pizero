# coding=cp1251

import os
import time
from threading import Thread
import logging

class FdDetector(Thread):
    def __init__(self, callback):
        Thread.__init__(self)
        self._callback = callback
        self.status = None
        self._isRunning = False

    def run(self):
        if not self._isRunning:
            self._isRunning = True
            self.detect()

    def abort(self):
        self._isRunning = False
        self.join(5)
        if self.isAlive:
            return False
        return True

    def detect(self):
        path = "/tmp/mounts/USB-A1"
        while self._isRunning:
            if os.path.exists(path):
                if self.status == None or self.status == False:
                    self.status = True
                    self._callback(True)
            else:
                if self.status == None or self.status == True:
                    self.status = False
                    self._callback(False)
            time.sleep(0.5) 

def walk(path="/tmp/mounts/USB-A1"):
    for d, dirs, files in os.walk(path):
        for file in files:
            logging.info("  " + os.path.join(d, file))

def onCange(status):
    if status:
        logging.info("FlashDrive plugged")
        walk()
    else:
        logging.info("FlashDrive unplugged")


def loop():
    detector = FdDetector(onCange)
    detector.start()

    counter = 0
    while True:
        logging.info("Main %r" % counter)
        counter += 1
        time.sleep(10)

if __name__ == "__main__":
    loop()




