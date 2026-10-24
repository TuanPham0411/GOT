from __future__ import annotations

import collections
import hashlib
import json
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
RESOURCE = ROOT / "resource"
failures: list[str] = []


def topic(name: str) -> dict:
    return json.loads((RESOURCE / name).read_text(encoding="utf-8"))


topic_files = sorted(RESOURCE.glob("topic-*.json"))
counts: dict[str, int] = {}
for path in topic_files:
    data = json.loads(path.read_text(encoding="utf-8"))
    items = data.get("items", [])
    counts[path.name] = len(items)
    for item in items:
        key = f"{path.name}/{item.get('slug', item.get('id'))}"
        if not item.get("viName") or not item.get("enName"):
            failures.append(f"{key}: missing bilingual name")
        if not item.get("description") or not item.get("descriptionEn"):
            failures.append(f"{key}: missing bilingual description")
        for fact in item.get("facts", []):
            if not all(fact.get(k) for k in ("label", "value", "labelEn", "valueEn")):
                failures.append(f"{key}: incomplete bilingual fact")

for name, minimum in {"animal": 351, "plant": 100, "object": 100, "transport": 100}.items():
    items = topic(f"topic-{name}.json")["items"]
    if len(items) < minimum:
        failures.append(f"{name}: only {len(items)} items")
    for field in ("slug", "viName", "enName", "image", "checksum"):
        dupes = [v for v, n in collections.Counter(str(x.get(field, "")).casefold() for x in items).items() if v and n > 1]
        if dupes:
            failures.append(f"{name}: duplicate {field}: {dupes[:3]}")
    for item in items:
        image = RESOURCE / item["image"]
        if not image.exists():
            failures.append(f"{name}/{item['slug']}: missing image")
            continue
        if hashlib.sha256(image.read_bytes()).hexdigest() != item["checksum"]:
            failures.append(f"{name}/{item['slug']}: checksum mismatch")
        with Image.open(image) as im:
            if im.format != "PNG" or "A" not in im.getbands() or im.getchannel("A").getextrema()[0] == 255:
                failures.append(f"{name}/{item['slug']}: not transparent PNG")

animals = topic("topic-animal.json")["items"]
expected = {
    "chon-hoi-soc-bac-my": ("Chồn hôi sọc Bắc Mỹ", "Striped Skunk", "Mephitis mephitis"),
    "khi-vang": ("Khỉ vàng", "Rhesus Macaque", "Macaca mulatta"),
    "thu-long-nhim-mo-dai-phuong-dong": ("Thú lông nhím mỏ dài phương Đông", "Eastern Long-beaked Echidna", "Zaglossus bartoni"),
}
by_slug = {x["slug"]: x for x in animals}
for slug, identity in expected.items():
    item = by_slug.get(slug)
    if not item or tuple(item.get(k) for k in ("viName", "enName", "scientificName")) != identity:
        failures.append(f"animal identity: {slug}")
if {"chon-muc", "thu-luon"} & by_slug.keys():
    failures.append("retired incorrect animal records remain active")

# Regression gate for the old substring classifier (`oc-`, `hau-`, `ong-`,
# `cu-`, `ech-`), which confused Vietnamese syllables inside unrelated names.
expected_groups = {
    "vooc-bac": "Động vật có vú", "vooc-mong-trang": "Động vật có vú",
    "soc-bay-uc": "Động vật có vú", "soc-xam-phuong-dong": "Động vật có vú",
    "gorilla-dong-bang": "Động vật có vú", "khi-soc-thuong": "Động vật có vú",
    "cu-dai-bang": "Chim", "doi-ma-ca-rong": "Động vật có vú",
    "vooc-mui-hech-vang": "Động vật có vú",
}
for slug, group in expected_groups.items():
    item = by_slug.get(slug)
    if not item or item["facts"][0]["value"] != group:
        failures.append(f"taxonomy regression: {slug}")

scenes = json.loads((RESOURCE / "hidden-scenes-v87.json").read_text(encoding="utf-8"))["scenes"]
scene_hashes = set()
for scene in scenes:
    path = ROOT / scene["image"].lstrip("/")
    with Image.open(path) as im:
        if im.width / im.height < 1.5 or ("A" in im.getbands() and im.getchannel("A").getextrema() != (255, 255)):
            failures.append(f"hidden scene is not opaque/full-frame: {path.name}")
    scene_hashes.add(hashlib.sha256(path.read_bytes()).hexdigest())
if len(scenes) != 30 or len(scene_hashes) != 30:
    failures.append("hidden scenes count or uniqueness")

js = (ROOT / "static/js/app-v87.js").read_text(encoding="utf-8")
if js.count("damage(") != 1 or "r.y-r.r>540)r.dead=true" not in js:
    failures.append("meteor damage boundary")
if ".musicGain.gain.value=.032" not in js or ".sfxGain.gain.value=.18" not in js:
    failures.append("audio mix")
for cue in ("correct", "wrong", "found", "shot", "meteor", "damage"):
    if f'effect("{cue}")' not in js:
        failures.append(f"missing audio cue: {cue}")

print(json.dumps({
    "failures": failures,
    "topicCounts": counts,
    "hiddenScenes": len(scenes),
    "uniqueHiddenScenes": len(scene_hashes),
}, ensure_ascii=False, indent=2))
raise SystemExit(bool(failures))
