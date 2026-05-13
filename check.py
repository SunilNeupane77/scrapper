"""
Submission checklist for Audio Bee ekantipur assessment.
"""
from __future__ import annotations

import ast
import json
import os
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REQUIRED_FILES = (
    "scraper.py",
    "output.json",
    "pyproject.toml",
    "prompts.txt",
    "recording.mp4",
)


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def main() -> None:
    errors: list[str] = []

    for name in REQUIRED_FILES:
        p = ROOT / name
        if not p.is_file():
            errors.append(f"Missing required file: {name}")

    output_path = ROOT / "output.json"
    if output_path.is_file():
        raw_json = _read_text(output_path)
        try:
            data = json.loads(raw_json)
        except json.JSONDecodeError as e:
            errors.append(f"output.json is not valid JSON: {e}")
            data = None
        else:
            ent = data.get("entertainment_news")
            if not isinstance(ent, list) or len(ent) != 5:
                errors.append("output.json: entertainment_news must be a list of exactly 5 items")
            else:
                req = {"title", "image_url", "category", "author"}
                for i, art in enumerate(ent):
                    if not isinstance(art, dict):
                        errors.append(f"Article {i} is not an object")
                        continue
                    if req - set(art.keys()):
                        errors.append(f"Article {i} missing keys {req - set(art.keys())}")
                    else:
                        u = art.get("image_url")
                        if not isinstance(u, str) or not u.startswith("http"):
                            errors.append(f"Article {i}: image_url must be absolute http(s)")
                        t = art.get("title")
                        if not t or not str(t).strip():
                            errors.append(f"Article {i}: title must be non-empty")

            cartoon = data.get("cartoon_of_the_day") if isinstance(data, dict) else None
            if not isinstance(cartoon, dict):
                errors.append("cartoon_of_the_day must be an object")
            else:
                for k in ("title", "image_url", "author"):
                    if k not in cartoon:
                        errors.append(f"cartoon_of_the_day missing key: {k}")
                ci = cartoon.get("image_url")
                if ci is not None and (not isinstance(ci, str) or not ci.startswith("http")):
                    errors.append("cartoon_of_the_day.image_url must be absolute http(s)")

            if "\\u0" in raw_json:
                errors.append("output.json appears to escape Unicode (ensure_ascii=False when saving)")

            devanagari_range = re.compile(r"[\u0900-\u097F]")
            if isinstance(data, dict):
                blob = json.dumps(data, ensure_ascii=False)
                if not devanagari_range.search(blob):
                    errors.append("Nepali/Devanagari text not detected in output.json payload")

    scraper_path = ROOT / "scraper.py"
    if scraper_path.is_file():
        src = _read_text(scraper_path)
        if "headless=False" in src:
            errors.append("scraper.py must not contain headless=False (use headed debugging separately)")
        if "headless=True" not in src:
            errors.append("scraper.py must launch Chromium with headless=True")
        if "ensure_ascii=False" not in src:
            errors.append("scraper.py must use ensure_ascii=False for JSON output")
        if "try:" not in src:
            errors.append("scraper.py should include try/except for resilience")
        if "finally:" not in src:
            errors.append("scraper.py should include a finally block (e.g. browser cleanup)")
        if "os.path" not in src:
            errors.append("scraper.py should use os.path for paths")
        if "page.pause()" in src:
            errors.append("scraper.py must not call page.pause()")
        if re.search(r"/home/|C:\\\\|D:\\\\", src):
            errors.append("scraper.py contains suspected hardcoded local path")

        try:
            tree = ast.parse(src)
        except SyntaxError as e:
            errors.append(f"scraper.py syntax error: {e}")
        else:
            tries = sum(isinstance(n, ast.Try) for n in ast.walk(tree))
            if tries == 0:
                errors.append("scraper.py: no try statements found")

    prompts_path = ROOT / "prompts.txt"
    if prompts_path.is_file():
        pt = _read_text(prompts_path)
        if not pt.strip():
            errors.append("prompts.txt is empty")
        elif len(pt.strip()) <= 50:
            errors.append("prompts.txt should contain more than 50 characters")

    if errors:
        print("Fix the following issues:")
        for e in errors:
            print(f"  - {e}")
    else:
        print("ALL CHECKS PASSED - READY TO SUBMIT")


if __name__ == "__main__":
    main()
