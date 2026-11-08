"""Dependency-free local preview: python3 -m app.preview [--port 8082]."""
from argparse import ArgumentParser
from pathlib import Path
from secrets import token_hex
from wsgiref.simple_server import make_server
from .config import Config
from .portal import create_app


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=8082)
    args = parser.parse_args()
    data = Path(__file__).resolve().parent.parent / 'data/preview'
    data.mkdir(mode=0o700, parents=True, exist_ok=True)
    key = data/'secret'
    if not key.exists():
        # Atomic creation if two previews are launched at the same time.
        try:
            with key.open('x') as stream:
                key.chmod(0o600)
                stream.write(token_hex(32))
        except FileExistsError:
            pass
    config = Config(data/'mia.sqlite3', key.read_text().strip(), origin=f'http://localhost:{args.port}')
    with make_server('127.0.0.1', args.port, create_app(config)) as server:
        print(f'MIA Fraude: http://localhost:{args.port}/fraude', flush=True)
        print(f'Recommander: http://localhost:{args.port}/recommander', flush=True)
        server.serve_forever()


if __name__ == '__main__':
    main()
