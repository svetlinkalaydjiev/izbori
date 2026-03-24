"""
Convert sections_outputs_from_xlsx.json → data/sections_coworker_scenario.json

Extracts the non-mandatory open stations (remains=1, Посолство_Консулство=false)
so the map can display the coworker's pre-computed scenario alongside ours.
"""
import json, os

SRC = os.path.join(os.path.dirname(__file__), '..', 'sections_outputs_from_xlsx.json')
DST = os.path.join(os.path.dirname(__file__), '..', 'data', 'sections_coworker_scenario.json')

with open(SRC, encoding='utf-8') as f:
    data = json.load(f)

open_stations = [
    {
        "name": s["Секция"],
        "lat":  s["Latitude"],
        "lng":  s["Longitude"],
    }
    for s in data["sections_27102024"]
    if s.get("remains") == 1 and not s.get("Посолство_Консулство")
]

output = {
    "description": "Coworker's scenario (based on 27 Oct 2024 election data)",
    "open_stations": open_stations,
}

with open(DST, 'w', encoding='utf-8') as f:
    json.dump(output, f, ensure_ascii=False, indent=2)

print(f"Written {len(open_stations)} open non-mandatory stations → sections_coworker_scenario.json")
