from asyncio import get_event_loop
from serial_asyncio import open_serial_connection

async def run():
    reader, writer = await open_serial_connection(url='/dev/ttyACM0', baudrate=9600)
    while True:
        line = await reader.readline()
        print(str(line, 'utf-8'))

loop = get_event_loop()
loop.run_until_complete(run())