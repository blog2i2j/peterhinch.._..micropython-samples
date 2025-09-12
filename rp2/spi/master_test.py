# master_test.py Test script for spi_dma.py

# Released under the MIT License (MIT). See LICENSE.
# Copyright (c) 2025 Peter Hinch

# Performs SPI output: check on scope or LA.
# TODO:
# Fails if baudrate >= 9MHz
# Problem with pin nos?
# 11 Sept slave works bidirectionally with tx.py, but with this code slave receives
# nothing, but responds with correct data. Waveforms look identical. MOSI data looks correct.
# Slave gets correct data with unidirectional setup (no ibuf)
# 45us after last clock edge, clk emits a 250ns pulse. CS/ goes high 724us after last clock
# I think spurious clk is screwing RX SM.
from machine import Pin
import asyncio
from .spi_master import SpiMaster

pin_cs = Pin(17, Pin.OUT, value=1)
pin_sck = Pin(18, Pin.OUT, value=0)
pin_mosi = Pin(19, Pin.OUT, value=0)
pin_miso = Pin(16, Pin.IN)

tsf = asyncio.ThreadSafeFlag()


def callback():  # Hard ISR
    pin_cs(1)  # Decrease deassert time from 724us to 93us but still fails
    tsf.set()  # Flag user code that transfer is complete


buf = bytearray(100)
spi = SpiMaster(6, 1_000_000, pin_sck, pin_mosi, callback, miso=pin_miso, ibuf=buf)


async def send(data):
    tsf.clear()  # no effect
    pin_cs(0)  # Assert CS/
    spi.write(data)  # "Immediate" return: minimal blocking.
    await tsf.wait()  # Wait for transfer complete (other tasks run)
    pin_cs(1)  # Deassert CS/


async def main():
    src_data = bytearray(b"\xFF\x55\xAA\x00the quick brown fox jumps over the lazy dog")
    n = 0
    while True:
        await send(src_data)
        print(n, bytes(buf[: len(src_data)]))
        await asyncio.sleep(1)
        n += 1
        n &= 0xFF
        src_data[0] = n


try:
    asyncio.run(main())
except KeyboardInterrupt:
    spi.deinit()
    asyncio.new_event_loop()
