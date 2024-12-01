# main_async.py

import asyncio
from framework import shared_data
from framework.memory import Memory
from framework.activity_loader import load_activities
from framework.activity_selector import select_activity
import uvicorn
from fastapi import FastAPI, WebSocket
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
import os
import json
import time
import datetime

# Create FastAPI app
app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def get():
    return HTMLResponse(open(os.path.join("templates", "index.html")).read())

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    memory = Memory()
    while True:
        # Fetch the last 10 activity logs
        async with memory.get_db_connection() as db:
            cursor = await db.execute('''
                SELECT timestamp, activity, result, duration, state_changes
                FROM activity_logs
                ORDER BY id DESC
                LIMIT 10
            ''')
            rows = await cursor.fetchall()
            activity_history = []
            for row in rows:
                timestamp, activity, result, duration, state_changes_str = row
                state_changes = json.loads(state_changes_str) if state_changes_str else {}
                activity_history.append({
                    'timestamp': timestamp,
                    'activity': activity,
                    'result': result,
                    'duration': duration,
                    'state_changes': state_changes
                })

        # Calculate the 24-hour summary
        summary_data = await get_24_hour_summary(memory)

        data = {
            'current_activity': shared_data.current_activity,
            'state': shared_data.state.to_dict(),
            'activity_history': activity_history,
            'summary_data': summary_data  # Include summary in the WebSocket data
        }
        await websocket.send_json(data)
        await asyncio.sleep(1)

async def get_24_hour_summary(memory):
    """Get summary of activity counts and durations for the past 24 hours."""
    now = datetime.datetime.now()
    since = now - datetime.timedelta(hours=24)

    async with memory.get_db_connection() as db:
        cursor = await db.execute('''
            SELECT activity, COUNT(*) as count, SUM(duration) as total_duration
            FROM activity_logs
            WHERE timestamp >= ?
            GROUP BY activity
        ''', (since.isoformat(),))
        rows = await cursor.fetchall()

    summary = []
    for row in rows:
        activity, count, total_duration = row
        summary.append({
            'activity': activity,
            'count': count,
            'total_duration': total_duration or 0
        })
    return summary


async def run_server():
    config = uvicorn.Config(app=app, host="0.0.0.0", port=8000, log_level="info", lifespan="off")
    server = uvicorn.Server(config)
    await server.serve()

async def main_loop():
    memory = Memory()
    await memory.initialize()

    # Load activities dynamically
    activity_functions = load_activities()

    asyncio.create_task(snapshot_state(shared_data.state, memory, interval=60))

    while True:
        activity_name = await select_activity(shared_data.state, activity_functions, memory)
        activity_func = activity_functions[activity_name]

        # Set current activity with start time
        shared_data.current_activity['name'] = activity_name
        shared_data.current_activity['start_time'] = time.time()  # Store start time as UNIX timestamp

        print(f"Starting activity: {activity_name}")
        await activity_func(shared_data.state, memory)
        print(f"Activity {activity_name} completed.")

        # Update activity history
        shared_data.activity_history.append({
            'activity': activity_name,
            'state': shared_data.state.to_dict(),
            'timestamp': time.time()
        })
        if len(shared_data.activity_history) > 100:
            shared_data.activity_history.pop(0)

        print(f"Current State: Energy={shared_data.state.energy}, Happiness={shared_data.state.happiness}, XP={shared_data.state.xp}")
        print("-" * 40)

        # Reset current activity
        shared_data.current_activity['name'] = None
        shared_data.current_activity['start_time'] = None

        await asyncio.sleep(1)

async def snapshot_state(state, memory, interval=3600):
    while True:
        await asyncio.sleep(interval)
        await memory.store_state_snapshot(state)
        print("State snapshot stored.")

async def main():
    # Start the web server and main loop concurrently
    await asyncio.gather(
        run_server(),
        main_loop()
    )

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Program interrupted by user.")
