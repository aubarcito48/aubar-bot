"""Explicit verified download; recognition itself never downloads assets."""
import hashlib
from pathlib import Path
import sys
import urllib.request

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from pc.aubar_control.whisper_assets import MODEL_DIR,REPOSITORY,REVISION,ASSETS


def main():
    MODEL_DIR.mkdir(parents=True,exist_ok=True)
    for name,size,checksum in ASSETS:
        target=MODEL_DIR/name
        if target.is_file() and target.stat().st_size==size:
            with target.open('rb') as stream:
                if hashlib.file_digest(stream,'sha256').hexdigest()==checksum:
                    print(name+': verificado',flush=True)
                    continue
        temporary=target.with_suffix(target.suffix+'.partial')
        url=f'https://huggingface.co/{REPOSITORY}/resolve/{REVISION}/{name}'
        digest=hashlib.sha256();total=0;progress=0
        print('Descargando '+name,flush=True)
        with urllib.request.urlopen(url,timeout=30) as response,temporary.open('wb') as output:
            while chunk:=response.read(1024*1024):
                total+=len(chunk)
                if total>size: raise ValueError('El modelo excedió el tamaño esperado.')
                digest.update(chunk);output.write(chunk)
                if total-progress>=64*1024*1024:
                    print(f'{total//1024**2}/{size//1024**2} MiB',flush=True);progress=total
        if total!=size or digest.hexdigest()!=checksum:
            raise ValueError('La descarga no coincide con el modelo verificado.')
        temporary.replace(target)
    (MODEL_DIR/'NOTICE.txt').write_text(
        'Whisper small, OpenAI / conversion Systran. MIT license.\n'
        f'https://huggingface.co/{REPOSITORY}/tree/{REVISION}\n',encoding='utf-8')
    print('Whisper small listo para CPU local.',flush=True)


if __name__=='__main__': main()
