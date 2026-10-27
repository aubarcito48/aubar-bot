"""Download verified Kokoro assets once; synthesis itself remains offline."""
import hashlib
from pathlib import Path
import sys
import urllib.request

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from pc.aubar_control.tts_assets import ASSETS, BASE_URL, MODEL_DIR


def verified(path,size,digest):
    if not path.is_file() or path.stat().st_size!=size:
        return False
    with path.open('rb') as stream:
        return hashlib.file_digest(stream,'sha256').hexdigest()==digest


def install(target=MODEL_DIR,opener=urllib.request.urlopen,assets=ASSETS):
    target.mkdir(parents=True,exist_ok=True)
    for name,size,digest in assets:
        path=target/name
        if verified(path,size,digest):
            continue
        partial=path.with_suffix(path.suffix+'.partial')
        print(f'Descargando voz local: {name} ({size//1_000_000} MB)',flush=True)
        try:
            total=0
            with opener(BASE_URL+name,timeout=30) as response,partial.open('wb') as output:
                while chunk:=response.read(1024*1024):
                    total+=len(chunk)
                    if total>size:
                        raise RuntimeError('El archivo de voz excede el tamano esperado.')
                    output.write(chunk)
            if not verified(partial,size,digest):
                raise RuntimeError('La descarga no coincide con el modelo de voz verificado.')
            partial.replace(path)
        finally:
            partial.unlink(missing_ok=True)
    print(f'Voz Dora disponible: {target}',flush=True)


if __name__=='__main__':
    install()
