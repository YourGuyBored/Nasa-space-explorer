"""My little window into NASA's photo archive.

Quick rule I set for myself: the browser never talks to NASA directly.
Every API call goes through this file, so the frontend stays dumb and
all the messy JSON wrangling lives in one place.

To run it:
    pip install -r requirements.txt
    python app.py
then open http://127.0.0.1:5002 and go look at nebulas.
"""

import requests
from flask import Flask, jsonify, render_template, request

app = Flask(__name__)

# ---------------------------------------------------------------------------
# talking to NASA (good news: this API doesn't need a key at all)
# ---------------------------------------------------------------------------
NASA_SEARCH = "https://images-api.nasa.gov/search"
REQUEST_TIMEOUT = 15

DEFAULT_QUERY = "Nebula"
QUICK_TAGS = ["Mars", "JWST", "Hubble", "Apollo", "Earth"]

# NASA will happily hand you hundreds of results. 24 is plenty —
# page stays snappy and the grid doesn't turn into an endless scroll.
PER_PAGE = 24

# dumb little dicts so we don't nag NASA twice for the same search.
_search_cache = {}
_asset_cache = {}


# ---------------------------------------------------------------------------
# little helpers
# ---------------------------------------------------------------------------
def parse_item(item):
    """Dig one card's worth of fields out of NASA's nested JSON.

    Their shape is collection -> items -> data[0] / links[0], and honestly
    any level of that can just... not be there. So everything gets a
    fallback, and if there's no usable image at all we return None and
    the caller skips it quietly.
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
    """Ask NASA for pictures, get back a tidy list of cards. That's it."""
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
    """Find the biggest file NASA has for one image.

    Every item has a collection.json manifest listing all its files, from
    tiny thumbs up to the original. We grab the ~orig if it's there.
    Cached forever — these manifests basically never change.
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
    """Homepage. Python renders the first batch of cards itself so there's
    something on screen even before any JS runs. After that the frontend
    just calls /api/search for fresh ones."""
    query = request.args.get("q", DEFAULT_QUERY)
    try:
        query, cards = search_nasa(query)
        error = None
    except requests.RequestException as exc:
        cards, error = [], f"NASA did not answer: {exc}"
    return render_template("index.html", query=query, cards=cards,
                           tags=QUICK_TAGS, error=error)


# ---------------------------------------------------------------------------
# my own little API. the JS in the template is only allowed to call these —
# it never talks to NASA itself, that's the whole point.
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
    """Hand the lightbox the full-size file URL for one NASA id."""
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


# ---------------------------------------------------------------------------
if __name__ == "__main__":
    print()
    print("  NASA Deep Space & Earth Image Explorer")
    print("  ->  http://127.0.0.1:5002")
    print("  Ctrl+C to stop.")
    print()
    app.run(host="127.0.0.1", port=5002, debug=False)
