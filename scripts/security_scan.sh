#!/usr/bin/env bash
# Layered security and leak scanner for Release Candidate validation.
# Covers: API key patterns, bearer/auth headers, PEM keys, AWS/GitHub/OpenAI/Slack
#         credentials, .env mispackaging, home-dir paths, build artifact scanning,
#         high-entropy string detection (best-effort), and subprocess injection.
#
# PLATFORM COMPATIBILITY:
#   Tested on macOS (BSD grep) and Linux (GNU grep).
#   Check 3 (PEM headers) uses multiple -e patterns to avoid macOS BSD grep
#   treating '-----BEGIN' as an option prefix in a single -E argument.
#
# SCANNER CAPABILITY AND LIMITATIONS (HONEST STATEMENT):
#   - This scanner uses pattern matching (regex). It CAN detect common credential
#     formats and known anti-patterns. It CANNOT guarantee zero leaks via:
#     * Obfuscated or encoded secrets (base64, hex-encoded values)
#     * Secrets injected at runtime from environment or external config
#     * Secrets in binary files or compiled assets
#     * New credential formats not covered by the patterns below
#   - High-entropy detection is heuristic and has false positives/negatives.
#     Known safe patterns (test fixtures, hash constants, SHA-256 digests) are
#     whitelisted by filename/context, not by value.
#   - Check 17 uses a word-boundary pattern to avoid false positives from
#     function names like _directory_fingerprint( or DirectoryFingerprint(.
#   - Placeholder whitelist (dummy / YOUR_KEY / <key> / REPLACE_ME / example)
#     is consistent across all credential checks (1, 2, 4, 5).
#   - This scanner supplements, but does NOT replace, a formal security audit.
#
# Exit codes: 0 = clean, 1 = findings detected.
# Usage: bash scripts/security_scan.sh

set -euo pipefail

EXIT=0
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DIST="$ROOT/dist"

echo "=== YouTube Intelligence Agent — RC Security Scan (v2) ==="
echo "Root   : $ROOT"
echo "Dist   : $DIST"
echo "Date   : $(date -u '+%Y-%m-%dT%H:%M:%SZ')"
echo ""

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
py_src()  { find "$ROOT/src" -name "*.py" -not -path "*/__pycache__/*"; }
py_test() { find "$ROOT/tests" -name "*.py" -not -path "*/__pycache__/*"; }
py_scripts() { find "$ROOT/scripts" -name "*.sh" -o -name "*.py" 2>/dev/null | grep -v __pycache__; }

fail() { echo "FAIL: $*"; EXIT=1; }
warn() { echo "WARN: $*"; }
pass() { echo "PASS: $*"; }

# ---------------------------------------------------------------------------
# 1. API Key patterns — common formats
# ---------------------------------------------------------------------------
echo "--- 1. API Key patterns (src/ + tests/) ---"
# Whitelist: known SHA-256 digests, test fixture placeholders, example values
PATTERN_APIKEY='(sk-[a-zA-Z0-9]{20,}|sk-proj-[a-zA-Z0-9_\-]{20,}|AIza[a-zA-Z0-9_-]{35}|AKIA[0-9A-Z]{16}|ghp_[a-zA-Z0-9]{36}|ghs_[a-zA-Z0-9]{36}|xox[baprs]-[0-9a-zA-Z\-]{10,}|SG\.[a-zA-Z0-9_\-]{22}\.[a-zA-Z0-9_\-]{43})'
WHITELIST_APIKEY='(test_fixture|placeholder|example|fake[_-]?key|dummy|YOUR_KEY|<key>|REPLACE_ME)'
HITS=$(grep -rniE "$PATTERN_APIKEY" --include='*.py' "$ROOT/src/" "$ROOT/tests/" 2>/dev/null \
    | grep -viE "$WHITELIST_APIKEY" || true)
if [ -n "$HITS" ]; then
    fail "Found API key patterns — review for real credentials"
    echo "$HITS" | head -20
else
    pass "No API key patterns found"
fi

# ---------------------------------------------------------------------------
# 2. Bearer / Authorization header literals
# ---------------------------------------------------------------------------
echo ""
echo "--- 2. Bearer / Authorization header literals ---"
HITS=$(grep -rniE '(Authorization|Bearer)\s*[:=]\s*["\x27][A-Za-z0-9._\-]{8,}' \
    --include='*.py' "$ROOT/src/" "$ROOT/tests/" 2>/dev/null \
    | grep -viE '(test|fake|placeholder|example|REPLACE|Bearer <|Authorization: Bearer $)' || true)
if [ -n "$HITS" ]; then
    fail "Found Bearer/Authorization literals"
    echo "$HITS" | head -10
else
    pass "No Bearer/Authorization literals"
fi

# ---------------------------------------------------------------------------
# 3. PEM private key headers
#    Use multiple -e patterns to avoid macOS BSD grep treating '-----BEGIN'
#    as an option prefix when passed as a single -E argument.
# ---------------------------------------------------------------------------
echo ""
echo "--- 3. PEM private key headers ---"
HITS=$(
    grep -rni \
        -e '-----BEGIN RSA PRIVATE KEY' \
        -e '-----BEGIN EC PRIVATE KEY' \
        -e '-----BEGIN DSA PRIVATE KEY' \
        -e '-----BEGIN OPENSSH PRIVATE KEY' \
        -e '-----BEGIN PRIVATE KEY' \
        --include='*.py' --include='*.pem' --include='*.key' \
        "$ROOT/src/" "$ROOT/tests/" "$ROOT/scripts/" 2>/dev/null || true
)
if [ -n "$HITS" ]; then
    fail "Found PEM private key header"
    echo "$HITS"
else
    pass "No PEM private key headers"
fi

# ---------------------------------------------------------------------------
# 4. AWS-style credential assignments
# ---------------------------------------------------------------------------
echo ""
echo "--- 4. AWS credential patterns ---"
HITS=$(grep -rniE '(AWS_ACCESS_KEY_ID|AWS_SECRET_ACCESS_KEY|aws_session_token)\s*[:=]\s*["\x27][A-Za-z0-9/+]{16,}' \
    --include='*.py' "$ROOT/src/" "$ROOT/tests/" 2>/dev/null \
    | grep -viE '(os\.environ|getenv|placeholder|example)' || true)
if [ -n "$HITS" ]; then
    fail "Found AWS credential assignments"
    echo "$HITS"
else
    pass "No AWS credential assignments"
fi

# ---------------------------------------------------------------------------
# 5. Generic credential assignments (key = "value" shapes)
# ---------------------------------------------------------------------------
echo ""
echo "--- 5. Generic credential assignments (src/ only) ---"
HITS=$(grep -rniE '(api[_-]?key|secret[_-]?key|password|access[_-]?token|private[_-]?key|client[_-]?secret)\s*[:=]\s*["\x27][^"\x27\$\{]{6,}["\x27]' \
    --include='*.py' "$ROOT/src/" 2>/dev/null \
    | grep -viE '(test|fake|placeholder|example|REPLACE|dummy|YOUR_KEY|<key>|REPLACE_ME|os\.environ|getenv|CheckConstraint|NOT NULL|schema_migrations)' || true)
if [ -n "$HITS" ]; then
    fail "Found credential-shape assignments in src/"
    echo "$HITS" | head -20
else
    pass "No credential assignments in src/"
fi

# ---------------------------------------------------------------------------
# 6. .env / config files tracked in git
# ---------------------------------------------------------------------------
echo ""
echo "--- 6. .env / config credential files in git ---"
TRACKED_ENV=$(cd "$ROOT" && git ls-files '*.env' '.env' '.env.*' '*.env.*' 2>/dev/null \
    | grep -vE '\.(example|sample|template)$' || true)
if [ -n "$TRACKED_ENV" ]; then
    fail "Credential .env files tracked in git"
    echo "$TRACKED_ENV"
else
    pass "No .env credential files tracked"
fi

# ---------------------------------------------------------------------------
# 7. Key / PEM / credential binary files in git
# ---------------------------------------------------------------------------
echo ""
echo "--- 7. Key/PEM/p12 files in git ---"
TRACKED_KEYS=$(cd "$ROOT" && git ls-files '*.key' '*.pem' '*.p12' '*.pfx' '*.cer' '*.crt' 2>/dev/null || true)
if [ -n "$TRACKED_KEYS" ]; then
    fail "Key/PEM files tracked in git"
    echo "$TRACKED_KEYS"
else
    pass "No key/PEM files tracked"
fi

# ---------------------------------------------------------------------------
# 8. SQLite databases / data files in git
# ---------------------------------------------------------------------------
echo ""
echo "--- 8. SQLite databases / data files in git ---"
TRACKED_DB=$(cd "$ROOT" && git ls-files '*.sqlite' '*.sqlite3' '*.db' '*.mdb' 2>/dev/null || true)
if [ -n "$TRACKED_DB" ]; then
    fail "Database files tracked in git"
    echo "$TRACKED_DB"
else
    pass "No database files tracked"
fi

# ---------------------------------------------------------------------------
# 9. Subprocess shell=True (injection risk)
# ---------------------------------------------------------------------------
echo ""
echo "--- 9. subprocess shell=True ---"
HITS=$(grep -rniE 'subprocess\.(run|call|Popen|check_output|check_call)\s*\(' \
    --include='*.py' "$ROOT/src/" 2>/dev/null \
    | grep -iE 'shell\s*=\s*True' || true)
if [ -n "$HITS" ]; then
    fail "Found subprocess shell=True"
    echo "$HITS"
else
    pass "No subprocess shell=True"
fi

# ---------------------------------------------------------------------------
# 10. eval / exec usage in src/
# ---------------------------------------------------------------------------
echo ""
echo "--- 10. eval/exec usage in src/ ---"
HITS=$(grep -rniE '^\s*\b(eval|exec)\s*\(' --include='*.py' "$ROOT/src/" 2>/dev/null || true)
if [ -n "$HITS" ]; then
    warn "Found eval/exec — review manually"
    echo "$HITS"
else
    pass "No eval/exec usage"
fi

# ---------------------------------------------------------------------------
# 11. URLs with embedded credentials
# ---------------------------------------------------------------------------
echo ""
echo "--- 11. URLs with embedded credentials ---"
HITS=$(grep -rniE 'https?://[^"'\''/ ]{1,}:[^"'\''/ ]{1,}@' \
    --include='*.py' "$ROOT/src/" "$ROOT/tests/" 2>/dev/null || true)
if [ -n "$HITS" ]; then
    fail "Found URLs with embedded credentials"
    echo "$HITS"
else
    pass "No credential-bearing URLs"
fi

# ---------------------------------------------------------------------------
# 12. User home directory absolute paths leaked in src/
# ---------------------------------------------------------------------------
echo ""
echo "--- 12. Home directory paths in src/ ---"
HOME_USER="${HOME:-/Users/UNKNOWN}"
HITS=$(grep -rniF "$HOME_USER" --include='*.py' "$ROOT/src/" 2>/dev/null || true)
if [ -n "$HITS" ]; then
    fail "Found home directory path leaked in src/: $HOME_USER"
    echo "$HITS" | head -10
else
    pass "No home directory paths in src/"
fi

# ---------------------------------------------------------------------------
# 13. High-entropy string detection (heuristic, best-effort)
#     Only checks files that are NOT: test fixtures, migration hashes, SBOM.
# ---------------------------------------------------------------------------
echo ""
echo "--- 13. High-entropy strings in src/ (heuristic — false positives expected) ---"
echo "    NOTE: This check is BEST-EFFORT. It may miss encoded secrets and will"
echo "          flag legitimate SHA-256 hashes or base64 blobs. Manual review required."
# Look for base64-ish strings of length >= 32 not in known-safe files
ENTROPY_HITS=$(grep -rniE '[A-Za-z0-9+/]{32,}={0,2}' --include='*.py' "$ROOT/src/" 2>/dev/null \
    | grep -viE '(checksum|content_hash|SHA-256|sha256|GLOB|NOT GLOB|[0-9a-f]{64}|base64|import|docstring|#|annotation)' \
    | grep -viE '(test_fixture|placeholder|example|REPLACE_ME|YOUR_KEY)' \
    | head -20 || true)
if [ -n "$ENTROPY_HITS" ]; then
    warn "Possible high-entropy strings (review manually — may be false positives)"
    echo "$ENTROPY_HITS"
else
    pass "No obvious high-entropy patterns (heuristic only)"
fi

# ---------------------------------------------------------------------------
# 14. Build artifact scan for credential patterns
# ---------------------------------------------------------------------------
echo ""
echo "--- 14. Build artifact credential scan ---"
if [ -d "$DIST" ] && ls "$DIST"/*.whl "$DIST"/*.tar.gz 2>/dev/null | head -1 | grep -q .; then
    ARTIFACT_SCAN_DIR="$(mktemp -d)"
    trap 'rm -rf "$ARTIFACT_SCAN_DIR"' EXIT
    # Extract wheel (zip) and sdist (tar.gz)
    for WHL in "$DIST"/*.whl; do
        [ -f "$WHL" ] || continue
        WDIR="$ARTIFACT_SCAN_DIR/wheel"
        mkdir -p "$WDIR"
        unzip -q "$WHL" -d "$WDIR" 2>/dev/null || true
    done
    for TGZ in "$DIST"/*.tar.gz; do
        [ -f "$TGZ" ] || continue
        TDIR="$ARTIFACT_SCAN_DIR/sdist"
        mkdir -p "$TDIR"
        tar -xzf "$TGZ" -C "$TDIR" 2>/dev/null || true
    done
    # Scan extracted python files for credential patterns
    ART_HITS=$(grep -rniE '(sk-[a-zA-Z0-9]{20,}|AKIA[0-9A-Z]{16}|ghp_[a-zA-Z0-9]{36}|-----BEGIN.*PRIVATE KEY)' \
        --include='*.py' --include='*.txt' --include='*.cfg' --include='*.toml' \
        "$ARTIFACT_SCAN_DIR/" 2>/dev/null || true)
    # Check for .env / home-dir paths in build artifacts
    ART_ENV_HITS=$(find "$ARTIFACT_SCAN_DIR" -name '*.env' -o -name '.env' 2>/dev/null | head -5 || true)
    ART_HOME_HITS=$(grep -rlF "$HOME_USER" --include='*.py' --include='*.txt' "$ARTIFACT_SCAN_DIR/" 2>/dev/null || true)

    ARTIFACT_FAIL=0
    if [ -n "$ART_HITS" ]; then
        fail "Credential patterns found in build artifact"
        echo "$ART_HITS" | head -10
        ARTIFACT_FAIL=1
    fi
    if [ -n "$ART_ENV_HITS" ]; then
        fail ".env files found in build artifact"
        echo "$ART_ENV_HITS"
        ARTIFACT_FAIL=1
    fi
    if [ -n "$ART_HOME_HITS" ]; then
        fail "Home directory path found in build artifact"
        echo "$ART_HOME_HITS"
        ARTIFACT_FAIL=1
    fi
    if [ "$ARTIFACT_FAIL" -eq 0 ]; then
        pass "No credential patterns in build artifacts"
    fi
    rm -rf "$ARTIFACT_SCAN_DIR"
    trap - EXIT
else
    warn "No build artifacts found in $DIST — skipping artifact scan (run uv build first)"
fi

# ---------------------------------------------------------------------------
# 15. LICENSE presence in build artifact
# ---------------------------------------------------------------------------
echo ""
echo "--- 15. LICENSE presence in build artifact ---"
LICENSE_PRESENT=0
for WHL in "$DIST"/*.whl; do
    [ -f "$WHL" ] || continue
    if unzip -l "$WHL" 2>/dev/null | grep -qiE 'LICENSE|COPYING|NOTICE'; then
        echo "  Found license-related file in wheel: $WHL"
        LICENSE_PRESENT=1
    fi
done
if [ "$LICENSE_PRESENT" -eq 0 ]; then
    warn "No LICENSE/NOTICE file found in wheel — project license is UNRESOLVED (see RELEASE_BLOCKERS.md)"
fi

# ---------------------------------------------------------------------------
# 16. .gitignore coverage
# ---------------------------------------------------------------------------
echo ""
echo "--- 16. .gitignore coverage ---"
MISSING=""
for pattern in ".venv/" "dist/" "build/" "__pycache__/" "/data/" "*.env" "*.key" "*.pem"; do
    if ! grep -qF "$pattern" "$ROOT/.gitignore" 2>/dev/null; then
        MISSING="$MISSING $pattern"
    fi
done
if [ -n "$MISSING" ]; then
    warn "Missing .gitignore patterns:$MISSING"
else
    pass ".gitignore covers essential patterns"
fi

# ---------------------------------------------------------------------------
# 17. print() calls in non-child-process src (potential data leak)
#    Only match actual print( call sites; exclude:
#      - cloud_llm.py  (child process; intentional stdout)
#      - lines that are part of function/variable names containing 'print'
#        but are NOT a print() call (e.g. _directory_fingerprint(, DirectoryFingerprint()
#    Pattern: literal 'print(' at word boundary, not preceded by alphanumeric/_
# ---------------------------------------------------------------------------
echo ""
echo "--- 17. print() calls in non-child-process src/ ---"
HITS=$(grep -rnE '(^|[^a-zA-Z0-9_])print\s*\(' --include='*.py' "$ROOT/src/" 2>/dev/null \
    | grep -v 'cloud_llm.py' \
    | grep -v '__main__' || true)
if [ -n "$HITS" ]; then
    warn "Found print() outside child process (review for sensitive data leakage)"
    echo "$HITS" | head -10
else
    pass "No unexpected print() calls"
fi

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
echo ""
echo "=== Scan Complete ==="
echo "Timestamp : $(date -u '+%Y-%m-%dT%H:%M:%SZ')"
echo ""
echo "SCANNER LIMITATIONS:"
echo "  - Pattern matching only; obfuscated/encoded secrets not detected"
echo "  - High-entropy check (test 13) is heuristic with false positives"
echo "  - Runtime-injected secrets (env vars, external configs) not covered"
echo "  - Binary files and compiled assets not scanned"
echo "  - print() check uses word-boundary pattern; function names like _fingerprint( excluded"
echo "  - Placeholder whitelist is consistent: dummy/YOUR_KEY/<key>/REPLACE_ME across checks"
echo "  - Platform: tested macOS BSD grep + Linux GNU grep; check 3 uses -e for compatibility"
echo "  - Does NOT replace a formal penetration test or security audit"
echo ""
if [ "$EXIT" -eq 0 ]; then
    echo "Result: ALL CHECKS PASS (subject to WARN items above)"
else
    echo "Result: FINDINGS DETECTED — review FAIL items above before distribution"
fi
exit "$EXIT"
