# master_slave_test.py Test asynchronous interface of SpiSlave and master class

# Released under the MIT License (MIT). See LICENSE.
# Copyright (c) 2025 Peter Hinch

from machine import Pin
import asyncio
from .spi_slave import SpiSlave


# Pins for slave
mosi = Pin(12, Pin.IN)
sck = Pin(13, Pin.IN)
csn = Pin(14, Pin.IN)
miso = Pin(15, Pin.OUT, value=0)
piospi = SpiSlave(buf=bytearray(300), sm_num=0, mosi=mosi, sck=sck, csn=csn, miso=miso)


async def receive(piospi):
    n = 0
    async for msg in piospi:
        piospi.write(f"Message {n} from slave")
        n += 1
        print(f"Slave received: {len(msg)} bytes:")
        print(bytes(msg))
        print()


async def test():
    obuf = bytearray(range(512))  # Test data
    rt = asyncio.create_task(receive(piospi))
    await asyncio.sleep_ms(0)  # Ensure receive task is running
    print("\nBasic test\n")
    while True:
        # piospi.write("hello")
        await asyncio.sleep(3)
    print("\nDone")


try:
    asyncio.run(test())
finally:
    piospi.deinit()
    asyncio.new_event_loop()
