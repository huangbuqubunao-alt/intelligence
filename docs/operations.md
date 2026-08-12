# Operations

After installing the distribution, run the formal `youtube-intel` command from the
project root after creating local `config/settings.yaml` and `config/channels.yaml`.
It uses the same CLI entry point as `python -m youtube_intel`. Configuration errors
and unavailable prerequisites exit with `2`; local SQLite or filesystem failures exit
with `3`; a completed command with one or more failed items exits with `1`; complete
success exits with `0`.

```text
youtube-intel check [--channel ID] [--limit N]
youtube-intel process [--video ID] [--resume]
youtube-intel retry [--video ID] [--failed-only]
youtube-intel weekly [--week YYYY-Www]
youtube-intel doctor
youtube-intel smoke-public-subtitles --temporary-root ABSOLUTE_NEW_EMPTY_DIR --video-id ID [--video-id ID] [--video-id ID]
```

`smoke-public-subtitles` is a release-QA-only entry point. It accepts only one
new absolute temporary root and one to three distinct video IDs; it does not
load YAML, environment values, credentials, or the default application
composition. Inside that root it initializes SQLite, empty `data/` and
`test-vault/` directories, and a redacted JSONL log. Per ID it makes one
metadata call, one subtitle-directory call, ranks existing candidates and reads
only the first selected subtitle body once in memory. It uses a fixed 30-second
timeout, never retries or downloads media, and never writes subtitle text,
temporary URLs, absolute paths, business records, or Vault notes. The existing
commands remain fail-closed when no `Operations` composition is injected.

`doctor` validates YAML structure, project-relative storage paths, the existing
`data/state.sqlite` migration record, Vault path containment, yt-dlp/MLX packages,
and the configured Ollama model through one bounded loopback `/api/tags` read. It
does not create Jobs, files, directories, or reports; process videos; read a secret
value or Vault contents; contact YouTube or a cloud Provider; or repair local state.
On a first run, use its missing-state report as guidance, run `check` to perform the
idempotent bootstrap, then run `doctor` again.

Each invocation writes JSONL records to `logs/operations.jsonl` with a UUID4
`run_id`. Records contain timestamp, level, event, run_id, stage and a safe
message; they may also contain video/job IDs, error codes and duration. Exception
objects, configuration values, absolute paths, secret values, subtitles, model
responses, user notes and tracebacks are never serialized. Retain operation logs
for 30 days by policy; this release does not automatically delete any log or file.

## Optional launchd scheduling

`config/launchd/com.yia.agent.daily.plist.example` and
`config/launchd/com.yia.agent.weekly.plist.example` are static examples only.
Choose exactly one schedule, copy it outside the repository, and replace every
`__PROJECT_ROOT__` placeholder with the same absolute project path. Confirm the
working directory, Python executable, command arguments and stdout/stderr log
locations before manually installing it. The daily example runs at 08:00; the
weekly example runs Sunday at 09:00.

Validate a copied plist with `plutil -lint path/to/copied.plist`. Installation,
loading, unloading and removal are explicit user-owned `launchctl` operations and
are deliberately not performed or scripted by this project. To stop scheduling,
manually unload the exact plist you installed and remove that copied file after
confirming its label; do not delete either tracked example.
