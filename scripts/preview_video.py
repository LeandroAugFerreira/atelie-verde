"""Serve somente a prévia local, com suporte a busca por tempo no vídeo."""
import argparse
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import re

parser = argparse.ArgumentParser()
parser.add_argument('--directory', type=Path, default=Path(__file__).resolve().parents[1] / 'release/video/previa-v1')
parser.add_argument('--port', type=int, default=18818)
args = parser.parse_args()
ROOT = args.directory.resolve()

class PreviewHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def send_head(self):
        self.limit = None
        path = Path(self.translate_path(self.path)).resolve()
        try:
            relative = path.relative_to(ROOT.resolve())
            if any(part.startswith('.') for part in relative.parts):
                self.send_error(403)
                return None
        except ValueError:
            self.send_error(403)
            return None
        requested = self.headers.get('Range')
        if not requested or not path.is_file():
            return super().send_head()
        match = re.fullmatch(r'bytes=(\d*)-(\d*)', requested.strip())
        size = path.stat().st_size
        if not match or not (match[1] or match[2]):
            self.send_error(416)
            return None
        if match[1]:
            start = int(match[1])
            end = min(int(match[2]) if match[2] else size - 1, size - 1)
        else:
            start = max(0, size - int(match[2]))
            end = size - 1
        if start >= size or end < start:
            self.send_response(416)
            self.send_header('Content-Range', f'bytes */{size}')
            self.end_headers()
            return None
        source = path.open('rb')
        source.seek(start)
        self.limit = end - start + 1
        self.send_response(206)
        self.send_header('Content-Type', self.guess_type(str(path)))
        self.send_header('Content-Length', str(self.limit))
        self.send_header('Content-Range', f'bytes {start}-{end}/{size}')
        self.end_headers()
        return source

    def end_headers(self):
        self.send_header('Accept-Ranges', 'bytes')
        self.send_header('Cache-Control', 'no-cache')
        super().end_headers()

    def copyfile(self, source, outputfile):
        if self.limit is None:
            return super().copyfile(source, outputfile)
        remaining = self.limit
        while remaining:
            data = source.read(min(1024 * 256, remaining))
            if not data:
                break
            outputfile.write(data)
            remaining -= len(data)

if __name__ == '__main__':
    ThreadingHTTPServer(('127.0.0.1', args.port), PreviewHandler).serve_forever()
