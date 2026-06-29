# Autonomous Agent Loop

SIR Saathi is built in small validated slices. Each slice must pass product, test, review, and privacy gates before it is committed and pushed.

## Loop

1. Pick one backlog slice with a user-visible or safety outcome.
2. Check repository status and confirm only intended files will be touched.
3. Implement the smallest useful change.
4. Run targeted tests, smoke checks, and `python scripts/check_sensitive.py`.
5. Review the diff for bugs, privacy regressions, and generated-data leaks.
6. Commit without `Co-authored-by` trailers.
7. Push to the personal GitHub remote.
8. Record risks and choose the next slice.

## Non-Negotiable Gates

- No raw electoral roll PDFs, parsed voter exports, generated datasets, or credentials in Git.
- No full EPIC numbers or real voter addresses in fixtures, docs, logs, screenshots, or tests.
- Search features must be scoped, redacted, and rate-limited before public launch.
- Official source links and freshness dates must be visible for voter guidance.

## Standard Validation Commands

```sh
python scripts/check_sensitive.py
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest
python -m py_compile pipeline/parse_2002.py pipeline/transliterate.py
python pipeline/transliterate.py --test
```
