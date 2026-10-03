#!/usr/bin/env python3
"""
Build "FORTUNA DIRECT ACCESS.csv" — guest-area logins for DIRECT bookings — from the
rental contracts (Mietverträge) kept in "Fortuna Clients Direct/<Family name>/".

Runs on Olivier's computer, from the "_guest-access" folder inside "Fortuna Clients Direct":
    python3 direct_access.py            # writes FORTUNA DIRECT ACCESS.csv next to this script
                                        # and prints it between ---CSV--- markers

  login        = family name (the guest's folder name) — plus an ASCII spelling for
                 umlauts (König -> Koenig) and a hyphenated surname found in the contract
                 (Rod-Stuby) as extra logins
  password     = FORTUNA (case-insensitive on the site)
  access window = 30 days before arrival -> 1 day after departure
  only stays whose access window has not ended yet are written

Contracts are read with pdftotext (.pdf) and LibreOffice (.doc/.docx). When several contracts
describe overlapping stays for the same guest, the signed one wins, then the dated
"YYYY MM DD …" one, then the most recently modified. Contracts whose end date is not after
the start date (typos) are ignored. Archive/, loose files at the top level, Word lock files
(~$…), images and stray scans (Scan_*, doc0128*, CCE*) are skipped. Results are cached by
file modification time in cache.json.
"""
import csv, datetime, io, json, os, re, subprocess, sys, tempfile, unicodedata

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)                      # "Fortuna Clients Direct"
OUT = os.path.join(HERE, "FORTUNA DIRECT ACCESS.csv")
CACHE = os.path.join(HERE, "cache.json")
PASSWORD = "FORTUNA"
BEFORE, AFTER = 30, 1
SKIP_DIRS = {"archive", os.path.basename(HERE).lower()}
SKIP_FILE = re.compile(r"^(~\$|\.|Scan_|doc0128|CCE)", re.I)
COLS = "login,password,access_from,access_until,arrival,departure,guest,platform,bookings_row,status,source".split(",")
DATE = r"(\d{1,2})\s*\.\s*(\d{1,2})\s*\.\s*(\d{4}|\d{2})\b"


def zermatt_today():
    try:
        from zoneinfo import ZoneInfo
        return datetime.datetime.now(ZoneInfo("Europe/Zurich")).date()
    except Exception:
        return datetime.date.today()


def fold(s):
    s = unicodedata.normalize("NFD", s)
    return re.sub(r"[^a-z0-9]", "", "".join(c for c in s if not unicodedata.combining(c)).lower())


def to_date(m):
    d, mo, y = (int(x) for x in m)
    y += 2000 if y < 100 else 0
    try:
        return datetime.date(y, mo, d)
    except ValueError:
        return None


def read_text(path, tmp):
    if path.lower().endswith(".pdf"):
        r = subprocess.run(["pdftotext", "-layout", path, "-"], capture_output=True, text=True)
        return r.stdout
    subprocess.run(["soffice", "--headless", "--convert-to", "txt:Text (encoded):UTF8",
                    "--outdir", tmp, path], capture_output=True, timeout=180)
    t = os.path.join(tmp, os.path.splitext(os.path.basename(path))[0] + ".txt")
    if os.path.exists(t):
        with open(t, encoding="utf-8", errors="ignore") as f:
            return f.read()
    return ""


def parse(text):
    flat = re.sub(r"\s+", " ", text)
    m = re.search(r"Mieter \(Name[^)]*\)\s*(.*?)(?:Locataire|Mietobjekt|$)", flat)
    tenant = m.group(1).split(",")[0].strip()[:80] if m else ""
    start = re.search(r"Mietbeginn\s*:?\s*" + DATE, flat)
    end = re.search(r"Mietende\s*:?\s*" + DATE, flat)
    if start and end:
        a, b = to_date(start.groups()), to_date(end.groups())
    else:                                         # French layout: "de location : Sa 17.10.2026"
        ds = re.findall(r"de location\s*:\s*(?:[A-Za-zé]{2,3}\.?\s+)?" + DATE, flat, re.I)
        a, b = (to_date(ds[0]), to_date(ds[1])) if len(ds) >= 2 else (None, None)
    return tenant, a and a.isoformat(), b and b.isoformat()


def main():
    today = zermatt_today()
    try:
        cache = json.load(open(CACHE))
    except (OSError, ValueError):
        cache = {}
    folders = [d for d in sorted(os.listdir(ROOT))
               if os.path.isdir(os.path.join(ROOT, d)) and d.lower() not in SKIP_DIRS and not d.startswith((".", "_"))]
    tmp = tempfile.mkdtemp()
    cands, warnings, new_cache = [], [], {}
    for d in folders:
        for f in sorted(os.listdir(os.path.join(ROOT, d))):
            if SKIP_FILE.match(f) or not re.search(r"\.(pdf|docx?)$", f, re.I):
                continue
            p = os.path.join(ROOT, d, f)
            rel, mt = f"{d}/{f}", os.path.getmtime(p)
            c = cache.get(rel)
            if not c or c.get("mtime") != mt:
                try:
                    tenant, a, b = parse(read_text(p, tmp))
                except Exception as e:
                    tenant, a, b = "", None, None
                    warnings.append(f"could not read {rel}: {e}")
                c = {"mtime": mt, "tenant": tenant, "start": a, "end": b}
            new_cache[rel] = c
            if not c["start"] or not c["end"]:
                continue
            a, b = datetime.date.fromisoformat(c["start"]), datetime.date.fromisoformat(c["end"])
            if not (a < b <= a + datetime.timedelta(days=60)):
                warnings.append(f"ignored {rel}: implausible dates {a} -> {b}")
                continue
            # contract filed in the wrong guest folder? follow the tenant's name
            owner, ft = d, fold(c["tenant"])
            if ft and fold(d) not in ft:
                others = [o for o in folders if fold(o) in ft]
                if others:
                    owner = others[0]
                    warnings.append(f"{rel} is for {owner}, not {d}")
            prio = (2 if re.search(r"sign|_sig\b", f, re.I) else 0) + (1 if re.match(r"\d{4} \d{2} \d{2}", f) else 0)
            cands.append(dict(owner=owner, tenant=c["tenant"], a=a, b=b, prio=prio, mtime=mt, src=rel))
    json.dump(new_cache, open(CACHE, "w"), ensure_ascii=False, indent=0)

    # one stay per overlapping group, best contract first
    stays = []
    for c in sorted(cands, key=lambda x: (-x["prio"], -x["mtime"])):
        clash = [s for s in stays if s["owner"] == c["owner"] and c["a"] < s["b"] and s["a"] < c["b"]]
        if clash:
            if (clash[0]["a"], clash[0]["b"]) != (c["a"], c["b"]):
                warnings.append(f"{c['owner']}: {c['src']} says {c['a']}->{c['b']}, kept {clash[0]['src']} ({clash[0]['a']}->{clash[0]['b']})")
            continue
        stays.append(c)

    rows = []
    for s in sorted(stays, key=lambda x: (x["a"], x["owner"])):
        frm, until = s["a"] - datetime.timedelta(days=BEFORE), s["b"] + datetime.timedelta(days=AFTER)
        if until < today:
            continue
        owner = unicodedata.normalize("NFC", s["owner"])   # macOS folder names are often decomposed
        logins = [owner]
        ascii_ = owner.translate(str.maketrans({"ä": "ae", "ö": "oe", "ü": "ue", "Ä": "Ae", "Ö": "Oe", "Ü": "Ue"}))
        if fold(ascii_) != fold(owner):
            logins.append(ascii_)
        for w in s["tenant"].split():                 # e.g. "Rod-Stuby"
            if "-" in w and fold(s["owner"]) in fold(w) and fold(w) not in map(fold, logins):
                logins.append(w)
        for login in logins:
            rows.append(dict(login=login, password=PASSWORD, access_from=frm.isoformat(), access_until=until.isoformat(),
                             arrival=s["a"].isoformat(), departure=s["b"].isoformat(), guest=s["tenant"] or s["owner"],
                             platform="Direct", bookings_row="", status="contract", source=s["src"]))
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=COLS, lineterminator="\n")
    w.writeheader(); w.writerows(rows)
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(buf.getvalue())
    print("---CSV---"); print(buf.getvalue(), end=""); print("---END---")
    for x in warnings:
        print("note:", x, file=sys.stderr)


if __name__ == "__main__":
    main()
