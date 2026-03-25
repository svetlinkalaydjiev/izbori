"""
parse_stations.py — parse zayavlenia.txt and write data/sections_2026.json
                    also converts bulgarian_stations_2024.csv → data/sections_2024.json

Input format (one line per station):
    Location name (count)

Usage:
    python scripts/parse_stations.py
"""

import re
import csv
import json
import sys
from pathlib import Path
from datetime import datetime, timezone
from collections import defaultdict

ROOT         = Path(__file__).parent.parent
INPUT_FILE   = ROOT / 'zayavlenia.txt'
CSV_FILE     = ROOT / 'bulgarian_stations_2024.csv'
OUT_2024     = ROOT / 'data' / 'sections_2024.json'
OUT_2026     = ROOT / 'data' / 'sections_2026.json'

LINE_RE = re.compile(r'^(.+?)\s+\((\d+)\)\s*$')

def normalize(s):
    """Normalize smart/curly quotes to straight quotes."""
    return s.replace('\u201c', '"').replace('\u201d', '"').replace('\u2018', "'").replace('\u2019', "'")

# Maps each zayavlenia name → 2024 CSV station id.
# Multiple names mapping to the same id are merged (counts summed).
MAPPING = {
    # Embassies / consulates
    "Вашингтон (Посолство)":                                                      "321070453",
    "Лос Анджелис (Генерално консулство)":                                        "321070465",
    "Ню Йорк (Генерално консулство)":                                             "321070475",
    "Чикаго (Генерално консулство)":                                              "321070494",
    # Northeast
    "Atlantic City, New Jersey, EHT, Bulgarian School Читанка":                   "321070448",
    "Boston":                                                                      "321070450",
    "Билирика, 310 River St, Billerica, MA USA":                                  "321070449",
    "Билирика, MA, 310 River Street, Billerica, MA":                              "321070449",
    "Barnstable, MA":                                                              "321070491",
    "Хаянис - Кейп Код":                                                          "321070491",
    "Нантакет МА, САЩ":                                                           "321070470",
    "Нантъкет":                                                                    "321070470",
    "Queens New York":                                                             "321070476",
    "Алфа Арт галерия Ню Бронсуик, Ню Джърси":                                   "321070474",
    "Ukrainian American Club of Southport, 279 King Drive, Southport, CT":        "321070473",
    "Норуолк":                                                                     "321070473",
    "Broomall, Pa, Euro Market":                                                   "321070451",
    "Питсбърг, Пенсилвания":                                                      "321070478",
    "Бъфало Ню Йорк":                                                              "321070452",
    # Mid-Atlantic / South
    "Вирджиния Бийч, Вирджиния":                                                  "321070454",
    "Шарлът-Матюс, Шарлът-Матюс":                                                 "321070495",
    # Florida
    "BULGARIAN LEARNING CENTER \"RODINA\"-ST. PETERSBURG FL, INC., 301 37TH AVE. N ST. PETERSBURG, FL": "321070485",
    "Saint Petersburg ABRITUS MINI MARKET, Saint Petersburg Florida":              "321070485",
    "Сейнт Питърсбърг, Флорид, Българска православна църква \"Света Петка\"":     "321070485",
    "Алтамонт, Флорида,Храм \"Свети Георги\",, Алтамонт, район Орландо Флорида": "321070445",
    "Джаксънвил, Флорида":                                                         "321070461",
    "Маями, Флорида, Форт Лотърдейл":                                              "321070467",
    "Нейпълс, Флорида / Naples, FL":                                               "321070472",
    # Southeast
    "Marietta, GA - MALINCHO Fresh Market, Atlanta, GA":                           "321070447",
    "Малинчо, Мариета":                                                             "321070447",
    # Midwest
    "Сейнт Луис , Мисури":                                                         "321070484",
    "Индианаполис, Индиана, САЩ":                                                  "321070462",
    "Детройт":                                                                     "321070460",
    "Минеаполис, Минесота":                                                        "321070469",
    "Хинсдейл":                                                                    "321070492",
    "Маунт Проспект, Илинойс - Културен център \"Българика\"":                    "321070466",
    "Дес Плейнс ,МАГАЗИН МАЛИНЧО,Илинойс,САЩ":                                   "321070457",
    "Дес Плейнс, Център \"Малката България\"":                                    "321070459",
    # South / Southwest
    "Нашвил, Тенеси":                                                              "321070471",
    "Синсинати, Охайо":                                                            "321070487",
    "Далас, Тексас, Далас, Тексас":                                               "321070455",
    "Остин, Тексас":                                                               "321070477",
    "Хюстън, Тексас":                                                              "321070493",
    # Mountain / West
    "Denver, Colorado":                                                             "321070456",
    "Денвър":                                                                       "321070456",
    "Финикс, Аризона":                                                             "321070490",
    "Солт Лейк Сити, Юта":                                                         "321070488",
    # West Coast
    "San Diego, California, Mira Mesa":                                            "321070482",
    "San Francisco, CA":                                                           "321070483",
    "Sunnyvale":                                                                   "321070489",
    "Ървайн/Тъстин, Калифорния":                                                   "321070497",
    "Tustin, California":                                                          "321070497",
    "Las Vegas, Nevada, Restaurant BESO":                                          "321070464",
    "Сакраменто, Сакраменто, Калифорния":                                          "321070481",
    "Мартинез Св.св.Кирил и Методи Българската църква, Мартинез,Калифирния, Съединени американски щати": "321070463",
    "Мартинес българска църква":                                                   "321070463",
    # Northwest
    "Сиатъл":                                                                      "321070486",
    "Портланд, Орегон":                                                            "321070479",
    # Virginia
    "Ричмънд, Вирджиния":                                                          "321070480",
}


# Unmatched zayavlenia entries with manually looked-up coordinates.
# Multiple zayavlenia names pointing to the same key are merged.
UNMATCHED_COORDS = {
    "Културен център \"Магура\" Шамбург / Schaumburg, Chicago, Illinois": {
        "name": "Schaumburg (Magura) IL", "lat": 42.0516, "lng": -88.0497,
    },
    "Българска Православна Църква Свети \" Иван Рилски\", Чикаго": {
        "name": "Chicago — St. Ivan Rilski IL",  "lat": 41.9636, "lng": -87.7737,
    },
    "Chesterfield MO":   {"name": "Chesterfield MO",  "lat": 38.6631, "lng": -90.5771},
    "Newark, Delaware":  {"name": "Newark DE",         "lat": 39.6837, "lng": -75.7497},
    "Raleigh, NC":       {"name": "Raleigh NC",        "lat": 35.7796, "lng": -78.6382},
    "Myrtle Beach":      {"name": "Myrtle Beach SC",   "lat": 33.6891, "lng": -78.8867},
    "Myrtle Beach SC":   {"name": "Myrtle Beach SC",   "lat": 33.6891, "lng": -78.8867},
    "Roanoke, VA":       {"name": "Roanoke VA",        "lat": 37.2710, "lng": -79.9414},
    "Сиракюз, Ню Йорк":  {"name": "Syracuse NY",       "lat": 43.0481, "lng": -76.1474},
    "Чарлстън, Южна Каролина": {"name": "Charleston SC", "lat": 32.7765, "lng": -79.9311},
}


def load_csv():
    stations = {}
    with open(CSV_FILE, encoding='utf-8') as f:
        for row in csv.DictReader(f):
            stations[row['id']] = {
                'name':      row['name'],
                'lat':       float(row['lat']),
                'lng':       float(row['lng']),
                'mandatory': row['mandatory'] == 'true',
                'voters':    int(row['voters']),
            }
    return stations


def write_json(path, stations):
    total = sum(s['voters'] for s in stations)
    stations_sorted = sorted(stations, key=lambda s: s['voters'], reverse=True)
    path.parent.mkdir(exist_ok=True)
    path.write_text(
        json.dumps({
            'updated':  datetime.now(timezone.utc).isoformat(),
            'total':    total,
            'stations': stations_sorted,
        }, ensure_ascii=False, indent=2),
        encoding='utf-8'
    )
    print(f'Written {len(stations_sorted)} stations ({total} voters) → {path.name}')


def main():
    if not INPUT_FILE.exists():
        print(f'ERROR: {INPUT_FILE} not found.')
        sys.exit(1)

    csv_stations = load_csv()

    # ── sections_2024.json ────────────────────────────────────────────────────
    write_json(OUT_2024, list(csv_stations.values()))

    # ── Parse zayavlenia.txt ──────────────────────────────────────────────────
    raw = []
    skipped = []
    for line in INPUT_FILE.read_text(encoding='utf-8').splitlines():
        line = line.strip()
        if not line:
            continue
        m = LINE_RE.match(line)
        if m:
            raw.append({'name': normalize(m.group(1)), 'count': int(m.group(2))})
        else:
            skipped.append(line)

    if skipped:
        print(f'WARNING: {len(skipped)} lines did not match expected format:')
        for s in skipped:
            print(f'  {s}')

    # Each group tracks: total voters, and the zayavlenia name with the most voters
    # merged_csv  keyed by csv_id
    # merged_extra keyed by clean name from UNMATCHED_COORDS
    merged_csv   = defaultdict(lambda: {'voters': 0, 'best_name': '', 'best_count': 0})
    merged_extra = defaultdict(lambda: {'voters': 0, 'best_name': '', 'best_count': 0})
    truly_unmatched = []

    for entry in raw:
        csv_id = MAPPING.get(entry['name'])
        if csv_id:
            g = merged_csv[csv_id]
            g['voters'] += entry['count']
            if entry['count'] > g['best_count']:
                g['best_name']  = entry['name']
                g['best_count'] = entry['count']
        elif entry['name'] in UNMATCHED_COORDS:
            key = UNMATCHED_COORDS[entry['name']]['name']
            g = merged_extra[key]
            g['voters'] += entry['count']
            g.update(UNMATCHED_COORDS[entry['name']])   # lat/lng/name (clean fallback)
            if entry['count'] > g['best_count']:
                g['best_name']  = entry['name']
                g['best_count'] = entry['count']
        else:
            truly_unmatched.append(entry)

    if truly_unmatched:
        print(f'WARNING — unresolved entries ({len(truly_unmatched)}):')
        for u in truly_unmatched:
            print(f'  {u["name"]} ({u["count"]})')

    # ── sections_2026.json ────────────────────────────────────────────────────
    stations_2026 = []
    for csv_id, g in merged_csv.items():
        base = csv_stations[csv_id]
        stations_2026.append({
            'name':      g['best_name'],
            'lat':       base['lat'],
            'lng':       base['lng'],
            'mandatory': base['mandatory'],
            'voters':    g['voters'],
        })
    for g in merged_extra.values():
        stations_2026.append({
            'name':      g['best_name'],
            'lat':       g['lat'],
            'lng':       g['lng'],
            'mandatory': False,
            'voters':    g['voters'],
        })

    print(f'2026: {len(merged_csv)} matched to 2024, {len(merged_extra)} geocoded')
    write_json(OUT_2026, stations_2026)


if __name__ == '__main__':
    main()
