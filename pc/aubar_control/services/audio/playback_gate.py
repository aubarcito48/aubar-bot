"""One microphone gate for test speech, action replies and future AI text."""
import time


class PlaybackGate:
    def __init__(self, clock=time.monotonic, echo_delay=.35):
        self.clock=clock
        self.echo_delay=echo_delay
        self._generation=0
        self._active=None
        self._release_at=0

    @property
    def active(self):
        return self._active is not None

    @property
    def blocked(self):
        return self.active or self.clock()<self._release_at

    def begin(self):
        self._generation+=1
        self._active=self._generation
        return self._active

    def finish(self, token):
        if token is not None and token==self._active:
            self._active=None
            self._release_at=self.clock()+self.echo_delay
