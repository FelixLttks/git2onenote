import threading

import uvicorn
from fastapi import FastAPI
from fastapi.responses import HTMLResponse


class WebServer:
    def __init__(self):
        pass

    def start_server(self, async_func, host="127.0.0.1", port=5000):
        self.app = FastAPI()

        @self.app.get("/", response_class=HTMLResponse)
        async def root():
            return """
            <!DOCTYPE html>
            <html>
                <head>
                    <title>Git2OneNote</title>
                </head>
                <body>
                    <h1>Git2OneNote</h1>
                    <a href="/sync">Sync now</a>
                </body>
            </html>"""

        @self.app.get("/sync")
        async def sync():
            await async_func()
            return {"status": "success"}

        uvicorn.run(self.app, host=host, port=port)

    def run(self, async_func):
        print("Starting server")
        self.server_tread = threading.Thread(
            target=self.start_server, daemon=True, args=(async_func,)
        )
        self.server_tread.start()
        print("Server started")
