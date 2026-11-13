"""Check contextual face retention while the actual ESP32 animates speech."""
import argparse
from pathlib import Path
import re
import sys
import time

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from pc.aubar_control.session import DeviceSession
from pc.aubar_control.voice_commands import VoiceAction
from tools.test_portrait_usb import diagnostics


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port',default='COM3')
    args=parser.parse_args()
    header=(Path(__file__).resolve().parents[1]/'firmware/KirbyPantalla/portrait_assets.h').read_text()
    emotions=int(re.search(r'PORTRAIT_EMOTIONS=(\d+)',header)[1])
    gestures=int(re.search(r'PORTRAIT_GESTURES=(\d+)',header)[1])
    session=DeviceSession()
    def apply(identifier):
        session.apply_action(VoiceAction('ANIMATION',identifier,''))
    try:
        session.connect(args.port)
        session.apply_action(VoiceAction('MODE','auto',''))
        cases=[('angry',emotions+112),('suspicious',emotions+40),('confused',emotions+88),
               ('sad',emotions+160),('scared',emotions+192),('shy',emotions+222),
               ('bored',gestures+44),('surprised',gestures+88),('proud',gestures+120),
               ('laughing',gestures+150),('happy',gestures+204),('playful',gestures+220)]
        for identifier,face in cases:
            apply(identifier)
            assert session.set_speaking(True)
            time.sleep(.4)
            before=diagnostics(session)
            assert before['face']==face,(identifier,before)
            assert session.set_speaking(True)
            time.sleep(.7)
            after=diagnostics(session)
            assert after['face']==face and 486<=after['frame']<666,(identifier,after)
            assert after['drawn']-before['drawn']>=10,(identifier,before,after)
            print(identifier,'face',face,'mouth',before['frame'],'->',after['frame'],flush=True)
        apply('thinking')
        assert session.set_speaking(True)
        time.sleep(.7)
        pose=diagnostics(session)
        assert pose['face']==482 and pose['frame']==482,pose
        assert session.set_speaking(False)
        session.apply_action(VoiceAction('MODE','auto',''))
        session.apply_action(VoiceAction('EXPRESSION','neutral',''))
        assert session.set_speaking(True)
        time.sleep(.5)
        neutral=diagnostics(session)
        assert neutral['face']==65535 and 486<=neutral['frame']<666,neutral
        assert session.set_speaking(False)
        time.sleep(.4)
        assert diagnostics(session)['frame']==480
        print('Expressive USB PASS: contextual faces, moving mouth, retained nonfrontal pose, neutral speech and stop.',flush=True)
    finally:
        try:
            if session.connected:
                session.set_speaking(False)
                session.apply_action(VoiceAction('MODE','auto',''))
        finally:
            session.close()


if __name__=='__main__':
    main()
