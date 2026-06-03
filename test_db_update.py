#!/usr/bin/env python3
"""Test script: update task status directly in database and see WS updates."""

import asyncio
import sys
from uuid import UUID

try:
    import asyncpg
except ImportError:
    print("Please install asyncpg: pip install asyncpg")
    sys.exit(1)


async def main():
    # Parse arguments
    if len(sys.argv) < 3:
        print("Usage: python test_db_update.py <task_id> <new_status>")
        print("Example: python test_db_update.py 550e8400-e29b-41d4-a716-446655440000 done")
        sys.exit(1)
    
    task_id_str = sys.argv[1]
    new_status = sys.argv[2]
    
    # Validate task ID
    try:
        task_id = UUID(task_id_str)
    except ValueError:
        print(f"✗ Invalid UUID: {task_id_str}")
        sys.exit(1)
    
    # Valid statuses
    valid_statuses = {"pending", "running", "done", "failed", "canceled"}
    if new_status not in valid_statuses:
        print(f"✗ Invalid status. Must be one of: {', '.join(valid_statuses)}")
        sys.exit(1)
    
    # Connect to database
    try:
        conn = await asyncpg.connect(
            host="localhost",
            port=5432,
            user="dev",
            password=None,
            database="development"
        )
    except Exception as e:
        print(f"✗ Database connection failed: {e}")
        sys.exit(1)
    
    try:
        # Check if task exists
        task = await conn.fetchrow(
            "SELECT id, status FROM tasks WHERE id = $1",
            task_id
        )
        
        if not task:
            print(f"✗ Task {task_id} not found")
            await conn.close()
            sys.exit(1)
        
        old_status = task["status"]
        print(f"Task: {task_id}")
        print(f"Old status: {old_status}")
        print(f"New status: {new_status}")
        
        # Update status (this will trigger NOTIFY)
        print("\nUpdating task status...")
        await conn.execute(
            "UPDATE tasks SET status = $1, updated_at = NOW() WHERE id = $2",
            new_status,
            task_id
        )
        
        print(f"✓ Status updated to '{new_status}'")
        print("\nThe WebSocket client should receive an update message shortly.")
        
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
