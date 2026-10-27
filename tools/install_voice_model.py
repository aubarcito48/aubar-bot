"""Download the Spanish offline model from the official Vosk distribution."""
import hashlib
from pathlib import Path
import stat
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parents[1] / 'models'
MODEL = 'vosk-model-small-es-0.42'
URL = f'https://alphacephei.com/vosk/models/{MODEL}.zip'
SHA256 = '09b239888f633ef2f0b4e09736e3d9936acfd810bc65d53fad45261762c6511f'
REQUIRED = ('am/final.mdl', 'conf/model.conf', 'conf/mfcc.conf',
            'graph/HCLr.fst', 'graph/Gr.fst', 'ivector/final.ie')


def install():
    target = ROOT / MODEL
    if all((target / name).is_file() for name in REQUIRED):
        print(f'Modelo de espanol disponible: {target}')
        return
    ROOT.mkdir(exist_ok=True)
    archive = ROOT / f'{MODEL}.zip'
    print(f'Descargando modelo de espanol desde {URL}', flush=True)
    digest = hashlib.sha256()
    size = 0
    with urllib.request.urlopen(URL, timeout=30) as response, archive.open('wb') as output:
        while chunk := response.read(1024*1024):
            size += len(chunk)
            if size > 100*1024*1024:
                raise RuntimeError('El archivo excede el tamano esperado.')
            digest.update(chunk)
            output.write(chunk)
    print(f'SHA256: {digest.hexdigest()}', flush=True)
    if digest.hexdigest() != SHA256:
        raise RuntimeError('La descarga no coincide con el modelo verificado.')
    with zipfile.ZipFile(archive) as package:
        if sum(item.file_size for item in package.infolist()) > 300*1024*1024:
            raise RuntimeError('El modelo descomprimido excede el tamano esperado.')
        for item in package.infolist():
            destination = (ROOT / item.filename).resolve()
            if not destination.is_relative_to(target.resolve()) or stat.S_ISLNK(item.external_attr >> 16):
                raise RuntimeError('El archivo contiene una ruta inesperada.')
        package.extractall(ROOT)
    if not all((target / name).is_file() for name in REQUIRED):
        raise RuntimeError('El modelo descargado esta incompleto.')
    print(f'Modelo listo: {target}')


if __name__ == '__main__':
    install()
