"""Bounded latest-response policy, scoped to a connection and cancellation epoch."""
from dataclasses import dataclass
import time


@dataclass(frozen=True)
class PendingReply:
    connection: int
    generation: int
    text: str
    created_at: float


class ReplyQueue:
    MAX_AGE = 15.0

    def __init__(self, clock=time.monotonic, max_age=MAX_AGE):
        self.clock=clock
        self.max_age=max_age
        self.generation=0
        self._pending=None

    @property
    def pending(self):
        if self._pending is not None and self.clock()-self._pending.created_at>=self.max_age:
            self._pending=None
        return self._pending

    def put(self, text, connection, generation):
        if generation!=self.generation:
            return False
        self._pending=PendingReply(connection,generation,text,self.clock())
        return True

    def peek(self, connection):
        reply=self.pending
        if reply is not None and (reply.connection!=connection or reply.generation!=self.generation):
            self._pending=None
            return None
        return reply

    def take(self, connection):
        reply=self.peek(connection)
        self._pending=None
        return reply

    def discard(self):
        self._pending=None

    def cancel(self):
        self.generation+=1
        self.discard()
