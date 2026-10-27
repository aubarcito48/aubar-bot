"""Cross-component acceptance scenarios; external devices/decoders stay simulated."""
import tkinter as tk
import unittest

from audio_fakes import FakeAudio
import test_app
from test_automatic import pcm
from test_recognition import FakeBackend, result
from test_session import FakeSerial
from test_playback_gate import Clock, ControlledSpeech
from pc.aubar_control.app import AubarApp
from pc.aubar_control.audio import InputDevice, MicrophoneCapture
from pc.aubar_control.playback_gate import PlaybackGate
from pc.aubar_control.recognition import LocalRecognizer
from pc.aubar_control.session import DevicePort, DeviceSession
from pc.aubar_control.config import load_groq_config


class AvatarSerial(FakeSerial):
    """Firmware-shaped state and ACKs at the serial boundary, including ACK loss."""
    def __init__(self, **kwargs):
        super().__init__(version=4, **kwargs)
        self.state=dict(mode='manual',expression='neutral',look='centro',animation='none')

    def write(self,data):
        if data==b'STATUS\n':
            self.requests.append(data)
            self.response.extend(('OK STATUS '+' '.join(f'{k}={v}' for k,v in self.state.items())+'\n').encode())
            return len(data)
        if data.startswith((b'EXPRESSION ',b'LOOK ',b'ANIMATION ',b'MODE ')):
            command,value,*direction=data.decode().split()
            if command=='MODE':
                self.state['mode']=value
            elif command=='LOOK':
                self.state.update(mode='manual',look=value)
            else:
                self.state.update(mode='manual',animation='none')
                self.state['expression' if command=='EXPRESSION' else 'animation']=value
                if direction:
                    self.state['look']=direction[0]
        return super().write(data)


class VoiceWorkflowTests(unittest.TestCase):
    pump=test_app.AppTests.pump

    def setUp(self):
        self.root=tk.Tk();self.root.withdraw()
        self.audio=FakeAudio()
        self.decoder=FakeBackend(result('aubar contento'))
        self.voice=ControlledSpeech()
        self.ports=[]
        def serial_factory(**kwargs):
            port=AvatarSerial(**kwargs)
            self.ports.append(port)
            return port
        self.app=AubarApp(self.root,session=DeviceSession(serial_factory,timeout=.05),
            port_provider=lambda:[DevicePort('COM3','ESP32 simulado',True)],
            capture=MicrophoneCapture(self.audio),
            audio_provider=lambda:[InputDevice(1,'Entrada simulada','Prueba',True)],
            recognizer=LocalRecognizer(backend=self.decoder),speech=self.voice,
            config_loader=lambda:load_groq_config(None,environ={}))
        self.clock=Clock()
        self.app.playback_gate=PlaybackGate(self.clock)
        self.pump(lambda:not self.app.busy and not self.app.audio_scan_busy)
        self.app.connect()
        self.pump(lambda:self.app.connected and not self.app.busy)
        self.start_listening()

    def tearDown(self):
        self.app.close()

    def start_listening(self):
        self.app.auto_enabled.set(True);self.app.toggle_automatic()
        self.pump(lambda:self.app.auto_running)
        self.audio.streams[-1].emit(pcm(.02))
        self.pump(lambda:self.app.automatic_capture.listening.is_set())
        self.audio.streams[-1].emit(pcm(.4))

    def phrase(self,text):
        self.decoder.final=result(text)
        self.audio.streams[-1].emit(pcm(.5,4000)+pcm(.8))

    def finish_response(self):
        self.voice.finish()
        self.pump(lambda:self.app._speech_future is None)
        self.clock.advance(.36)
        self.pump(lambda:self.app.automatic_capture.listening.is_set())

    def actions(self):
        return [request for port in self.ports for request in port.requests
                if request.startswith((b'EXPRESSION ',b'LOOK ',b'ANIMATION ',b'MODE '))]

    def test_combined_actions_rejections_and_mode_complete_a_listening_cycle(self):
        self.phrase('aubar enojado derecha')
        self.pump(lambda:len(self.voice.calls)==1)
        self.assertEqual(self.actions(),[b'EXPRESSION enojado derecha\n'])
        self.assertEqual(self.app.values['expression'].get(),'Enojado')
        self.assertEqual(self.app.values['look'].get(),'Derecha')
        self.assertEqual(self.voice.calls,['Estoy enojado mirando a la derecha.'])
        self.assertFalse(self.app.automatic_capture.listening.is_set())
        # Audio entering while the response plays cannot become another command.
        self.phrase('aubar celebrar izquierda')
        self.assertTrue(self.app.automatic_capture.utterances.empty())
        self.finish_response()
        for text in ('contento','aubar hoy hace frio','aubar no te pongas contento'):
            self.phrase(text)
            expected=text.removeprefix('aubar ')
            self.pump(lambda:self.app.recognition_text.get()==expected)
            self.pump(lambda:self.app.automatic_capture.listening.is_set())
            self.assertEqual(self.app.recognized_query,expected if text.startswith('aubar ') else None)
            self.assertEqual(len(self.actions()),1)
            self.assertEqual(len(self.voice.calls),1)
        self.phrase('aubar celebrar izquierda')
        self.pump(lambda:len(self.voice.calls)==2)
        self.assertEqual(self.actions()[-1],b'ANIMATION celebrate izquierda\n')
        self.assertEqual(self.app.animation_value.get(),'Animación: Celebrar')
        self.assertEqual(self.app.values['look'].get(),'Izquierda')
        self.assertEqual(self.voice.calls[-1],'Voy a celebrar mirando a la izquierda.')
        self.finish_response()
        self.phrase('aubar modo automatico')
        self.pump(lambda:len(self.voice.calls)==3)
        self.assertEqual(self.actions()[-1],b'MODE auto\n')
        self.assertEqual(self.app.values['mode'].get(),'Automático')
        self.finish_response()
        self.assertEqual(len(self.actions()),3)
        self.assertEqual(len(self.voice.calls),3)

    def test_lost_ack_keeps_action_uncertain_and_reconnect_never_replays_it(self):
        self.ports[-1].drop_ack=True
        self.phrase('aubar contento')
        self.pump(lambda:not self.app.connected and not self.app.busy and self.app.audio_phase=='idle')
        self.assertEqual(self.actions(),[b'EXPRESSION contento\n'])
        self.assertEqual(self.ports[0].state['expression'],'contento')
        self.assertEqual(self.voice.calls,[])
        self.assertFalse(self.app.auto_enabled.get())
        self.app.connect()
        self.pump(lambda:self.app.connected and not self.app.busy)
        self.assertEqual(len(self.actions()),1)
        self.assertEqual(self.voice.calls,[])
        self.assertFalse(self.app.auto_enabled.get())
        self.start_listening()
        self.phrase('aubar derecha')
        self.pump(lambda:len(self.voice.calls)==1)
        self.assertEqual(self.actions(),[b'EXPRESSION contento\n',b'LOOK derecha\n'])
        self.assertEqual(self.voice.calls,['Miro a la derecha.'])
        self.finish_response()

    def test_muted_action_then_interruption_preserves_explicit_microphone_off(self):
        self.app.speech_enabled.set(False);self.app.toggle_speech()
        self.phrase('aubar contento')
        self.pump(lambda:len(self.actions())==1 and not self.app.busy and self.app.audio_phase=='idle')
        self.assertEqual(self.app.values['expression'].get(),'Contento')
        self.assertEqual(self.voice.calls,[])
        self.app.speech_enabled.set(True);self.app.toggle_speech()
        self.pump(lambda:self.app.automatic_capture.listening.is_set())
        self.assertEqual(self.voice.calls,[])
        self.phrase('aubar enojado derecha')
        self.pump(lambda:len(self.voice.calls)==1)
        stream=self.audio.streams[-1]
        self.app.auto_enabled.set(False);self.app.toggle_automatic()
        self.pump(lambda:self.app.audio_phase=='idle')
        self.app.stop_speech()
        self.pump(lambda:self.app._speech_future is None)
        self.clock.advance(.36)
        self.root.update()
        self.assertFalse(self.app.auto_enabled.get())
        self.assertFalse(self.app.automatic_capture.listening.is_set())
        self.assertTrue(stream.closed)
        self.start_listening()
        self.phrase('aubar centro')
        self.pump(lambda:len(self.voice.calls)==2)
        self.assertEqual(self.actions()[-1],b'LOOK centro\n')
        self.assertEqual(self.voice.calls[-1],'Miro al centro.')
        self.finish_response()
