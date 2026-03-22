"""
parse_stations.py — parse zayavlenia.txt and write data/stations.json

Usage:
    python scripts/parse_stations.py

Input:  zayavlenia.txt  (save the CIK page as plain text)
Output: data/stations.json
"""

import re
import json
import sys
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).parent.parent
INPUT_FILE = ROOT / 'zayavlenia.txt'
OUTPUT_FILE = ROOT / 'data' / 'stations.json'


def parse_usa_stations(text):
    lines = text.splitlines()

    # Find the line containing "САЩ (N)"
    usa_idx = None
    total = None
    for i, line in enumerate(lines):
        m = re.search(r'САЩ\s*\((\d+)\)', line)
        if m:
            usa_idx = i
            total = int(m.group(1))
            break

    if usa_idx is None:
        print('ERROR: Could not find "САЩ (N)" in the file.')
        sys.exit(1)

    print(f'Found "САЩ ({total})" at line {usa_idx + 1}')

    # Collect lines after the heading until the next country heading
    # A country heading is any non-empty line containing "(N)"
    stations = []
    for line in lines[usa_idx + 1:]:
        stripped = line.strip()
        if not stripped:
            continue
        if re.search(r'\(\d+\)', stripped):
            print(f'Stopping at next heading: {stripped[:80]}')
            break
        stations.append(stripped)

    return total, stations


def main():
    if not INPUT_FILE.exists():
        print(f'ERROR: {INPUT_FILE} not found.')
        sys.exit(1)

    text = INPUT_FILE.read_text(encoding='utf-8')
    print(f'Read {len(text)} chars from {INPUT_FILE.name}')

    total, stations = parse_usa_stations(text)
    print(f'Parsed {len(stations)} stations:')
    for s in stations:
        print(f'  {s}')

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
    print(f'\nWritten to {OUTPUT_FILE}')


if __name__ == '__main__':
    main()
