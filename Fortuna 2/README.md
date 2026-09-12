# Chalet Fortuna — Website

Modern trilingual (EN/FR/DE) website for Chalet Fortuna, Zermatt, with a reservation calendar synced from Airbnb & VRBO.

## Files

- `index.html` — the whole public site (design, 3 languages, gallery, calendar)
- `guest.html` — the guest area: login + the welcome guide
- `images/` — optimized photos (from the old site, 27 MB → 3 MB)
- `images/guide/` — photos used in the welcome guide
- `guide/` — the **encrypted** welcome guide and guest logins (generated, safe to publish)
- `guide-src/` — the readable guide and the guest list (**git-ignored — never commit**)
- `availability.json` — booked dates shown in the calendar
- `scripts/sync_ical.py` — fetches Airbnb/VRBO iCal feeds and rewrites `availability.json`
- `scripts/build_guide.py` — encrypts the welcome guide and the guest logins
- `.github/workflows/sync-calendar.yml` — runs the calendar script daily and commits the result

## Guest area (welcome pack behind a login)

Guests open `guest.html` and sign in with **their booking e-mail address** and **their
reservation number**. The guide itself is never served in readable form: it is encrypted
with AES-256-GCM, and each guest's e-mail + reservation number derives (PBKDF2, 300 000
iterations) the key that unwraps the decryption key. A visitor without a valid pair only
ever downloads ciphertext.

### Add a guest

```bash
pip install cryptography                       # once
python3 scripts/build_guide.py --add guest@example.com HMABC12345 "Smith family"
git add guide && git commit -m "Add guest" && git push
```

The guest can sign in a few seconds after the push (GitHub Pages rebuild). To remove a
guest, delete their line from `guide-src/guests.csv` and run `python3 scripts/build_guide.py`.

### Edit the guide

Edit `guide-src/content.html` (each `<section data-title="…">` becomes a chapter in the
sidebar), then run `python3 scripts/build_guide.py` and commit `guide/`.

### Important

`guide-src/` holds the readable guide, the guest list and the content key. It is listed
in `.gitignore` so it is **never** pushed to GitHub — keep a copy somewhere safe (it is
also attached to the Claude project). If you lose `guide-src/content.key`, just rebuild:
a new key is generated and all guest entries are rewritten.

A dummy login is included for testing: `oesnou@gmail.com` / `Fortuna1`.

## Publish on GitHub Pages

1. In the `ChaletFortuna/Fortuna` repo, delete the old files and upload everything in this folder (keep the folder structure, including `.github/`).
2. Go to **Settings → Pages → Source: Deploy from a branch → main → / (root)** → Save.
3. Your site will be live at `https://chaletfortuna.github.io/Fortuna/`.

## Calendar sync (already configured)

The Airbnb, VRBO and Booking.com iCal feeds are already set in `scripts/sync_ical.py`. After uploading to GitHub, go to the **Actions** tab → "Sync reservation calendar" → **Run workflow** once. It then runs automatically every day at 05:00 UTC and updates `availability.json`. You can also edit `availability.json` by hand at any time.
