import socketio

sio = socketio.AsyncServer(cors_allowed_origins="*", async_mode="asgi")
