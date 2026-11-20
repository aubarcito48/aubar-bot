"""Pair private local .env files without displaying or changing API/session keys."""
from pathlib import Path
import re
import secrets
import sys
from dotenv import dotenv_values

ROOT=Path(__file__).resolve().parents[2]


def update(path,settings):
    content=path.read_text(encoding='utf-8-sig') if path.exists() else ''
    for key,value in settings.items():
        pattern=r'(?m)^\s*(?:export\s+)?'+re.escape(key)+r'=[^\r\n]*'
        line=key+'='+value
        if re.search(pattern,content):
            content=re.sub(pattern,lambda _:line,content)
        else:
            content=content.rstrip()+'\n'+line+'\n'
    path.write_text(content,encoding='utf-8')


def main():
    node_path=ROOT/'integrations'/'whatsapp-bot'/'.env'
    legacy=ROOT.parent/'portfolio'/'whatsapp-bot'/'.env'
    if not node_path.is_file() and legacy.is_file():
        node_path=legacy
    desktop_path=ROOT/'.env'
    if not node_path.is_file() or not desktop_path.is_file():
        raise ValueError('Prepará los archivos .env de ambos proyectos antes de vincularlos.')
    node=dotenv_values(node_path,interpolate=False)
    desktop=dotenv_values(desktop_path,interpolate=False)
    tokens=[value for value in (node.get('AUBAR_CONTROL_TOKEN'),desktop.get('AUBAR_CONTROL_TOKEN')) if value]
    if any(not re.fullmatch(r'[a-f0-9]{64}',token) for token in tokens) or len(set(tokens))>1:
        raise ValueError('Los tokens existentes no coinciden o son inválidos. No se modificó la configuración.')
    token=tokens[0] if tokens else secrets.token_hex(32)
    port=int(node.get('PORT') or '3000')
    if not 1<=port<=65535: raise ValueError('El puerto del bot no es válido.')
    update(node_path,{'AUBAR_CONTROL_TOKEN':token})
    update(desktop_path,{'AUBAR_CONTROL_TOKEN':token,
        'AUBAR_WHATSAPP_CONTROL_URL':f'http://127.0.0.1:{port}/control/',
        'AUBAR_WHATSAPP_HEALTH_URL':f'http://127.0.0.1:{port}/health'})
    print('Puente local configurado en ambos proyectos. Token privado no mostrado. Reiniciá ambos procesos.')


if __name__=='__main__':
    try: main()
    except Exception:
        print('No se pudo vincular la configuración local. Revisá los archivos y el puerto; no compartas las claves.',file=sys.stderr)
        raise SystemExit(1)
