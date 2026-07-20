# Chalet Fortuna — Website

Modern trilingual (EN/FR/DE) website for Chalet Fortuna, Zermatt, with a reservation calendar synced from Airbnb & VRBO.

## Files

- `index.html` — the whole site (design, 3 languages, gallery, calendar)
- `images/` — optimized photos (from the old site, 27 MB → 3 MB)
- `availability.json` — booked dates shown in the calendar (currently sample data)
- `scripts/sync_ical.py` — fetches Airbnb/VRBO iCal feeds and rewrites `availability.json`
- `.github/workflows/sync-calendar.yml` — runs the script daily and commits the result

## Publish on GitHub Pages

1. In the `ChaletFortuna/Fortuna` repo, delete the old files and upload everything in this folder (keep the folder structure, including `.github/`).
2. Go to **Settings → Pages → Source: Deploy from a branch → main → / (root)** → Save.
3. Your site will be live at `https://chaletfortuna.github.io/Fortuna/`.

## Calendar sync (already configured)

The Airbnb, VRBO and Booking.com iCal feeds are already set in `scripts/sync_ical.py`. After uploading to GitHub, go to the **Actions** tab → "Sync reservation calendar" → **Run workflow** once. It then runs automatically every day at 05:00 UTC and updates `availability.json`. You can also edit `availability.json` by hand at any time.
