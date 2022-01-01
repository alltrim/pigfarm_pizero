from serial import Serial
from time import sleep

s = Serial(port="/dev/serial0", baudrate=57600)

while True:
    s.write(b"\x0201\x0D{\xF9B}")
    sleep(1)
