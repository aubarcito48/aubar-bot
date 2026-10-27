from array import array
import unittest

from audio_fakes import FakeAudio
from pc.aubar_control.audio import AudioError, MicrophoneCapture


class AudioTests(unittest.TestCase):
    def setUp(self):
        self.backend = FakeAudio()
        self.capture = MicrophoneCapture(self.backend)

    def test_no_stream_without_activation_and_early_release_cancels_start(self):
        self.assertFalse(self.capture.start(1))
        self.capture.arm()
        self.capture.cancel()
        self.assertFalse(self.capture.start(1))
        self.assertEqual(self.backend.streams, [])

    def test_release_gates_samples_immediately_and_finish_closes_stream(self):
        self.capture.arm()
        self.assertTrue(self.capture.start(1))
        self.assertFalse(self.capture.ready.is_set())
        stream = self.backend.streams[-1]
        pcm = array('h', [12000, -12000]*4000).tobytes()
        stream.emit(pcm)
        self.assertTrue(self.capture.ready.is_set())
        self.assertGreater(self.capture.level, 0)
        self.capture.cancel()
        stream.emit(pcm)  # Data after release must not enter the recording.
        recording = self.capture.finish()
        self.assertEqual(recording.pcm, pcm)
        self.assertEqual(recording.duration, 0.5)
        self.assertTrue(stream.closed)
        self.assertFalse(stream.started)
        self.assertFalse(self.capture.requested.is_set())

    def test_maximum_is_exactly_ten_seconds(self):
        self.capture.arm()
        self.capture.start(1)
        self.backend.streams[-1].emit(array('h', [1000]*161000).tobytes())
        self.assertTrue(self.capture.limit_reached)
        self.assertFalse(self.capture.requested.is_set())
        self.assertEqual(self.capture.finish().duration, 10)

    def test_fallback_preserves_actual_sample_rate(self):
        self.backend.reject_16k = True
        self.capture.arm()
        self.capture.start(1)
        self.backend.streams[-1].emit(array('h', [4000]*4800).tobytes())
        recording = self.capture.finish()
        self.assertEqual(recording.sample_rate, 48000)
        self.assertEqual(recording.duration, 0.1)

    def test_open_error_and_repeated_sessions_release_resources(self):
        self.backend.reject_open = True
        self.capture.arm()
        with self.assertRaises(AudioError):
            self.capture.start(1)
        self.assertFalse(self.capture.requested.is_set())
        self.assertIsNone(self.capture.stream)
        self.backend.reject_open = False
        for _ in range(2):
            self.capture.arm()
            self.capture.start(1)
            self.capture.finish()
        self.assertTrue(all(stream.closed for stream in self.backend.streams))


if __name__ == '__main__':
    unittest.main()
