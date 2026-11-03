import html
import json
import re
import sys
import urllib.request
from pathlib import Path
from urllib.parse import quote

sys.stdout.reconfigure(encoding='utf-8')
ROOT = Path(__file__).resolve().parents[1]

def read(url):
    request = urllib.request.Request(url, headers={'User-Agent':'AtelieVerde/1.0 (educational botanical catalog, attribution retained)'})
    return urllib.request.urlopen(request, timeout=40).read()

def plain(value):
    return html.unescape(re.sub('<[^>]+>','',value))

def commons(slug):
    scientific = {'plinia-cauliflora':'Myrciaria cauliflora'}.get(slug,slug.replace('-', ' '))
    url = 'https://commons.wikimedia.org/w/api.php?action=query&generator=search&gsrsearch='+quote(scientific)+'&gsrnamespace=6&gsrlimit=12&prop=imageinfo&iiprop=url%7Cextmetadata&iiurlwidth=1200&format=json'
    data = json.loads(read(url))
    result = []
    pages = sorted(data.get('query',{}).get('pages',{}).values(), key=lambda p:p.get('index',99))
    for page in pages:
        info = page.get('imageinfo',[{}])[0]
        meta = info.get('extmetadata',{})
        license_label = meta.get('LicenseShortName',{}).get('value','')
        if not license_label.startswith(('CC BY','CC0','Public domain')) or 'NC' in license_label or 'ND' in license_label:
            continue
        if not all(word in page['title'].lower() for word in scientific.lower().split()):
            continue
        # Download a repository-provided thumbnail; no local photo modification.
        remote = info.get('thumburl') or info.get('url')
        try:
            content = read(remote)
            if len(content) > 10*1024*1024:
                continue
            filename = f'{slug}-{len(result)+1}.jpg'
            (ROOT/'frontend/public/plants'/filename).write_bytes(content)
            result.append({'url':'/plants/'+filename, 'author':plain(meta.get('Artist',{}).get('value','Autor indicado na fonte')),
                'license':license_label,'license_url':meta.get('LicenseUrl',{}).get('value',''),
                'caption':plain(meta.get('ImageDescription',{}).get('value',scientific)),
                'source_url':info['descriptionurl'], 'original_url':info['url'].split('?')[0],
                'changes':'Miniatura disponibilizada pelo Wikimedia Commons; enquadramento responsivo na interface.'})
        except Exception as exc:
            print(slug, type(exc).__name__, flush=True)
        if len(result) == 2:
            break
    return result

if __name__ == '__main__':
    manifest = json.loads((ROOT/'backend/app/photo_manifest.json').read_text(encoding='utf-8'))
    for item in manifest:
        if not item['photos'] or len(item['photos']) == 1:
            photos = commons(item['slug'])
            if photos:
                item['photos'] = photos
            print(item['slug'], len(item['photos']), flush=True)
    (ROOT/'backend/app/photo_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
