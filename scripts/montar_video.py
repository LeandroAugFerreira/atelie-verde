"""Monta a prévia Full HD, com capítulos e duas faixas de legendas."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import textwrap

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser()
parser.add_argument('--version', choices=['v1', 'v2'], default='v1')
args = parser.parse_args()
WORK = ROOT / f'.local/video-apresentacao-{args.version}'
OUT = ROOT / ('release/video/final-v2' if args.version == 'v2' else 'release/video/previa-v1')
FFMPEG = shutil.which('ffmpeg') or r'C:\ffmpeg\bin\ffmpeg.exe'
FPS = 24

def run(args):
    subprocess.run([FFMPEG, '-hide_banner', '-loglevel', 'error', '-y', *args], cwd=WORK, check=True)

def stamp(seconds, sep='.'):
    milliseconds = round(seconds * 1000)
    h, milliseconds = divmod(milliseconds, 3600000)
    m, milliseconds = divmod(milliseconds, 60000)
    s, ms = divmod(milliseconds, 1000)
    return f'{h:02}:{m:02}:{s:02}{sep}{ms:03}'

def main():
    OUT.mkdir(parents=True, exist_ok=True)
    media = WORK / 'media'
    media.mkdir(exist_ok=True)
    chapters = json.loads((WORK / 'timeline.json').read_text(encoding='utf-8'))
    cues = []
    metadata = [';FFMETADATA1', 'title=Ateliê Verde — Jardinagem e paisagismo', 'artist=Leandro Augusto Ferreira', 'comment=Demonstração com dados fictícios.']
    for c in chapters:
        index = c['index']
        recording = json.loads((WORK / f'recordings/{index:02}.json').read_text(encoding='utf-8'))
        assert abs(recording['duration'] - c['duration']) < .04
        (media / f'title-{index:02}.txt').write_text(c['title'], encoding='utf-8')
        filters = (
            'fps=24,scale=1824:1026:flags=lanczos,setsar=1,'
            'pad=1920:1080:48:48:color=0x052017,'
            f"drawtext=fontfile='C\\:/Windows/Fonts/segoeuib.ttf':textfile='media/title-{index:02}.txt':fontcolor=white:fontsize=28:x=48:y=7,"
            'drawbox=x=48:y=40:w=1824:h=2:color=0x88e7b3:t=fill,'
            f'fade=t=in:d=0.3,fade=t=out:st={c["duration"] - .35:.3f}:d=0.35'
        )
        output = media / f'chapter-{index:02}.mp4'
        if not output.is_file() or output.stat().st_size < 10000 or output.stat().st_mtime < max((WORK / f'recordings/{index:02}.json').stat().st_mtime, (WORK / f'audio/chapter-{index:02}.wav').stat().st_mtime):
            run(['-ss', str(recording['trim']), '-i', str(WORK / 'recordings' / recording['file']), '-i', str(WORK / f'audio/chapter-{index:02}.wav'), '-t', str(c['duration']),
                 '-vf', filters, '-af', ('highpass=f=65,loudnorm=I=-19:TP=-2:LRA=8,aresample=48000' if args.version == 'v2' else 'loudnorm=I=-18:TP=-2:LRA=7,aresample=48000'), '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '18', '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a', '128k', '-threads', '4', str(output)])
        cues.extend({'start': c['start'] + cue['start'], 'end': c['start'] + cue['end'], 'pt': cue['pt'], 'en': cue['en']} for cue in c['cues'])
        metadata.extend(['[CHAPTER]', 'TIMEBASE=1/1000', f'START={round(c["start"] * 1000)}', f'END={round(c["end"] * 1000)}', f'title={c["title"]}'])
        print(f'Montagem {index + 1}/{len(chapters)}: {c["id"]}', flush=True)
    for language in ('pt', 'en'):
        vtt = ['WEBVTT', '']
        srt = []
        for index, cue in enumerate(cues, 1):
            wrapped = '\n'.join(textwrap.wrap(cue[language], width=56, break_long_words=False, break_on_hyphens=False))
            vtt.extend([str(index), f'{stamp(cue["start"])} --> {stamp(cue["end"])}', wrapped, ''])
            srt.extend([str(index), f'{stamp(cue["start"], ",")} --> {stamp(cue["end"], ",")}', wrapped, ''])
        (OUT / f'atelie-verde-{language}.vtt').write_text('\n'.join(vtt), encoding='utf-8')
        (OUT / f'atelie-verde-{language}.srt').write_text('\n'.join(srt), encoding='utf-8')
    (media / 'concat.txt').write_text('\n'.join(f"file 'chapter-{c["index"]:02}.mp4'" for c in chapters), encoding='utf-8')
    (media / 'chapters.txt').write_text('\n'.join(metadata), encoding='utf-8')
    run(['-f', 'concat', '-safe', '0', '-i', str(media / 'concat.txt'), '-i', str(OUT / 'atelie-verde-pt.srt'), '-i', str(OUT / 'atelie-verde-en.srt'), '-i', str(media / 'chapters.txt'),
         '-map', '0:v:0', '-map', '0:a:0', '-map', '1:0', '-map', '2:0', '-map_metadata', '3', '-map_chapters', '3', '-c:v', 'copy', '-c:a', 'copy', '-c:s', 'mov_text',
         '-metadata:s:a:0', 'language=por', '-metadata:s:s:0', 'language=por', '-metadata:s:s:0', 'title=Português BR', '-metadata:s:s:1', 'language=eng', '-metadata:s:s:1', 'title=English', '-movflags', '+faststart', str(OUT / 'atelie-verde-apresentacao.mp4')])
    (OUT / 'capitulos.json').write_text(json.dumps([{key: c[key] for key in ('id', 'title', 'start', 'end')} for c in chapters], ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'Prévia pronta: {chapters[-1]["end"]:.2f}s.', flush=True)

if __name__ == '__main__':
    main()
