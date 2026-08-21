"""Forum/RSS symptom search — stdlib only (urllib + ElementTree).

Feeds are user-configurable; results are cached locally so repeat searches
work offline. Anything fetched is public forum content; nothing is uploaded.
"""

import json
import time
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

from . import paths

CACHE = paths.backups_dir() / "feeds_cache.json"
DEFAULT_FEEDS = [
    # Add your preferred forum RSS feeds here. Examples:
    # "https://www.fordownersclub.com/forums/forum/123-kuga/rss/",
    # "https://www.kugaownersclub.co.uk/forums/-/index.rss",
]
UA = {"User-Agent": "ford-tdci-recovery/0.2 (+open source diagnostics)"}


def fetch_feed(url, timeout=15):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        root = ET.fromstring(r.read())
    items = []
    for it in root.iter("item"):
        items.append({
            "title": (it.findtext("title") or "").strip(),
            "link": (it.findtext("link") or "").strip(),
            "summary": (it.findtext("description") or "").strip()[:400],
        })
    # Atom fallback
    if not items:
        ns = {"a": "http://www.w3.org/2005/Atom"}
        for it in root.iter("{http://www.w3.org/2005/Atom}entry"):
            link = it.find("a:link", ns)
            items.append({
                "title": (it.findtext("a:title", "", ns) or "").strip(),
                "link": link.get("href", "") if link is not None else "",
                "summary": (it.findtext("a:summary", "", ns) or "").strip()[:400],
            })
    return items


def search(feeds, keywords, cache_path=CACHE):
    """Return matching items across feeds, with offline cache fallback."""
    cache = {}
    if cache_path.exists():
        try:
            cache = json.loads(cache_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            cache = {}
    kw = [k.lower() for k in keywords]
    results, errors = [], []
    for url in feeds:
        try:
            items = fetch_feed(url)
            cache[url] = {"fetched": time.time(), "items": items}
        except Exception as e:
            errors.append(f"{url}: {e}")
            items = cache.get(url, {}).get("items", [])
        for it in items:
            hay = (it["title"] + " " + it["summary"]).lower()
            if all(k in hay for k in kw):
                results.append(it)
    cache_path.parent.mkdir(exist_ok=True)
    cache_path.write_text(json.dumps(cache, indent=1), encoding="utf-8")
    return results, errors
