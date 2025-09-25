#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List
from urllib import error, request

from topics import pick_for_today, resolve_topics

CATEGORIES = ["Minimalismus", "Selbstentwicklung", "Frugalismus", "Investieren"]

REPO_ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = REPO_ROOT / "data" / "schema.json"
FALLBACK_PATH = REPO_ROOT / "data" / "fallback.json"
ITEM_PATH = REPO_ROOT / "item.json"

CHAT_COMPLETIONS_URL = "https://api.openai.com/v1/chat/completions"


def load_schema() -> Dict[str, Any]:
    with SCHEMA_PATH.open("r", encoding="utf-8") as schema_file:
        return json.load(schema_file)


def load_fallback_items() -> List[Dict[str, Any]]:
    with FALLBACK_PATH.open("r", encoding="utf-8") as fallback_file:
        data = json.load(fallback_file)
    if not isinstance(data, list) or not data:
        raise ValueError("Fallback-Datei enthält keine Artikel.")
    return data


def validate_item(item: Dict[str, Any], schema: Dict[str, Any]) -> None:
    required = schema.get("required", [])
    properties: Dict[str, Any] = schema.get("properties", {})
    for field in required:
        if field not in item:
            raise ValueError(f"Antwort fehlt Feld '{field}'.")
    for key, spec in properties.items():
        if key not in item:
            continue
        value = item[key]
        expected_type = spec.get("type")
        if expected_type == "string" and not isinstance(value, str):
            raise ValueError(f"Feld '{key}' muss Zeichenkette sein.")
        if isinstance(value, str):
            min_len = spec.get("minLength")
            max_len = spec.get("maxLength")
            if min_len is not None and len(value) < min_len:
                raise ValueError(f"Feld '{key}' unterschreitet Mindestlänge {min_len}.")
            if max_len is not None and len(value) > max_len:
                raise ValueError(f"Feld '{key}' überschreitet Maximallänge {max_len}.")
            pattern = spec.get("pattern")
            if pattern and not re.match(pattern, value):
                raise ValueError(f"Feld '{key}' erfüllt Muster '{pattern}' nicht.")
            min_words = spec.get("minWords")
            max_words = spec.get("maxWords")
            if min_words or max_words:
                word_count = len(value.split())
                if min_words and word_count < min_words:
                    raise ValueError(f"Feld '{key}' benötigt mindestens {min_words} Wörter (aktuell {word_count}).")
                if max_words and word_count > max_words:
                    raise ValueError(f"Feld '{key}' erlaubt höchstens {max_words} Wörter (aktuell {word_count}).")
        enum_values = spec.get("enum")
        if enum_values and value not in enum_values:
            raise ValueError(f"Feld '{key}' muss einen Wert aus {enum_values} besitzen.")
    for field in item:
        if field not in properties:
            raise ValueError(f"Unerwartetes Feld '{field}' in Antwort.")


def call_openai(api_key: str, model: str, topic: str) -> Dict[str, Any]:
    system_prompt = (
        "Du schreibst inspirierende, deutschsprachige Kurzartikel. "
        "Halte dich an die geforderten Wortzahlen und bleibe seriös."
    )
    user_prompt = (
        'Erzeuge EINEN Artikel als JSON mit Feldern:\n'
        '{ "title": string, "body": string, "url": string, "category": string }.\n'
        "Sprache: Deutsch. Länge body: 150–200 Wörter.\n"
        f'Thema: "{topic}".\n'
        'Kategorie: eine aus ["Minimalismus","Selbstentwicklung","Frugalismus","Investieren"].\n'
        'Am Ende des Textes keinen weiteren Call-to-Action; Link in "url".\n'
        "Liefere ausschließlich ein JSON-Objekt ohne Kommentartext."
    )
    payload = json.dumps(
        {
            "model": model,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }
    ).encode("utf-8")
    http_request = request.Request(
        CHAT_COMPLETIONS_URL,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )
    with request.urlopen(http_request, timeout=60) as response:
        body = response.read().decode("utf-8")
    result = json.loads(body)
    choices = result.get("choices")
    if not choices:
        raise ValueError("Antwort enthält keine Auswahl.")
    content = choices[0]["message"]["content"]
    return json.loads(content)


def select_fallback(topic: str, fallback_items: List[Dict[str, Any]]) -> Dict[str, Any]:
    if not fallback_items:
        raise ValueError("Keine Fallback-Artikel verfügbar.")
    checksum = sum(ord(char) for char in topic)
    today_index = (checksum + os.getpid()) % len(fallback_items)
    return fallback_items[today_index]


def main() -> int:
    schema = load_schema()
    fallback_items = load_fallback_items()
    topics = resolve_topics()
    todays_topic = pick_for_today(topics)
    api_key = os.getenv("OPENAI_API_KEY", "")
    model = os.getenv("MODEL", "gpt-4o-mini") or "gpt-4o-mini"

    item: Dict[str, Any]
    try:
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY fehlt.")
        item = call_openai(api_key, model, todays_topic)
        validate_item(item, schema)
    except Exception as exc:  # noqa: BLE001
        print(f"[WARN] OpenAI-Generierung fehlgeschlagen: {exc}", file=sys.stderr)
        item = select_fallback(todays_topic, fallback_items)
        try:
            validate_item(item, schema)
        except Exception as inner_exc:  # noqa: BLE001
            print(f"[ERROR] Fallback-Artikel ungültig: {inner_exc}", file=sys.stderr)
            return 1

    item["title"] = item["title"].strip()
    item["body"] = item["body"].strip()
    item["url"] = item["url"].strip()
    item["category"] = item["category"].strip()
    item["topic"] = todays_topic

    with ITEM_PATH.open("w", encoding="utf-8") as item_file:
        json.dump(item, item_file, ensure_ascii=False, indent=2)

    print(f"[INFO] Artikel für Thema '{todays_topic}' erzeugt.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
