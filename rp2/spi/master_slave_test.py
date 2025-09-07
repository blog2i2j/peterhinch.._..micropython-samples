# master_slave_test.py Test asynchronous interface of SpiSlave and master class

# Released under the MIT License (MIT). See LICENSE.
# Copyright (c) 2025 Peter Hinch

# Link pins
# 0-19 MOSI
# 1-18 SCK
# 2-17 CSN
# 3-16 MISO

from machine import Pin
import asyncio
from .spi_slave import SpiSlave
from .spi_master import SpiMaster


tsf = asyncio.ThreadSafeFlag()


def callback():  # Hard ISR
    print("cb")
    tsf.set()  # Flag user code that transfer is complete


# Sender uses nonblocking master
cs = Pin(17, Pin.OUT, value=1)  # Ensure CS/ is False before we try to receive.
pin_sck = Pin(18, Pin.OUT, value=0)
pin_mosi = Pin(19, Pin.OUT, value=0)
pin_miso = Pin(16, Pin.IN)
ibuf = bytearray(20)
spi = SpiMaster(4, 10_000_000, pin_sck, pin_mosi, callback, miso=pin_miso, ibuf=ibuf)
# Pins for slave
mosi = Pin(0, Pin.IN)
sck = Pin(1, Pin.IN)
csn = Pin(2, Pin.IN)
miso = Pin(3, Pin.OUT, value=0)
piospi = SpiSlave(buf=bytearray(300), sm_num=0, mosi=mosi, sck=sck, csn=csn, miso=miso)


async def send(data):
    cs(0)  # Assert CS/
    spi.write(data)  # "Immediate" return: minimal blocking.
    print("GH01")
    await tsf.wait()  # Wait for transfer complete (other tasks run)
    print("GH02")
    cs(1)  # Deassert CS/
    await asyncio.sleep_ms(100)
    print("Master received", ibuf)


async def receive(piospi):
    async for msg in piospi:
        print(f"Slave received: {len(msg)} bytes:")
        print(bytes(msg))
        print()


async def test():
    obuf = bytearray(range(512))  # Test data
    # piospi.write(b"Hello from slave", -1)  # Repeat
    rt = asyncio.create_task(receive(piospi))
    await asyncio.sleep_ms(0)  # Ensure receive task is running
    print("\nBasic test\n")
    await send(obuf[:256])
    await send(obuf[:20])
    await send(b"The quick brown fox jumps over the lazy dog")
    print("\nDone")


try:
    asyncio.run(test())
finally:
    piospi.deinit()
    spi.deinit()
    asyncio.new_event_loop()
