"""Fetch primary botanical sources and reusable photographs, keeping attribution."""
import concurrent.futures
import html
import json
import re
import urllib.request
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
SLUGS = [
    'hibiscus-rosa-sinensis', 'lavandula-dentata', 'zamioculcas-zamiifolia',
    'dracaena-trifasciata', 'monstera-deliciosa', 'ixora-coccinea',
    'echeveria-elegans', 'spathiphyllum-wallisii', 'salvia-rosmarinus',
    'agapanthus-africanus', 'plumeria-rubra', 'rhapis-excelsa',
    'buxus-sempervirens', 'adenium-obesum', 'lantana-camara',
    'epipremnum-aureum', 'chlorophytum-comosum', 'anthurium-andraeanum',
    'crassula-ovata', 'peperomia-obtusifolia', 'coleus-scutellarioides',
    'chrysalidocarpus-lutescens', 'nephrolepis-exaltata', 'strelitzia-reginae',
    'bougainvillea-glabra', 'ocimum-basilicum', 'mentha-spicata',
    'maranta-leuconeura', 'fittonia-albivenis', 'tradescantia-zebrina',
]

class Parser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.photos = []
    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == 'img' and a.get('data-attrib') and a.get('data-license'):
            license_html = a['data-license']
            license_label = re.sub('<[^>]+>', '', license_html).strip()
            match = re.search(r"href=['\"]([^'\"]+)", license_html)
            if any(x in license_label.upper() for x in ('NC', 'ND')):
                return
            if not any(x in license_label.upper() for x in ('CC BY', 'CC-BY', 'CC0', 'PUBLIC DOMAIN')):
                return
            self.photos.append({
                'remote_url': a['src'], 'author': a['data-attrib'],
                'license': license_label, 'license_url': match[1] if match else '',
                'caption': a.get('data-caption', a.get('alt', '')),
            })

def fetch(slug):
    url = f'https://plants.ces.ncsu.edu/plants/{slug}/'
    try:
        response = urllib.request.urlopen(url, timeout=35)
        source = response.geturl()
        raw = response.read().decode()
        parser = Parser()
        parser.feed(raw)
        # Prefer views of the plant or flower over microscopic or pest images.
        photos = sorted(parser.photos, key=lambda p: (
            any(w in p['caption'].lower() for w in ('insect', 'fruit', 'seed', 'stem', 'root')),
            not any(w in p['caption'].lower() for w in ('form', 'habit', 'potted', 'plant', 'flower')),
        ))
        acquired = []
        folder = ROOT / 'frontend/public/plants'
        folder.mkdir(parents=True, exist_ok=True)
        for photo in photos:
            if len(acquired) == 2:
                break
            try:
                res = urllib.request.urlopen(photo['remote_url'], timeout=40)
                content = res.read(10 * 1024 * 1024 + 1)
                if len(content) > 10 * 1024 * 1024:
                    continue
                extension = Path(urlparse(photo['remote_url']).path).suffix.lower()
                if extension not in ('.jpg', '.jpeg', '.jpe', '.png', '.webp'):
                    continue
                if extension == '.jpe':
                    extension = '.jpg'
                filename = f'{slug}-{len(acquired)+1}{extension}'
                (folder / filename).write_bytes(content)
                photo['url'] = f'/plants/{filename}'
                photo['source_url'] = source
                photo['original_url'] = photo.pop('remote_url').split('?')[0]
                photo['changes'] = 'Original intacto; enquadramento responsivo na interface.'
                acquired.append(photo)
            except Exception as exc:
                print(f'Photo retry {slug}: {type(exc).__name__}', flush=True)
        plain = html.unescape(re.sub('<[^>]+>', ' ', raw))
        plain = re.sub(r'\s+', ' ', plain)
        pos = plain.find('Description')
        result = {'slug':slug, 'source_url':source, 'photos':acquired,
                  'research_excerpt':plain[pos:pos+6000]}
        print(f'{slug}: {len(acquired)} photos', flush=True)
        return result
    except Exception as exc:
        print(f'ERROR {slug}: {exc}', flush=True)
        return {'slug':slug, 'source_url':url, 'photos':[], 'error':str(exc)}

if __name__ == '__main__':
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        research = list(pool.map(fetch, SLUGS))
    (ROOT/'.local/botany-research.json').write_text(json.dumps(research, ensure_ascii=False, indent=2), encoding='utf-8')
    manifest = [{k:v for k,v in r.items() if k not in ('research_excerpt','error')} for r in research]
    (ROOT/'backend/app/photo_manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
