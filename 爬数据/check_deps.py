"""检查并报告项目依赖是否可用（会在当前解释器中检测）"""
import sys

REQUIRED = [
    ('requests', 'requests'),
    ('bs4', 'beautifulsoup4'),
    ('pandas', 'pandas'),
    ('openpyxl', 'openpyxl'),
]

missing = []

for module, pkg in REQUIRED:
    try:
        __import__(module)
        print(f"OK: import {module}")
    except Exception as e:
        print(f"MISSING: import {module} failed: {type(e).__name__} {e}")
        missing.append(pkg)

if missing:
    print('\nSome packages are missing. Install with:')
    print('    python -m pip install ' + ' '.join(sorted(set(missing))))
    sys.exit(1)

print('\nAll dependencies appear installed in this interpreter.')
