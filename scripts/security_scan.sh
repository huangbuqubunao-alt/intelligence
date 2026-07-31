#!/usr/bin/env bash
# Comprehensive security and leak scanner for Release Candidate validation.
# Exit codes: 0 = clean, 1 = findings detected.
# Usage: bash scripts/security_scan.sh
set -euo pipefail

EXIT=0
ROOT="$(cd "$(dirname "$0")/.." && pwd)"

echo "=== YouTube Intelligence Agent — RC Security Scan ==="
echo "Root: $ROOT"
echo ""

# 1. Credential and secret patterns in source
echo "--- 1. Credential patterns in src/ ---"
HITS=$(grep -rniE '(api[_-]?key|secret[_-]?key|password|access[_-]?token|bearer|private[_-]?key)\s*[:=]\s*["\x27]' "$ROOT/src/" 2>/dev/null || true)
if [ -n "$HITS" ]; then
    echo "FAIL: Found credential-like assignments in source"
    echo "$HITS"
    EXIT=1
else
    echo "PASS: No credential assignments in source"
fi

# 2. Hardcoded secrets in tests (exclude known safe patterns)
echo ""
echo "--- 2. Hardcoded secrets in tests/ ---"
HITS=$(grep -rniE '(sk-[a-zA-Z0-9]{20,}|ghp_[a-zA-Z0-9]{36}|AIza[a-zA-Z0-9_-]{35})' "$ROOT/tests/" 2>/dev/null || true)
if [ -n "$HITS" ]; then
    echo "FAIL: Found hardcoded secret patterns in tests"
    echo "$HITS"
    EXIT=1
else
    echo "PASS: No hardcoded secrets in tests"
fi

# 3. .env files tracked
echo ""
echo "--- 3. .env files in git ---"
HITS=$(cd "$ROOT" && git ls-files '*.env' '.env.*' 2>/dev/null | grep -v '\.example$' | grep -v '\.sample$' || true)
if [ -n "$HITS" ]; then
    echo "FAIL: .env files tracked in git"
    echo "$HITS"
    EXIT=1
else
    echo "PASS: No .env files tracked"
fi

# 4. Key/pem files tracked
echo ""
echo "--- 4. Key/PEM files in git ---"
HITS=$(cd "$ROOT" && git ls-files '*.key' '*.pem' '*.p12' '*.pfx' 2>/dev/null || true)
if [ -n "$HITS" ]; then
    echo "FAIL: Key/PEM files tracked in git"
    echo "$HITS"
    EXIT=1
else
    echo "PASS: No key/PEM files tracked"
fi

# 5. SQLite databases tracked
echo ""
echo "--- 5. SQLite databases in git ---"
HITS=$(cd "$ROOT" && git ls-files '*.sqlite' '*.sqlite3' '*.db' 2>/dev/null || true)
if [ -n "$HITS" ]; then
    echo "FAIL: SQLite databases tracked in git"
    echo "$HITS"
    EXIT=1
else
    echo "PASS: No SQLite databases tracked"
fi

# 6. Path traversal patterns in source
echo ""
echo "--- 6. Path traversal vulnerabilities ---"
HITS=$(grep -rnE '(\.\./|\.\.\\\\)' "$ROOT/src/" 2>/dev/null | grep -v 'test' | grep -v '# ' | grep -v '"' || true)
if [ -n "$HITS" ]; then
    echo "WARN: Found path traversal patterns in source (review manually)"
    echo "$HITS"
else
    echo "PASS: No path traversal patterns found"
fi

# 7. Subprocess with shell=True
echo ""
echo "--- 7. Subprocess shell=True ---"
HITS=$(grep -rnE 'subprocess\.(run|call|Popen|check_output)\(.*shell\s*=\s*True' "$ROOT/src/" 2>/dev/null || true)
if [ -n "$HITS" ]; then
    echo "FAIL: Found subprocess shell=True"
    echo "$HITS"
    EXIT=1
else
    echo "PASS: No subprocess shell=True"
fi

# 8. eval/exec usage
echo ""
echo "--- 8. eval/exec usage ---"
HITS=$(grep -rnE '\beval\(|exec\(' "$ROOT/src/" 2>/dev/null || true)
if [ -n "$HITS" ]; then
    echo "WARN: Found eval/exec usage (review manually)"
    echo "$HITS"
else
    echo "PASS: No eval/exec usage"
fi

# 9. Insecure temp file creation
echo ""
echo "--- 9. Insecure temp file creation ---"
HITS=$(grep -rnE '(mktemp|NamedTemporaryFile|TemporaryFile|mkdtemp)' "$ROOT/src/" --include='*.py' 2>/dev/null || true)
if [ -n "$HITS" ]; then
    echo "WARN: Found temp file usage (review for secure defaults)"
    echo "$HITS"
else
    echo "PASS: No insecure temp file patterns"
fi

# 10. Credential names followed by assignment in new diff lines
echo ""
echo "--- 10. Credential-shape leak scan on staged+working diff ---"
DIFF=$(cd "$ROOT" && git diff HEAD 2>/dev/null | grep '^+[^+]' || true)
LEAK_HITS=$(echo "$DIFF" | grep -iE '(api[_-]?key|secret|password|token|credential|bearer|authorization)\s*[:=]\s*["\x27]' || true)
if [ -n "$LEAK_HITS" ]; then
    echo "FAIL: Credential-shape patterns in new diff lines"
    echo "$LEAK_HITS"
    EXIT=1
else
    echo "PASS: No credential-shape patterns in new diff"
fi

# 11. Sensitive URLs in source
echo ""
echo "--- 11. Hardcoded URLs with credentials ---"
HITS=$(grep -rnE 'https?://[^"]*:[^"]*@' "$ROOT/src/" --include='*.py' 2>/dev/null || true)
if [ -n "$HITS" ]; then
    echo "FAIL: Found URLs with embedded credentials"
    echo "$HITS"
    EXIT=1
else
    echo "PASS: No credential-bearing URLs"
fi

# 12. Print statements leaking sensitive data
echo ""
echo "--- 12. Print statements in non-child source ---"
HITS=$(grep -rn 'print(' "$ROOT/src/" --include='*.py' 2>/dev/null | grep -v 'cloud_llm.py' | grep -v '__main__' | grep -v '__pycache__' || true)
if [ -n "$HITS" ]; then
    echo "WARN: Found print statements outside child process (review for sensitive data)"
    echo "$HITS" | head -10
else
    echo "PASS: No unexpected print statements"
fi

# 13. .gitignore coverage
echo ""
echo "--- 13. .gitignore coverage ---"
MISSING=""
for pattern in ".venv/" "dist/" "build/" "*.egg-info/" "__pycache__/" "/data/" "/logs/" ".env" "*.key" "*.pem" ".DS_Store"; do
    if ! grep -qF "$pattern" "$ROOT/.gitignore" 2>/dev/null; then
        MISSING="$MISSING $pattern"
    fi
done
if [ -n "$MISSING" ]; then
    echo "WARN: Missing .gitignore patterns:$MISSING"
else
    echo "PASS: .gitignore covers essential patterns"
fi

# Summary
echo ""
echo "=== Scan Complete ==="
if [ "$EXIT" -eq 0 ]; then
    echo "Result: ALL PASS"
else
    echo "Result: FINDINGS DETECTED — review above"
fi
exit "$EXIT"
