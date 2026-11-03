"""Gera narração e tempos da prévia, sem tocar nas dependências da aplicação."""
import asyncio
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import wave

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.local/video-tools'))
import edge_tts

WORK = ROOT / '.local/video-apresentacao-v1'
VOICE = 'pt-BR-FranciscaNeural'
FFMPEG = shutil.which('ffmpeg') or r'C:\ffmpeg\bin\ffmpeg.exe'
FPS = 24

async def main():
    script = json.loads((ROOT / 'docs/roteiro-video.json').read_text(encoding='utf-8'))
    audio_dir = WORK / 'audio'
    audio_dir.mkdir(parents=True, exist_ok=True)
    timeline = []
    elapsed = 0.0
    for index, chapter in enumerate(script):
        chapter_pcm = bytearray(bytes(round(24000 * .4) * 2))
        at = .4
        cues = []
        for cue_index, cue in enumerate(chapter['cues']):
            name = f'{index:02}-{cue_index:02}'
            wav = audio_dir / f'{name}.wav'
            spoken = cue['pt'].replace('ChatGPT', 'Chat G P T')
            digest = hashlib.sha256((spoken + VOICE + '-3%').encode()).hexdigest()
            marker = audio_dir / f'{name}.sha256'
            minimum_seconds = max(1.0, len(spoken.split()) / 5)
            cached_valid = False
            if wav.is_file() and marker.is_file() and marker.read_text() == digest:
                with wave.open(str(wav), 'rb') as cached:
                    cached_valid = cached.getnframes() / cached.getframerate() >= minimum_seconds
            if not cached_valid:
                mp3 = audio_dir / f'{name}.mp3'
                metadata = audio_dir / f'{name}.speech.jsonl'
                for attempt in range(3):
                    try:
                        await edge_tts.Communicate(spoken, VOICE, rate='-3%', pitch='+0Hz', volume='+0%', boundary='WordBoundary').save(str(mp3), str(metadata))
                        subprocess.run([FFMPEG, '-hide_banner', '-loglevel', 'error', '-y', '-i', str(mp3), '-ar', '24000', '-ac', '1', '-c:a', 'pcm_s16le', str(wav)], check=True)
                        with wave.open(str(wav), 'rb') as generated:
                            assert generated.getnframes() / generated.getframerate() >= minimum_seconds, 'Narração incompleta recebida.'
                        events = [json.loads(line) for line in metadata.read_text(encoding='utf-8').splitlines() if line.strip()]
                        assert len(events) >= len(spoken.split()) * .65, 'Palavras insuficientes na narração.'
                        break
                    except Exception:
                        if attempt == 2:
                            raise
                        await asyncio.sleep(2)
                marker.write_text(digest)
            with wave.open(str(wav), 'rb') as source:
                assert source.getframerate() == 24000 and source.getnchannels() == 1 and source.getsampwidth() == 2
                seconds = source.getnframes() / 24000
                chapter_pcm.extend(source.readframes(source.getnframes()))
            cues.append({'start': at, 'end': at + seconds, **cue})
            at += seconds + .4
            chapter_pcm.extend(bytes(round(24000 * .4) * 2))
        duration = round((at + .7) * FPS) / FPS
        samples = round(duration * 24000)
        chapter_pcm.extend(bytes(max(0, samples * 2 - len(chapter_pcm))))
        with wave.open(str(audio_dir / f'chapter-{index:02}.wav'), 'wb') as output:
            output.setparams((1, 2, 24000, 0, 'NONE', 'not compressed'))
            output.writeframes(chapter_pcm[:samples * 2])
        timeline.append({'index': index, 'id': chapter['id'], 'title': chapter['title'], 'duration': duration, 'start': elapsed, 'end': elapsed + duration, 'cues': cues})
        elapsed += duration
        (WORK / 'timeline.json').write_text(json.dumps(timeline, ensure_ascii=False, indent=2), encoding='utf-8')
        print(f'Narração {index + 1}/{len(script)}: {chapter["id"]} · {duration:.2f}s', flush=True)
    (WORK / 'narracao.json').write_text(json.dumps({'voice': VOICE, 'rate': '-3%', 'language': 'pt-BR', 'duration': elapsed}, indent=2), encoding='utf-8')
    print(f'Duração total: {elapsed:.2f}s', flush=True)

if __name__ == '__main__':
    asyncio.run(main())
