# NASA Deep Space & Earth Image Explorer

Search NASA's official Image and Video Library — nebulas, rovers,
telescopes, missions — in a clean white observatory-style gallery.

Python (Flask) backend, plain HTML/CSS/vanilla JS frontend. The browser
never talks to NASA directly; every API call goes through the server.

## Run it

```bash
pip install -r requirements.txt
python app.py
```

Then open http://127.0.0.1:5002

## Try it

- Type a query like `Eagle Nebula`, or hit a quick tag: Mars, JWST, Hubble, Apollo, Earth
- Click any card for the full-size photo + NASA's description
- ...there's also one secret search word. You'll know it if you type it.
