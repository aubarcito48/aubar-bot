"""Check the full catalog against the actual production firmware (panel closed)."""
import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pc.aubar_control.catalog import EXPRESSIONS, ANIMATIONS
from pc.aubar_control.session import DeviceSession
from pc.aubar_control.voice_commands import VoiceAction, match_command


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--port', default='COM3')
    args=parser.parse_args()
    session=DeviceSession()
    checks=0
    try:
        session.connect(args.port)
        for identifier in EXPRESSIONS:
            status=session.apply_action(VoiceAction('EXPRESSION', identifier, ''))
            assert status.mode=='manual' and status.expression==identifier and status.animation=='none',status
            checks+=1
        for identifier,label in ANIMATIONS.items():
            action=match_command(label)
            status=session.apply_action(action)
            assert status.mode=='manual' and status.animation==identifier,status
            checks+=1
        status=session.apply_action(VoiceAction('EXPRESSION','contento',''))
        assert status.animation=='none' and status.expression=='contento',status
        session.apply_action(VoiceAction('MODE','auto',''))
        print(f'USB catalog PASS: {checks} options confirmed; manual interruption PASS; automatic mode restored.')
    finally:
        session.close()


if __name__=='__main__':
    main()
