from array import array
from types import SimpleNamespace
import unittest
from unittest.mock import Mock

import test_app
from pc.aubar_control.audio import Recording, AudioError
from pc.aubar_control.microphone_probe import MicrophoneProbe


class ProbeTests(unittest.TestCase):
    def probe(self,values):
        backend=Mock();backend.get_stream.return_value=SimpleNamespace(active=False)
        recording=Recording(array('h',values).tobytes(),48000)
        probe=MicrophoneProbe(backend);probe.arm()
        return probe,backend,recording

    def test_playback_preserves_pcm_level_and_sample_rate(self):
        probe,backend,recording=self.probe([1000,-2000]*200)
        message=probe.play(recording)
        self.assertEqual(backend.play.call_args.args[0].tobytes(),recording.pcm)
        self.assertEqual(backend.play.call_args.kwargs,dict(samplerate=48000,blocking=False))
        self.assertIn('Pico de entrada',message)
        backend.stop.assert_called_once()

    def test_low_input_and_clipping_are_reported_separately(self):
        for values,expected in (([100,-100]*200,'muy baja'),([32767,-32768]*200,'saturando')):
            probe,backend,recording=self.probe(values)
            self.assertIn(expected,probe.play(recording))

    def test_cancel_before_worker_never_starts_late_playback(self):
        probe,backend,recording=self.probe([1000]*200)
        probe.stop()
        self.assertEqual(probe.play(recording),'Prueba detenida.')
        backend.play.assert_not_called()
        probe.arm();probe.play(recording)
        backend.play.assert_called_once()

    def test_output_error_is_safe_and_stop_failure_does_not_break_cleanup(self):
        probe,backend,recording=self.probe([1000]*200)
        backend.play.side_effect=OSError('internal device details')
        backend.stop.side_effect=OSError('internal stop details')
        with self.assertRaises(AudioError) as caught:probe.play(recording)
        self.assertNotIn('internal',str(caught.exception))
        probe.stop()


class ProbePanelTests(unittest.TestCase):
    setUp=test_app.AppTests.setUp
    tearDown=test_app.AppTests.tearDown
    pump=test_app.AppTests.pump

    def start_probe(self):
        self.app.microphone_probe=Mock()
        self.app.microphone_probe.play.return_value='Prueba terminada.'
        self.app.recognizer.recognize=Mock(side_effect=AssertionError('Probe must not recognize'))
        self.app.ai_service.submit=Mock(side_effect=AssertionError('Probe must not query'))
        self.app.test_microphone()
        self.pump(lambda:self.app.audio_phase=='warming')
        self.app.capture.ready.set()
        self.pump(lambda:self.app.audio_phase=='recording')
        self.audio.streams[-1].emit(array('h',[3000,-3000]*4000).tobytes())

    def test_probe_records_then_replays_without_commands_queries_or_retained_audio(self):
        self.start_probe()
        self.app.stop_recording(object()) # Releasing the test button is not a manual capture release.
        self.assertEqual(self.app.audio_phase,'recording')
        self.app.stop_recording()
        self.pump(lambda:self.app.recognition_message.get()=='Prueba terminada.')
        self.app.microphone_probe.play.assert_called_once()
        self.app.recognizer.recognize.assert_not_called()
        self.app.ai_service.submit.assert_not_called()
        self.assertEqual(self.session.actions,[])
        self.assertEqual(self.app.speech.calls,[])
        self.assertIsNone(self.app.last_recording)
        self.assertIsNone(self.app._probe_timer)
        self.assertEqual(self.app.audio_phase,'idle')
        self.assertFalse(self.app.auto_enabled.get())

    def test_stop_during_probe_capture_discards_sample_without_replay(self):
        self.start_probe();self.app.test_microphone()
        self.pump(lambda:self.app.audio_phase=='idle')
        self.app.microphone_probe.play.assert_not_called()
        self.app.recognizer.recognize.assert_not_called()
        self.assertIsNone(self.app._probe_timer)
        self.assertIsNone(self.app.last_recording)
