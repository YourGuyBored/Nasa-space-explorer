# NASA Deep Space & Earth Image Explorer

I wanted a simple way to dig through NASA's photo library — nebulas,
rovers, telescopes, old missions — without fighting their site. So this
is a clean white gallery thing, kind of like a lab bench.

It's just Python (Flask) on the back and plain HTML/CSS/JS on the front.
The browser never talks to NASA itself, everything goes through the server.
Made my life way easier to debug that way.

## Run it (fresh clone to running server)

You only need Python 3. That's it. No Node, no build step, nothing weird.

1. Grab the code and go into it:
```bash
git clone <your-repo-url>
cd nasa_space_explorer
```

2. I use a virtual environment so I don't mess up my system Python.
Honestly on Arch / Ubuntu you'll probably need this, otherwise pip
yells about "externally-managed-environment":
```bash
python3 -m venv venv
source venv/bin/activate
```
You'll know it worked because your prompt gets a little `(venv)` in front.

3. Install the three things this needs:
```bash
pip install -r requirements.txt
```
That's just `flask` (the server), `requests` (talks to NASA), and
`python-dotenv` (loads your key from `.env`). Takes like 10 seconds.

4. Set up your key file (optional — demo key works out of the box):
```bash
cp .env.example .env
```
Then open `.env` and paste your api.nasa.gov key in there. Heads up —
the image search works fine without any key, this is only for the
picture-of-the-day route (`/api/apod`). Skip it, or leave the
`your_key_here` placeholder in place, and that route just uses NASA's
public `DEMO_KEY` instead. Rate-limited fast, but the app still runs,
nothing crashes over a missing key.

Forgot the `cp` step? Don't worry about it — the server makes `.env`
from `.env.example` by itself on first run.

5. Start it:
```bash
python app.py
```
(or `python3 app.py` if `python` doesn't work on your machine.)

Then open http://127.0.0.1:5002 in your browser. Done. Ctrl+C when
you wanna stop it.

Stuck? Two things bite everyone:
- `ModuleNotFoundError: No module named 'dotenv'` — you forgot step 3,
just run the pip install again inside your venv.
- pip complaining about externally-managed-environment — that's step 2,
use the venv, or if you really don't want one: `pip install --break-system-packages -r requirements.txt`.

## About the API key

Fun quirk: the image search doesn't need a key at all. But the astronomy-picture-of-the-day route (`/api/apod`) does, so it reads `NASA_API_KEY` out of `.env`. That file's gitignored, so don't commit the real key — I left an example one to copy from. Missing, blank, or still sitting on `your_key_here`? Falls back to `DEMO_KEY` on its own, so APOD keeps answering (within NASA's demo rate limits).

## Try it

- Type something like `Eagle Nebula`, or just smash one of the quick tags: Mars, JWST, Hubble, Apollo, Earth
- Click any card and you'll get the big version + whatever NASA wrote about it
- ...and yeah, there's one secret search word buried in there. You'll know it when you type it.
