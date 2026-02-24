import asyncio
import websockets

async def test_ws():
    uri = "ws://localhost:8000/admin/ws/notifications"
    try:
        async with websockets.connect(uri) as websocket:
            print("Connected!")
            await websocket.send("ping")
            response = await websocket.recv()
            print(f"Received: {response}")
    except Exception as e:
        print(f"Failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_ws())
