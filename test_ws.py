#!/usr/bin/env python3
"""Simple WebSocket test client for task status updates."""

import asyncio
import json
import sys

try:
    import websockets
except ImportError:
    print("Please install websockets: pip install websockets")
    sys.exit(1)


async def main():
    uri = "ws://localhost:8000/ws"
    
    try:
        print(f"Connecting to {uri}...")
        async with websockets.connect(uri) as ws:
            print("✓ Connected to WebSocket")
            print("\nListening for task status updates...")
            print("(Try updating a task status in another terminal to see updates)\n")
            
            async for message in ws:
                try:
                    data = json.loads(message)
                    task_id = data.get("task_id", "unknown")
                    status = data.get("status", "unknown")
                    operation = data.get("operation", "UPDATE")
                    print(f"📤 Task {task_id[:8]}... → status: {status} ({operation})")
                except json.JSONDecodeError:
                    print(f"📤 Received: {message}")
                    
    except KeyboardInterrupt:
        print("\n✓ Disconnected")
    except Exception as e:
        print(f"✗ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
