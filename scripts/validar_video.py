"""Valida a mídia final, a sincronização das legendas e a integridade do áudio."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import wave

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser()
parser.add_argument('--version', choices=['v1', 'v2'], default='v1')
args = parser.parse_args()
OUT = ROOT / ('release/video/final-v2' if args.version == 'v2' else 'release/video/previa-v1')
WORK = ROOT / f'.local/video-apresentacao-{args.version}'
FFMPEG = shutil.which('ffmpeg') or r'C:\ffmpeg\bin\ffmpeg.exe'
FFPROBE = shutil.which('ffprobe') or r'C:\ffmpeg\bin\ffprobe.exe'

def main():
    target = OUT / 'atelie-verde-apresentacao.mp4'
    timeline = json.loads((WORK / 'timeline.json').read_text(encoding='utf-8'))
    result = subprocess.run([FFPROBE, '-v', 'error', '-show_streams', '-show_format', '-show_chapters', '-of', 'json', str(target)], capture_output=True, text=True, encoding='utf-8', check=True)
    info = json.loads(result.stdout)
    video = next(s for s in info['streams'] if s['codec_type'] == 'video')
    sound = next(s for s in info['streams'] if s['codec_type'] == 'audio')
    subtitles = [s for s in info['streams'] if s['codec_type'] == 'subtitle']
    assert (video['width'], video['height']) == (1920, 1080)
    assert video['codec_name'] == 'h264' and video['pix_fmt'] == 'yuv420p'
    assert video['sample_aspect_ratio'] == '1:1' and video['r_frame_rate'] == '24/1'
    assert sound['codec_name'] == 'aac' and sound['sample_rate'] == '48000'
    assert [s['tags']['language'] for s in subtitles] == ['por', 'eng']
    assert len(info['chapters']) == 10
    assert abs(float(info['format']['duration']) - timeline[-1]['end']) < .15
    checks = ['Full HD H.264, pixels quadrados, 24 fps', 'AAC 48 kHz', 'Duas faixas de legenda e dez capítulos', 'Duração coerente com a narração']
    for c in timeline:
        if c.get('continuous_speech'):
            metadata = json.loads((WORK / f'audio/chapter-{c["index"]:02}.phonemes.json').read_text(encoding='utf-8'))
            assert len(metadata) == c['phonemes'] and metadata
            with wave.open(str(WORK / f'audio/chapter-{c["index"]:02}.speech.wav'), 'rb') as source:
                assert source.getnframes() / source.getframerate() >= sum(len(cue['pt'].split()) for cue in c['cues']) / 5
        else:
            for i, cue in enumerate(c['cues']):
                with wave.open(str(WORK / f'audio/{c["index"]:02}-{i:02}.wav'), 'rb') as source:
                    assert source.getnframes() / source.getframerate() >= len(cue['pt'].split()) / 5
        assert all(cue['start'] < cue['end'] < c['duration'] for cue in c['cues'])
    checks.append('Vinte trechos de voz com duração válida')
    for language in ('pt', 'en'):
        text = (OUT / f'atelie-verde-{language}.vtt').read_text(encoding='utf-8')
        assert text.startswith('WEBVTT\n') and text.count(' --> ') == 20
        for c in timeline:
            for cue in c['cues']:
                assert ' '.join(cue[language].split()) in ' '.join(text.split())
    checks.append('Vinte legendas completas em cada idioma')
    decoded = subprocess.run([FFMPEG, '-hide_banner', '-v', 'error', '-i', str(target), '-map', '0:v:0', '-map', '0:a:0', '-f', 'null', '-'], capture_output=True, text=True)
    assert decoded.returncode == 0 and not decoded.stderr.strip(), decoded.stderr
    checks.append('Vídeo e áudio decodificados integralmente sem erros')
    loudness = subprocess.run([FFMPEG, '-hide_banner', '-i', str(target), '-map', '0:a:0', '-vn', '-af', 'ebur128=peak=true', '-f', 'null', '-'], capture_output=True, text=True, check=True)
    summary = loudness.stderr.rsplit('Summary:', 1)[-1]
    integrated = float(re.search(r'I:\s+(-?[\d.]+) LUFS', summary).group(1))
    peak = float(re.search(r'Peak:\s+(-?[\d.]+) dBFS', summary).group(1))
    assert -22 <= integrated <= -14 and peak <= -.5
    checks.append('Volume consistente e áudio sem clipping')
    report = {'ok': True, 'duration': float(info['format']['duration']), 'resolution': '1920x1080', 'fps': 24, 'chapters': 10, 'captions_per_language': 20, 'integrated_lufs': integrated, 'true_peak_dbfs': peak, 'bytes': target.stat().st_size, 'sha256': hashlib.file_digest(target.open('rb'), 'sha256').hexdigest(), 'checks': checks}
    (OUT / 'validacao.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(report, ensure_ascii=True), flush=True)

if __name__ == '__main__':
    main()
