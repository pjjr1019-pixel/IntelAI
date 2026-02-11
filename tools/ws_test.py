import asyncio
import json
import sys

try:
    import websockets
except ImportError:
    print("websockets not installed")
    sys.exit(2)

async def main():
    uri = 'ws://127.0.0.1:8000/ws/trends?geo=US'
    try:
        async with websockets.connect(uri) as ws:
            print('Connected to', uri)
            msg = await ws.recv()
            print('Received:', msg[:1000])
    except Exception as e:
        print('Connection error:', e)

if __name__ == '__main__':
    asyncio.get_event_loop().run_until_complete(main())
