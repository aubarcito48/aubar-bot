"""Explicit, checksum-pinned preparation of local Aubar Director semantic assets."""
import hashlib
from pathlib import Path
import sys
import urllib.request

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from pc.aubar_control.services.assistant.director.director_encoder import FOLDER, ASSETS, REPOSITORY, REVISION


def main():
    FOLDER.mkdir(parents=True, exist_ok=True)
    for remote, name, size, checksum in ASSETS:
        destination = FOLDER/name
        if destination.is_file() and destination.stat().st_size == size:
            if hashlib.sha256(destination.read_bytes()).hexdigest() == checksum:
                print(f'{name}: already verified', flush=True)
                continue
        url = f'https://huggingface.co/{REPOSITORY}/resolve/{REVISION}/{remote}'
        request = urllib.request.Request(url, headers={'User-Agent': 'AubarDirector/0.1'})
        temporary = destination.with_suffix(destination.suffix+'.partial')
        digest, total = hashlib.sha256(), 0
        with urllib.request.urlopen(request, timeout=30) as response, temporary.open('wb') as output:
            while chunk := response.read(1024*1024):
                total += len(chunk)
                if total > size:
                    raise ValueError('Unexpected Aubar encoder download size')
                digest.update(chunk)
                output.write(chunk)
        if total != size or digest.hexdigest() != checksum:
            raise ValueError('Aubar encoder download verification failed')
        temporary.replace(destination)
        print(f'{name}: verified {total} bytes', flush=True)
    (FOLDER/'NOTICE.txt').write_text(
        'Sentence Transformers paraphrase-multilingual-MiniLM-L12-v2\n'
        'License: Apache-2.0, https://www.apache.org/licenses/LICENSE-2.0\n'
        f'Source: https://huggingface.co/{REPOSITORY}/tree/{REVISION}\n'
        'This is the feature extractor, not Aubar\'s trained performance classifier.\n', encoding='utf-8')


if __name__ == '__main__':
    main()
