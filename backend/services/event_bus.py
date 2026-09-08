import asyncio
from typing import Dict, List, AsyncGenerator
from backend.models import SSEEvent

class EventBus:
    def __init__(self):
        self.subscribers: Dict[str, List[asyncio.Queue]] = {}
        # Store events per mission so late subscribers get replay
        self.history: Dict[str, List[SSEEvent]] = {}

    async def publish(self, mission_id: str, event: SSEEvent):
        # Always store in history first
        if mission_id not in self.history:
            self.history[mission_id] = []
        self.history[mission_id].append(event)

        # Deliver to all live subscribers
        if mission_id in self.subscribers:
            for queue in self.subscribers[mission_id]:
                await queue.put(event)

    async def subscribe(self, mission_id: str) -> AsyncGenerator[SSEEvent, None]:
        if mission_id not in self.subscribers:
            self.subscribers[mission_id] = []
        queue: asyncio.Queue = asyncio.Queue()
        self.subscribers[mission_id].append(queue)

        # Replay any events that fired before this subscriber connected
        for past_event in self.history.get(mission_id, []):
            await queue.put(past_event)

        try:
            while True:
                event = await asyncio.wait_for(queue.get(), timeout=120)
                if event is None:
                    break
                yield event
        except asyncio.TimeoutError:
            pass
        finally:
            if mission_id in self.subscribers and queue in self.subscribers[mission_id]:
                self.subscribers[mission_id].remove(queue)

event_bus = EventBus()
