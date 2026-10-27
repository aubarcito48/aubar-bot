class FakeStream:
    def __init__(self, **kwargs):
        self.callback = kwargs['callback']
        self.finished_callback = kwargs['finished_callback']
        self.started = False
        self.closed = False

    def start(self):
        self.started = True

    def abort(self):
        self.started = False
        self.finished_callback()

    def close(self):
        self.closed = True

    def emit(self, pcm, status=None):
        self.callback(pcm, len(pcm)//2, None, status)


class FakeAudio:
    def __init__(self):
        self.streams = []
        self.reject_16k = False
        self.reject_open = False

    def query_devices(self, device, kind):
        return {'default_samplerate': 48000}

    def check_input_settings(self, **kwargs):
        if self.reject_16k and kwargs['samplerate'] == 16000:
            raise ValueError('Unsupported rate')

    def RawInputStream(self, **kwargs):
        if self.reject_open:
            raise OSError('Unavailable microphone')
        stream = FakeStream(**kwargs)
        self.streams.append(stream)
        return stream
