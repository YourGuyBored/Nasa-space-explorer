"""My little window into NASA's photo archive.

I got tired of digging through NASA's site, so I built this — type
something like "Eagle Nebula" and it pulls real photos from their
open library. Nothing fancy, just Flask + some vanilla JS.

One rule I stuck to: the browser never talks to NASA directly.
Everything goes through this file so the frontend stays dumb and
all the weird JSON stuff lives in one spot where I can find it.

To run it:
    pip install -r requirements.txt
    cp .env.example .env  (then drop your api.nasa.gov key in there)
    python app.py
then open http://127.0.0.1:5002 and go look at nebulas.
"""

import os

import requests
from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request

load_dotenv()

app = Flask(__name__)

# ---------------------------------------------------------------------------
# NASA stuff — turns out there are two of them and they work different
# ---------------------------------------------------------------------------
# images-api.nasa.gov (the image search) doesn't care about keys at all.
# api.nasa.gov (APOD and friends) does, so I keep mine in .env and
# never hardcode it. learned that lesson already, not doing it again.
NASA_API_KEY = os.getenv("NASA_API_KEY", "DEMO_KEY")
NASA_SEARCH = "https://images-api.nasa.gov/search"
NASA_APOD = "https://api.nasa.gov/planetary/apod"
REQUEST_TIMEOUT = 15

DEFAULT_QUERY = "Nebula"
QUICK_TAGS = ["Mars", "JWST", "Hubble", "Apollo", "Earth"]

# NASA will happily dump hundreds of results on you if you let it. I tried
# that once, page took forever. 24 feels about right — snappy, and the
# grid doesn't turn into an endless scroll.
PER_PAGE = 24

# just a couple dumb dicts so I stop asking NASA for the same thing twice.
# nothing clever, they reset every time I restart the server and that's fine.
_search_cache = {}
_asset_cache = {}


# ---------------------------------------------------------------------------
# little helpers
# ---------------------------------------------------------------------------
def parse_item(item):
    """Pull one card's worth of stuff out of NASA's nested JSON.

    Their shape is collection -> items -> data[0] / links[0], and honestly
    half the time some level is just... missing. So I fallback everything,
    and if there's no usable image I bail with None and the caller
    quietly skips it. No point crashing over one bad record.
    """
    if not isinstance(item, dict):
        return None
    data = item.get("data") or []
    info = data[0] if data else {}
    links = item.get("links") or []
    thumb = links[0].get("href") if links else None
    if not thumb:
        return None
    return {
        "title": info.get("title") or "Untitled",
        "nasa_id": info.get("nasa_id") or "",
        "date_created": (info.get("date_created") or "")[:10],  # just the YYYY-MM-DD part
        "description": info.get("description") or "No description on file.",
        "thumbnail": thumb,
    }


def search_nasa(query):
    """Ask NASA for pictures, get back a tidy little list of cards. That's all this does."""
    query = (query or "").strip() or DEFAULT_QUERY
    if query in _search_cache:
        return query, _search_cache[query]

    response = requests.get(
        NASA_SEARCH,
        params={"q": query, "media_type": "image", "page_size": PER_PAGE},
        timeout=REQUEST_TIMEOUT,
    )
    response.raise_for_status()
    raw_items = response.json().get("collection", {}).get("items", [])

    cards = []
    for raw in raw_items:
        card = parse_item(raw)
        if card:
            cards.append(card)

    _search_cache[query] = cards
    return query, cards


def full_asset_url(nasa_id):
    """Track down the biggest file NASA has for one image.

    Each item has this collection.json manifest with all its files in it,
    tiny thumbs up to the original. I grab the ~orig one if it's there.
    I cache these forever — that manifest basically never changes.
    """
    if nasa_id in _asset_cache:
        return _asset_cache[nasa_id]

    url = f"https://images-assets.nasa.gov/image/{nasa_id}/collection.json"
    response = requests.get(url, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    # heads up: the manifest is just a flat list of URL strings. The old
    # docs show some nested dict thing instead, so I accept both — learned
    # that one the hard way (it 500'd on the very first real image).
    payload = response.json()
    if isinstance(payload, dict):
        raw = payload.get("collection", {}).get("items", [])
        files = [f.get("href", "") if isinstance(f, dict) else str(f)
                 for f in raw]
    else:
        files = [str(f) for f in payload]

    jpgs = [f for f in files if f.lower().endswith((".jpg", ".jpeg"))]
    best = None
    for href in jpgs:
        if "~orig" in href:
            best = href
            break
    if best is None:
        # no original on file. NASA names things ~thumb < ~small < ~medium
        # < ~large < ~orig, so the last one alphabetically is the best
        # we've got.
        best = sorted(jpgs)[-1] if jpgs else None

    _asset_cache[nasa_id] = best
    return best


# ---------------------------------------------------------------------------
# the actual pages
# ---------------------------------------------------------------------------
@app.route("/")
def index():
    """Homepage. I render the first batch in Python so there's already
    pictures on screen before any JS even runs. After that the page
    just hits /api/search for fresh ones."""
    query = request.args.get("q", DEFAULT_QUERY)
    try:
        query, cards = search_nasa(query)
        error = None
    except requests.RequestException as exc:
        cards, error = [], f"NASA did not answer: {exc}"
    return render_template("index.html", query=query, cards=cards,
                           tags=QUICK_TAGS, error=error)


# ---------------------------------------------------------------------------
# my own tiny API. the JS is only allowed to call these — it never talks
# to NASA itself. that was the whole point, keeps me sane.
# ---------------------------------------------------------------------------
@app.route("/api/search")
def api_search():
    query = request.args.get("q", DEFAULT_QUERY)
    try:
        query, cards = search_nasa(query)
    except requests.RequestException as exc:
        return jsonify({"ok": False,
                        "error": f"NASA did not answer: {exc}"}), 502
    return jsonify({"ok": True, "query": query, "count": len(cards),
                    "cards": cards})


@app.route("/api/asset")
def api_asset():
    """Hand the lightbox the full-size file for one NASA id. Thumbnail's
    already on screen by then, this just swaps in the good version."""
    nasa_id = (request.args.get("nasa_id") or "").strip()
    if not nasa_id:
        return jsonify({"ok": False, "error": "Missing nasa_id."}), 400
    try:
        url = full_asset_url(nasa_id)
    except requests.RequestException as exc:
        return jsonify({"ok": False,
                        "error": f"NASA did not answer: {exc}"}), 502
    if not url:
        return jsonify({"ok": False,
                        "error": "No full-size file on record."}), 404
    return jsonify({"ok": True, "nasa_id": nasa_id, "url": url})


@app.route("/api/apod")
def api_apod():
    """Today's astronomy picture. This one's from api.nasa.gov so it needs
    my key from .env — without it you just get rate-limited to death."""
    params = {"api_key": NASA_API_KEY}
    date = (request.args.get("date") or "").strip()
    if date:
        params["date"] = date
    try:
        response = requests.get(NASA_APOD, params=params,
                                timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        return jsonify({"ok": True, **response.json()})
    except requests.RequestException as exc:
        return jsonify({"ok": False,
                        "error": f"NASA did not answer: {exc}"}), 502


# ---------------------------------------------------------------------------
if __name__ == "__main__":
    print()
    print("  NASA Deep Space & Earth Image Explorer")
    print("  ->  http://127.0.0.1:5002")
    print("  Ctrl+C to stop.")
    print()
    app.run(host="127.0.0.1", port=5002, debug=False)
