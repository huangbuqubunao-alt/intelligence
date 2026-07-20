# Synthetic audio test fixture policy

`test_whisper_provider.py` constructs a deterministic mono PCM WAV in its test
temporary directory with Python's standard-library `wave` module (16 kHz,
16-bit, 160 silent frames). It is not downloaded from YouTube or any media
service, and the test never decodes it or loads a Whisper model. Keeping the
fixture generated avoids storing non-source binary data while retaining fully
reproducible offline coverage.
