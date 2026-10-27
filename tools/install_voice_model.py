"""Download the Spanish offline model from the official Vosk distribution."""
import hashlib
from pathlib import Path
import stat
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parents[1] / 'models'
MODEL = 'vosk-model-es-0.42'
URL = f'https://alphacephei.com/vosk/models/{MODEL}.zip'
SHA256 = 'bbbfaf9239bed5dcb0d140886b5834fcc13c13c7fb2f2799ae790f03ff20bfce'
REQUIRED = ('am/final.mdl', 'conf/model.conf', 'conf/mfcc.conf',
            'graph/HCLG.fst', 'graph/words.txt', 'ivector/final.ie',
            'ivector/online_cmvn.conf', 'rescore/G.fst', 'rescore/G.carpa',
            'rnnlm/final.raw', 'rnnlm/feat_embedding.final.mat')


def install():
    target = ROOT / MODEL
    if not target.resolve().is_relative_to(ROOT.resolve()):
        raise RuntimeError('La carpeta del modelo debe permanecer dentro de models.')
    if all((target / name).is_file() for name in REQUIRED):
        print(f'Modelo de espanol disponible: {target}')
        return
    ROOT.mkdir(exist_ok=True)
    archive = ROOT / f'{MODEL}.zip'
    cached = False
    if archive.is_file():
        with archive.open('rb') as source:
            cached = hashlib.file_digest(source,'sha256').hexdigest() == SHA256
    if not cached:
        print(f'Descargando modelo completo de espanol (1,4 GB) desde {URL}', flush=True)
        digest = hashlib.sha256()
        size = progress = 0
        partial = archive.with_suffix('.zip.partial')
        with urllib.request.urlopen(URL, timeout=30) as response, partial.open('wb') as output:
            while chunk := response.read(1024*1024):
                size += len(chunk)
                if size > 1600*1024*1024:
                    raise RuntimeError('El archivo excede el tamano esperado.')
                digest.update(chunk)
                output.write(chunk)
                if size-progress>=128*1024*1024:
                    print(f'Descargados {size//1024**2} MiB de aproximadamente 1415 MiB.',flush=True)
                    progress=size
        if digest.hexdigest() != SHA256:
            raise RuntimeError('La descarga no coincide con el modelo verificado.')
        partial.replace(archive)
    with zipfile.ZipFile(archive) as package:
        if sum(item.file_size for item in package.infolist()) > 3*1024*1024*1024:
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
