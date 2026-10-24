from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
template = (ROOT / "templates/index.html").read_text(encoding="utf-8")
script = (ROOT / "static/js/app-v89.js").read_text(encoding="utf-8")
styles = (ROOT / "static/css/app-v89.css").read_text(encoding="utf-8")
failures: list[str] = []


def require(source: str, tokens: tuple[str, ...], label: str) -> None:
    for token in tokens:
        if token not in source:
            failures.append(f"{label}: missing {token}")


require(template, (
    "app-v89.css", "app-v89.js", "THƯ VIỆN KHÁM PHÁ",
    "detailDescriptionVi", "detailDescriptionEn", "speakDescriptionVi",
    "speakDescriptionEn", "speakVi", "speakEn", "stopSpeech",
), "template")
require(script, (
    "itemSpeechText", "speakItem", 'lang==="en"?"en-US":"vi-VN"',
    "library-card-open", "card-speak vi", "card-speak en",
    'data-lang="vi"', 'data-lang="en"', "speechSynthesis.cancel()",
    "FACT_ICONS", "factIcon(f)",
), "javascript")
require(styles, (
    "v8.9", ".joy-strip", ".library-hero", ".library-card-audio",
    ".language-panel", ".fact-audio", ":focus-visible",
    "@media(max-width:620px)",
), "css")

if "app-v87.js" in template or "app-v87.css" in template:
    failures.append("template: still references v87 assets")
if 'id="detailDescription"' in template:
    failures.append("template: obsolete monolingual description remains")
if "<button class=\"library-card\"" in script:
    failures.append("javascript: obsolete nested-button library card remains")
if script.count("SpeechSynthesisUtterance") != 1:
    failures.append("javascript: unexpected TTS implementation count")

print("UI v8.9 audit:", "PASS" if not failures else "FAIL")
for failure in failures:
    print("-", failure)
raise SystemExit(bool(failures))
