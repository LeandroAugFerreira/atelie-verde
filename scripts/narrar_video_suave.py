"""Narração neural local em tomadas contínuas, com alinhamento fonético."""
import hashlib
import json
from pathlib import Path
import sys
import wave

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.local/voice-local'))
import numpy as np
import onnxruntime as rt
from kokoro_onnx import Kokoro

WORK = ROOT / '.local/video-apresentacao-v2'
VOICE = 'pf_dora'
SPEED = .94
FPS = 24

def main():
    script = json.loads((ROOT / 'docs/roteiro-video.json').read_text(encoding='utf-8'))
    audio_dir = WORK / 'audio'
    audio_dir.mkdir(parents=True, exist_ok=True)
    options = rt.SessionOptions()
    options.intra_op_num_threads = 4
    options.inter_op_num_threads = 1
    session = rt.InferenceSession(str(ROOT / '.local/voice-models/kokoro-v1.0.onnx'), sess_options=options, providers=['CPUExecutionProvider'])
    model = Kokoro.from_session(session, str(ROOT / '.local/voice-models/voices-v1.0.bin'))
    assert model.has_timings
    timeline = []
    elapsed = 0.0
    for index, chapter in enumerate(script):
        spoken = ' '.join(cue['pt'] for cue in chapter['cues'])
        phonemes = model.tokenizer.known(' '.join(model.tokenizer.phonemize(spoken, 'pt-br').split()))
        stems = []
        accumulated = ''
        for cue in chapter['cues']:
            accumulated = (accumulated + ' ' + cue['pt']).strip()
            prefix = model.tokenizer.known(' '.join(model.tokenizer.phonemize(accumulated, 'pt-br').split()))
            assert phonemes.startswith(prefix), 'Sequência fonética inconsistente.'
            stems.append(len(prefix))
        stem = f'chapter-{index:02}'
        wav = audio_dir / f'{stem}.speech.wav'
        metadata = audio_dir / f'{stem}.phonemes.json'
        marker = audio_dir / f'{stem}.sha256'
        digest = hashlib.sha256((spoken + VOICE + str(SPEED) + 'continuous-v1').encode()).hexdigest()
        if not (wav.is_file() and metadata.is_file() and marker.is_file() and marker.read_text() == digest):
            samples, sample_rate, timings = model.create_timed(phonemes, VOICE, speed=SPEED, lang='pt-br', is_phonemes=True, continuous=True, sentence_pause=.22, clause_pause=.08)
            assert sample_rate == 24000 and len(samples) / sample_rate >= len(spoken.split()) / 5
            assert len(timings) == len(phonemes)
            pcm = (np.clip(samples, -1, 1) * 32767).astype('<i2').tobytes()
            with wave.open(str(wav), 'wb') as output:
                output.setparams((1, 2, 24000, 0, 'NONE', 'not compressed'))
                output.writeframes(pcm)
            events = [{'phoneme': t.phoneme, 'start': t.start, 'end': t.end} for t in timings]
            metadata.write_text(json.dumps(events, ensure_ascii=False), encoding='utf-8')
            marker.write_text(digest)
        events = json.loads(metadata.read_text(encoding='utf-8'))
        assert ''.join(event['phoneme'] for event in events) == phonemes
        lead = .35
        cues = []
        first = 0
        for cue, boundary in zip(chapter['cues'], stems):
            cues.append({'start': lead + events[first]['start'], 'end': lead + events[boundary - 1]['end'], **cue})
            first = boundary
        with wave.open(str(wav), 'rb') as source:
            pcm = bytes(round(lead * 24000) * 2) + source.readframes(source.getnframes())
        duration = round((len(pcm) / 48000 + .65) * FPS) / FPS
        samples = round(duration * 24000)
        pcm += bytes(max(0, samples * 2 - len(pcm)))
        assert cues[-1]['end'] < duration
        with wave.open(str(audio_dir / f'{stem}.wav'), 'wb') as target:
            target.setparams((1, 2, 24000, 0, 'NONE', 'not compressed'))
            target.writeframes(pcm[:samples * 2])
        timeline.append({'index': index, 'id': chapter['id'], 'title': chapter['title'], 'duration': duration, 'start': elapsed, 'end': elapsed + duration, 'cues': cues, 'continuous_speech': True, 'phonemes': len(events)})
        elapsed += duration
        (WORK / 'timeline.json').write_text(json.dumps(timeline, ensure_ascii=False, indent=2), encoding='utf-8')
        print(f'Narração suave {index + 1}/{len(script)}: {chapter["id"]} · {duration:.2f}s', flush=True)
    (WORK / 'narracao.json').write_text(json.dumps({'engine': 'Kokoro-82M / ONNX', 'voice': VOICE, 'speed': SPEED, 'language': 'pt-BR', 'continuous_chapters': True, 'captions': 'phoneme timing', 'duration': elapsed}, indent=2), encoding='utf-8')
    print(f'Duração total: {elapsed:.2f}s', flush=True)

if __name__ == '__main__':
    main()
