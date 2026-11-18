from array import array
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import Mock

from pc.aubar_control.audio import Recording
from pc.aubar_control.recognition import RecognitionError
from pc.aubar_control.whisper_recognition import WhisperRecognizer


def segment(text,probability=.95,**kwargs):
    return SimpleNamespace(text=text,words=[SimpleNamespace(probability=probability) for _ in text.split()],
        avg_logprob=kwargs.get('avg_logprob',-.1),no_speech_prob=kwargs.get('no_speech_prob',.01),
        compression_ratio=kwargs.get('compression_ratio',1))


class WhisperRecognitionTests(unittest.TestCase):
    def recording(self,silent=False):
        return Recording(array('h',[0 if silent else 3000]*16000).tobytes(),16000)

    def decoder(self,segments):
        model=Mock()
        model.transcribe.return_value=(iter(segments),SimpleNamespace())
        factory=Mock(return_value=model)
        return WhisperRecognizer(backend=factory),factory,model

    def test_spanish_cpu_only_without_network_and_model_is_loaded_once(self):
        engine,factory,model=self.decoder([segment('Contame sobre el portfolio de Nahuel.')])
        result=engine.recognize(self.recording())
        self.assertEqual(result.query,'Contame sobre el portfolio de Nahuel.')
        self.assertEqual(factory.call_args.kwargs['device'],'cpu')
        self.assertEqual(factory.call_args.kwargs['compute_type'],'int8')
        self.assertTrue(factory.call_args.kwargs['local_files_only'])
        self.assertEqual(model.transcribe.call_args.kwargs['language'],'es')
        self.assertTrue(model.transcribe.call_args.kwargs['vad_filter'])
        self.assertFalse(model.transcribe.call_args.kwargs['condition_on_previous_text'])
        self.assertNotIn('initial_prompt',model.transcribe.call_args.kwargs)
        engine.prepare();factory.assert_called_once()

    def test_silence_does_not_load_or_invoke_the_decoder(self):
        engine,factory,_=self.decoder([])
        self.assertIsNone(engine.recognize(self.recording(silent=True)).query)
        factory.assert_not_called()

    def test_actions_require_higher_evidence_than_queries_and_negations_are_preserved(self):
        engine,_,_=self.decoder([segment('Mirá a la izquierda.')])
        self.assertEqual(engine.recognize_automatic(self.recording()).action.argument,'izquierda')
        engine,_,_=self.decoder([segment('Mirá a la izquierda.',probability=.7)])
        rejected=engine.recognize(self.recording())
        self.assertIsNone(rejected.action);self.assertIsNone(rejected.query)
        engine,_,_=self.decoder([segment('No mires a la izquierda.')])
        result=engine.recognize(self.recording())
        self.assertIsNone(result.action)
        self.assertEqual(result.query,'No mires a la izquierda.')

    def test_low_confidence_external_send_is_not_routed_as_a_query(self):
        engine,_,_=self.decoder([segment('enviá un WhatsApp a +5493511234567: Hola',probability=.7)])
        self.assertIsNone(engine.recognize(self.recording()).query)

    def test_unreliable_and_repetitive_segments_are_rejected_without_dropping_words(self):
        for settings in ({'no_speech_prob':.95},{'avg_logprob':-2},{'compression_ratio':3}):
            engine,_,_=self.decoder([segment('Mirá a la izquierda.',**settings)])
            result=engine.recognize(self.recording())
            self.assertIsNone(result.action);self.assertIsNone(result.query)
        engine,_,_=self.decoder([segment('Hola',probability=float('nan'))])
        self.assertIsNone(engine.recognize(self.recording()).query)

    def test_model_missing_is_a_local_error_not_a_download(self):
        with TemporaryDirectory() as directory:
            engine=WhisperRecognizer(model_path=Path(directory))
            with self.assertRaisesRegex(RecognitionError,'Falta Whisper local'):
                engine.prepare()

    def test_application_defaults_to_whisper(self):
        import inspect
        from pc.aubar_control.app import AubarApp
        self.assertIn('else WhisperRecognizer()',inspect.getsource(AubarApp.__init__))


if __name__=='__main__': unittest.main()
