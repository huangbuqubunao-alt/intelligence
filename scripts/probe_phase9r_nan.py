"""Observe frozen SDK filter failure without changing decode returns/options."""
import json
import socket
from pathlib import Path

import mlx.core as mx
import mlx_whisper
import mlx_whisper.decoding as decoding
import mlx_whisper.load_models as loader
from measure_phase9r_profiles import MODEL


def offline(*args, **kwargs):
    raise RuntimeError('network forbidden')


def main():
    socket.socket.connect = offline
    socket.create_connection = offline
    loader.snapshot_download = offline
    root = Path('.var/phase9r')
    events = []
    original = decoding.ApplyTimestampRules.apply

    def observe(self, logits, tokens):
        result = original(self, logits, tokens)
        if not bool(mx.any(mx.isfinite(result)).item()):
            logprobs = logits - mx.logsumexp(logits, axis=-1, keepdims=True)
            timestamp_mass = logprobs[:, self.tokenizer.timestamp_begin:].logsumexp(axis=-1).item()
            max_text = logprobs[:, :self.tokenizer.timestamp_begin].max().item()
            events.append({'tokens': tokens.tolist()[0], 'sample_begin': self.sample_begin,
                           'timestamp_begin': self.tokenizer.timestamp_begin,
                           'finite_logits_before': int(mx.sum(mx.isfinite(logits)).item()),
                           'finite_logits_after': int(mx.sum(mx.isfinite(result)).item()),
                           'timestamp_logprob_before_structural_mask': timestamp_mass,
                           'max_text_logprob_before_structural_mask': max_text})
        return result

    decoding.ApplyTimestampRules.apply = observe
    raw = mlx_whisper.transcribe(str(root / 'frozen-corpus/medium.wav'), path_or_hf_repo=str(MODEL), task='transcribe', language=None, temperature=0., compression_ratio_threshold=2.4, logprob_threshold=-1., no_speech_threshold=.6, initial_prompt=None, verbose=None, word_timestamps=False, condition_on_previous_text=True)
    report = {'events': events, 'nonfinite_segments': sum(not __import__('math').isfinite(s['avg_logprob']) for s in raw['segments']), 'note': 'No model, option, filter output or decoder return changed.'}
    (root / 'timestamp-filter-origin.json').write_text(json.dumps(report, indent=2, allow_nan=False))
    print(json.dumps({'events': len(events), 'first_summary': {k: v for k, v in events[0].items() if k != 'tokens'}}))


if __name__ == '__main__':
    main()
