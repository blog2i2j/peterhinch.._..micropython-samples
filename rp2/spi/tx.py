# spi.tx.py Send data to SPI slave

# Released under the MIT License (MIT). See LICENSE.
# Copyright (c) 2025 Peter Hinch

# SPI slave receives data at up to 30MHz
# but return direction only works at 10MHz.

from machine import Pin, SPI
from time import sleep_ms


cs = Pin(17, Pin.OUT, value=1)  # Ensure CS/ is False before we try to receive.
pin_miso = Pin(16, Pin.IN)  # Not used: keep driver happy
pin_sck = Pin(18, Pin.OUT, value=0)
pin_mosi = Pin(19, Pin.OUT, value=0)

spi = SPI(0, baudrate=1_000_000, sck=pin_sck, mosi=pin_mosi, miso=pin_miso)


def send(obuf):
    obuf = bytearray(obuf)
    cs(0)
    spi.write_readinto(obuf, obuf)
    print("got", bytes(obuf))
    cs(1)
    sleep_ms(1000)


while True:
    send(b"The quick brown fox       ")
    send(b"jumps over the lazy dog. ")
