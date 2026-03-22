"""
parse_stations.py — parse zayavlenia.txt and write data/stations.json

Input format (one line per station):
    * Location name (count)

Usage:
    python scripts/parse_stations.py
"""

import re
import json
import sys
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).parent.parent
INPUT_FILE = ROOT / 'zayavlenia.txt'
OUTPUT_FILE = ROOT / 'data' / 'stations.json'

LINE_RE = re.compile(r'^\*\s+(.+?)\s+\((\d+)\)\s*$')


def main():
    if not INPUT_FILE.exists():
        print(f'ERROR: {INPUT_FILE} not found.')
        sys.exit(1)

    lines = INPUT_FILE.read_text(encoding='utf-8').splitlines()

    stations = []
    skipped = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        m = LINE_RE.match(line)
        if m:
            stations.append({'name': m.group(1), 'count': int(m.group(2))})
        else:
            skipped.append(line)

    if skipped:
        print(f'WARNING: {len(skipped)} lines did not match expected format:')
        for s in skipped:
            print(f'  {s}')

    total = sum(s['count'] for s in stations)
    print(f'Parsed {len(stations)} stations, {total} total registrations.')

    OUTPUT_FILE.parent.mkdir(exist_ok=True)
    result = {
        'updated': datetime.now(timezone.utc).isoformat(),
        'total': total,
        'stations': stations,
    }
    OUTPUT_FILE.write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding='utf-8'
    )
    print(f'Written to {OUTPUT_FILE}')


if __name__ == '__main__':
    main()
