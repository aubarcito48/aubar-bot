"""Check actual LCD decode, pose routing and live motion over USB (panel closed)."""
import argparse
from pathlib import Path
import re
import sys
import time
import zlib

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from pc.aubar_control.session import DeviceSession
from pc.aubar_control.voice_commands import VoiceAction

ROOT=Path(__file__).resolve().parents[1]


def diagnostics(session):
    session._serial.write(b'PORTRAIT\n')
    response=session._readline(time.monotonic()+3)
    assert response.startswith('OK PORTRAIT '),response
    data={k:int(v) for k,v in (part.split('=') for part in response.split()[2:])}
    assert data['ready']==1 and data['errors']==0,data
    assert data['psram']>=8*1024*1024,data
    return data


def hashes():
    header=(ROOT/'firmware/KirbyPantalla/portrait_assets.h').read_text()
    def array(name):
        return list(map(int,re.search(name+r'\[\] = \{([^}]+)',header)[1].split(',')))
    offsets,lengths=array('PORTRAIT_OFFSETS'),array('PORTRAIT_LENGTHS')
    blob=(ROOT/'firmware/KirbyPantalla/portrait_assets.dat').read_bytes()
    result=[]
    for offset,length in zip(offsets,lengths):
        raw=zlib.decompress(blob[offset:offset+length])
        assert len(raw)==172*320
        value=2166136261
        for pixel in raw: value=((value^pixel)*16777619)&0xffffffff
        result.append(value)
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port',default='COM3')
    args=parser.parse_args()
    expected=hashes()
    session=DeviceSession()
    try:
        session.connect(args.port)
        def apply(command,argument,look=None):
            return session.apply_action(VoiceAction(command,argument,'',look))
        apply('MODE','auto')
        cases=[('EXPRESSION','neutral',480),('EXPRESSION','gentle-downward-gaze',481),
               ('ANIMATION','thinking',482),('EXPRESSION','dormido',483),
               ('ANIMATION','laughing',484),('EXPRESSION','sorprendido',485)]
        for command,identifier,frame in cases:
            apply(command,identifier)
            time.sleep(.5)
            data=diagnostics(session)
            assert data['frame']==frame,(identifier,data)
            assert data['checksum']==expected[frame],(identifier,data)
            print(identifier,data,flush=True)
        for direction,frame in [('izquierda',72),('derecha',42),('centro',480)]:
            apply('EXPRESSION','neutral',direction)
            time.sleep(1.1)
            data=diagnostics(session)
            assert data['frame']==frame and data['checksum']==expected[frame],(direction,data)
        apply('MODE','auto')
        apply('ANIMATION','idle')
        before=diagnostics(session)
        time.sleep(2)
        after=diagnostics(session)
        assert after['frame']!=before['frame'],(before,after)
        assert after['drawn']-before['drawn']>=35,(before,after)
        assert after['checksum']==expected[after['frame']],after
        print('idle live motion',before,after,flush=True)
        apply('ANIMATION','searching')
        time.sleep(.7)
        data=diagnostics(session)
        assert 240<=data['frame']<480 and data['checksum']==expected[data['frame']],data
        print('horizontal live motion',data,flush=True)
        apply('EXPRESSION','neutral')
        assert session.set_speaking(True)
        time.sleep(.5)
        before=diagnostics(session)
        assert 486<=before['frame']<666,before
        # Renewing playback must not reset the clip or logical pose.
        assert session.set_speaking(True)
        time.sleep(.5)
        after=diagnostics(session)
        assert after['frame']>before['frame'],(before,after)
        assert after['checksum']==expected[after['frame']],after
        assert session.status().expression=='neutral'
        assert session.set_speaking(False)
        time.sleep(.4)
        assert diagnostics(session)['frame']==480
        assert session.set_speaking(True)
        # Simulate a crashed/unplugged desktop: speech expires by itself.
        time.sleep(4.3)
        assert diagnostics(session)['frame']==480
        print('Speech playback, heartbeat, stop, preserved pose and lease expiry PASS.',flush=True)
        apply('MODE','auto')
        print(f'Portrait USB PASS: {len(expected)} desktop decodes, stills, gazes, videos, speech, checksums, PSRAM, live frame rate. Auto restored.')
    finally:
        session.close()


if __name__=='__main__': main()
