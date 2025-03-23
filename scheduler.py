import asyncio
import threading
import time

import schedule


class Scheduler:
    def __init__(self, func, schedule_time):
        self.func = func
        self.schedule_time = schedule_time
        self.thread = threading.Thread(target=self.run, daemon=True)
        self.thread.start()

    def run_async_task(self):
        """Runs the async function inside an event loop in a new thread."""
        asyncio.run(self.func())

    def schedule_task(self):
        """Schedules the async task to run at 07:55 every day."""
        schedule.every().day.at(self.schedule_time).do(
            lambda: threading.Thread(target=self.run_async_task).start()
        )

    def run(self):
        while True:
            schedule.run_pending()
            time.sleep(60)
