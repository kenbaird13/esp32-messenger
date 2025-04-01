import asyncio
import websockets
import sqlite3
import json
from aiohttp import web
import traceback

# SQLite database file
DB_FILE = "messages.db"

def init_db():
    """Initialize the SQLite database and create the messages table if it doesn't exist."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sender TEXT,
            message TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

async def store_message(sender, message):
    """Store a new message in the database."""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO messages (sender, message) VALUES (?, ?)", (sender, message))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Error storing message: {e}")
        print(traceback.format_exc())

async def get_messages():
    """Retrieve the last 10 messages from the database (most recent first)."""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("SELECT sender, message, timestamp FROM messages ORDER BY id DESC LIMIT 10")
        messages = cursor.fetchall()
        conn.close()
        return messages
    except Exception as e:
        print(f"Error retrieving messages: {e}")
        print(traceback.format_exc())
        return []

# Keep track of all connected WebSocket clients
clients = set()

async def websocket_handler(websocket, path):
    """Handle new WebSocket connections, store and broadcast messages."""
    print("New client connected.")
    clients.add(websocket)
    try:
        # Send the last 10 messages to the newly connected client
        messages = await get_messages()
        for msg in reversed(messages):  # Send in chronological order
            await websocket.send(json.dumps({"sender": msg[0], "message": msg[1], "timestamp": msg[2]}))

        # Listen for messages from this client
        async for message in websocket:
            try:
                data = json.loads(message)
                sender = data.get("sender", "Unknown")
                msg_text = data.get("message", "")

                print(f"Received message from {sender}: {msg_text}")

                # Store the message in the database
                await store_message(sender, msg_text)

                # Broadcast the message to all connected clients
                for client in clients:
                    await client.send(json.dumps({"sender": sender, "message": msg_text}))
            except Exception as e:
                print(f"Error handling message: {e}")
                print(traceback.format_exc())

    except websockets.exceptions.ConnectionClosed:
        print("Client disconnected.")
    except Exception as e:
        print(f"WebSocket error: {e}")
        print(traceback.format_exc())
    finally:
        # Remove client from the active list when disconnected
        clients.remove(websocket)

# Serve the web UI (index.html)
async def index(request):
    """Serve the chat web UI."""
    return web.FileResponse("index.html")

# Create an aiohttp web application for serving the UI
app = web.Application()
app.router.add_get("/", index)

# Initialize the database before starting the server
init_db()

# Start WebSocket server
async def start_websocket_server():
    """Start the WebSocket server and keep it running."""
    try:
        print("Starting WebSocket server on ws://0.0.0.0:8765...")
        async with websockets.serve(websocket_handler, "0.0.0.0", 8765):
            await asyncio.Future()  # Keeps the server running indefinitely
    except Exception as e:
        print(f"WebSocket server failed: {e}")
        print(traceback.format_exc())

# Function to start the web server
async def start_web_server():
    """Start the web server to serve the UI at http://localhost:8080."""
    try:
        print("Starting web server on http://0.0.0.0:8080...")
        web_server = web.AppRunner(app)
        await web_server.setup()
        site = web.TCPSite(web_server, "0.0.0.0", 8080)
        await site.start()
    except Exception as e:
        print(f"Web server failed: {e}")
        print(traceback.format_exc())

async def main():
    """Run both the web server and WebSocket server concurrently."""
    try:
        await asyncio.gather(start_web_server(), start_websocket_server())
    except Exception as e:
        print(f"Fatal error in main(): {e}")
        print(traceback.format_exc())

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nServer shutting down gracefully...")
    except Exception as e:
        print(f"Unhandled error: {e}")
        print(traceback.format_exc())
