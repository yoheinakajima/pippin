# server.py

import asyncio
from fastapi import FastAPI, WebSocket
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
import uvicorn
from threading import Thread
import json
import datetime

import shared_data
from framework.memory import Memory  # Ensure correct import path for Memory

app = FastAPI()

# Mount the 'static' directory for static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Serve the index.html template
@app.get("/")
async def get():
    return HTMLResponse(open("templates/index.html").read())

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    memory = Memory()
    while True:
        # Fetch the last 10 activity logs from the database
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
                # Parse state_changes JSON string
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

        # Prepare data to send
        data = {
            'current_activity': shared_data.current_activity,
            'state': shared_data.state.to_dict(),
            'activity_history': activity_history,
            'summary_data': summary_data  # Include summary in the data
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

def run_server():
    uvicorn.run(app, host="0.0.0.0", port=8000)

# Run the FastAPI server in a separate thread
server_thread = Thread(target=run_server, daemon=True)
server_thread.start()
