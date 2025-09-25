#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from email.utils import format_datetime
from pathlib import Path
from typing import Dict, Optional
from xml.etree import ElementTree as ET

CATEGORIES = ["Minimalismus", "Selbstentwicklung", "Frugalismus", "Investieren"]
REPO_ROOT = Path(__file__).resolve().parents[1]
FEED_PATH = REPO_ROOT / "feed.xml"
ITEM_PATH = REPO_ROOT / "item.json"


def load_item() -> Dict[str, str]:
    if not ITEM_PATH.exists():
        raise FileNotFoundError("item.json wurde nicht gefunden. Bitte zuerst generate_item ausführen.")
    with ITEM_PATH.open("r", encoding="utf-8") as item_file:
        data = json.load(item_file)
    for field in ("title", "body", "url", "category"):
        if field not in data:
            raise ValueError(f"item.json fehlt Feld '{field}'.")
    if data["category"] not in CATEGORIES:
        raise ValueError(f"Ungültige Kategorie: {data['category']}")
    return data


def indent(element: ET.Element, level: int = 0) -> None:
    spacing = "\n" + "  " * level
    if len(element):
        if not element.text or not element.text.strip():
            element.text = spacing + "  "
        for child in element:
            indent(child, level + 1)
        if not element.tail or not element.tail.strip():
            element.tail = spacing
    else:
        if level and (not element.tail or not element.tail.strip()):
            element.tail = spacing


def ensure_channel(tree: ET.ElementTree, defaults: Dict[str, str]) -> ET.Element:
    root = tree.getroot()
    if root.tag != "rss":
        raise ValueError("feed.xml besitzt kein <rss>-Root.")
    channel = root.find("channel")
    if channel is None:
        channel = ET.SubElement(root, "channel")
    for tag, text in (
        ("title", defaults["title"]),
        ("link", defaults["link"]),
        ("description", defaults["description"]),
        ("language", "de-de"),
    ):
        node = channel.find(tag)
        if node is None:
            node = ET.SubElement(channel, tag)
        node.text = text
    last_build = channel.find("lastBuildDate")
    now_formatted = format_datetime(datetime.now(timezone.utc))
    if last_build is None:
        last_build = ET.SubElement(channel, "lastBuildDate")
    last_build.text = now_formatted
    return channel


def create_new_feed(defaults: Dict[str, str]) -> ET.ElementTree:
    rss = ET.Element("rss", attrib={"version": "2.0"})
    tree = ET.ElementTree(rss)
    ensure_channel(tree, defaults)
    return tree


def build_item_element(item: Dict[str, str]) -> ET.Element:
    now = datetime.now(timezone.utc)
    item_element = ET.Element("item")
    title = ET.SubElement(item_element, "title")
    title.text = item["title"]

    description = ET.SubElement(item_element, "description")
    description.text = item["body"]

    link = ET.SubElement(item_element, "link")
    link.text = item["url"]

    category = ET.SubElement(item_element, "category")
    category.text = item["category"]

    guid = ET.SubElement(item_element, "guid", attrib={"isPermaLink": "false"})
    guid.text = f"{now.timestamp():.0f}-{abs(hash(item['title']))}"

    pub_date = ET.SubElement(item_element, "pubDate")
    pub_date.text = format_datetime(now)

    return item_element


def read_feed(defaults: Dict[str, str]) -> ET.ElementTree:
    if not FEED_PATH.exists():
        return create_new_feed(defaults)
    tree = ET.parse(FEED_PATH)
    return tree


def get_feed_defaults() -> Dict[str, str]:
    feed_title = os.getenv("FEED_TITLE", "").strip() or "Personal Development Feed (DE)"
    feed_link_env = os.getenv("FEED_LINK", "").strip()
    feed_description = os.getenv("FEED_DESC", "").strip() or "Tägliche Nuggets mit Link zum Weiterlesen."

    if feed_link_env:
        feed_link = feed_link_env
    else:
        repository = os.getenv("GITHUB_REPOSITORY", "")
        owner, _, repo = repository.partition("/")
        if owner and repo:
            feed_link = f"https://{owner}.github.io/{repo}/feed.xml"
        else:
            feed_link = "https://example.com/feed.xml"
    return {
        "title": feed_title,
        "link": feed_link,
        "description": feed_description,
    }


def parse_max_items() -> int:
    raw_value = os.getenv("MAX_ITEMS", "60")
    try:
        max_items = int(raw_value)
    except ValueError as exc:
        raise ValueError("MAX_ITEMS muss eine ganze Zahl sein.") from exc
    if max_items <= 0:
        raise ValueError("MAX_ITEMS muss größer als 0 sein.")
    return max_items


def main() -> int:
    try:
        item = load_item()
    except Exception as exc:  # noqa: BLE001
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 1

    defaults = get_feed_defaults()
    try:
        feed_tree = read_feed(defaults)
    except Exception as exc:  # noqa: BLE001
        print(f"[ERROR] feed.xml konnte nicht gelesen werden: {exc}", file=sys.stderr)
        return 1

    channel = ensure_channel(feed_tree, defaults)
    new_item = build_item_element(item)
    channel.insert(0, new_item)

    try:
        max_items = parse_max_items()
    except ValueError as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 1

    existing_items = channel.findall("item")
    for extra in existing_items[max_items:]:
        channel.remove(extra)

    indent(feed_tree.getroot())
    feed_tree.write(FEED_PATH, encoding="utf-8", xml_declaration=True)
    print(f"[INFO] feed.xml aktualisiert (max {max_items} Einträge).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
