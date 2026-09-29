"""
Clean malaysia_phishing_dataset_features.csv and recompute its features.

The generated data is good but carries four defects, three of them inherited
unchanged from the first dataset:

  1. Brand / domain mismatch on LEGITIMATE rows. The generator paired a template
     with a random domain from its "real domain" pool instead of the domain
     belonging to the brand named in the mail, producing rows like a Maybank2u
     e-statement that links to netflix.com. In reality that mismatch IS the
     phishing tell, so those rows teach the model backwards. The domain is
     repaired rather than the label flipped, because the rows were clearly
     intended as legitimate.

  2. The same bug in the appointment template, where the sending agency does not
     match the place named in the mail (moh.gov.my sending a JPN appointment).

  3. Truncated month names ("for ov 2026", "for ay 2026") from a slicing bug.

  4. Order numbers in the subject that do not match the body.

It then recomputes every feature with features.py, so the CSV and the live API
agree by construction, and drops the columns that cannot be trained on:
sender_is_official (0.999 accurate alone - it is the label), url_count and
link_has_at (constant on all 1060 rows).

Usage:  python clean_features.py
"""

import csv
import re
from collections import Counter

from features import FEATURE_ORDER, extract_features, host_of

SRC = "malaysia_phishing_dataset_features.csv"
DST = "malaysia_phishing_dataset_final.csv"

# Brand as written in the mail -> the domain that brand actually owns.
# Longest / most specific first: "CelcomDigi" must be tested before "Celcom",
# "Shopee Express" before "Shopee", "Public Bank PBe" before "Bank".
BRAND_DOMAIN = [
    ("Public Bank PBe",    "pbebank.com"),
    ("Bank Muamalat",      "muamalat.com.my"),
    ("Bank Rakyat",        "bankrakyat.com.my"),
    ("Bank Islam",         "bankislam.com"),
    ("Alliance Bank",      "alliancebank.com.my"),
    ("Affin Bank",         "affinbank.com.my"),
    ("HLB Connect",        "hlb.com.my"),
    ("Hong Leong",         "hlb.com.my"),
    ("CIMB Clicks",        "cimbclicks.com.my"),
    ("Maybank2u",          "maybank2u.com.my"),
    ("RHB Now",            "rhbgroup.com"),
    ("AmBank",             "ambank.com.my"),
    ("OCBC",               "ocbc.com.my"),
    ("UOB",                "uob.com.my"),
    ("BSN",                "mybsn.com.my"),

    ("Touch 'n Go eWallet", "touchngo.com.my"),
    ("ShopeePay",          "shopee.com.my"),
    ("GrabPay",            "grab.com"),
    ("BigPay",             "bigpayme.com"),
    ("Boost",              "myboost.com.my"),
    ("Setel",              "setel.com"),

    ("Shopee Express",     "shopee.com.my"),
    ("TikTok Shop",        "tiktok.com"),
    ("Shopee",             "shopee.com.my"),
    ("Lazada",             "lazada.com.my"),
    ("Zalora",             "zalora.com.my"),
    ("Carousell",          "carousell.com.my"),
    ("PGMall",             "pgmall.my"),
    ("Temu",               "temu.com"),

    ("CelcomDigi",         "celcomdigi.com"),
    ("U Mobile",           "u.com.my"),
    ("TM Unifi",           "unifi.com.my"),
    ("Unifi",              "unifi.com.my"),
    ("Celcom",             "celcom.com.my"),
    ("Maxis",              "maxis.com.my"),
    ("Digi",               "digi.com.my"),
    ("YES",                "yes.my"),

    ("Tenaga Nasional",    "tnb.com.my"),
    ("TNB",                "tnb.com.my"),
    ("Gas Malaysia",       "gasmalaysia.com"),
    ("Air Selangor",       "airselangor.com"),
    ("Syabas",             "airselangor.com"),
    ("Indah Water",        "iwk.com.my"),

    ("J&T Express",        "jtexpress.my"),
    ("Flash Express",      "flashexpress.my"),
    ("City-Link",          "citylinkexpress.com"),
    ("Ninja Van",          "ninjavan.co"),
    ("Pos Laju",           "pos.com.my"),
    ("GDex",               "gdexpress.com"),
    ("DHL",                "dhl.com"),

    ("Disney+ Hotstar",    "hotstar.com"),
    ("YouTube Premium",    "youtube.com"),
    ("Netflix",            "netflix.com"),
    ("Spotify",            "spotify.com"),
    ("iQIYI",              "iq.com"),
    ("Astro",              "astro.com.my"),
    ("Viu",                "viu.com"),
    ("Apple",              "apple.com"),

    ("Malaysia Airlines",  "malaysiaairlines.com"),
    ("Batik Air",          "batikair.com"),
    ("AirAsia",            "airasia.com"),
    ("Booking.com",        "booking.com"),
    ("Agoda",              "agoda.com"),

    ("German-Malaysian",   "portal.gmi.edu.my"),
    ("KWSP",               "kwsp.gov.my"),
    ("PERKESO",            "perkeso.gov.my"),
    ("PTPTN",              "ptptn.gov.my"),
    ("LHDN",               "hasil.gov.my"),
    ("JPJ",                "jpj.gov.my"),

    # appointment template: the agency named in the mail owns the sender
    ("Imigresen Malaysia", "imi.gov.my"),
    ("Hospital Serdang",   "moh.gov.my"),
    ("Klinik Kesihatan",   "moh.gov.my"),
    ("Pejabat Pos",        "pos.com.my"),
    ("JPN",                "jpn.gov.my"),
]

MONTH_FIX = {"for ov ": "for Nov ", "for ay ": "for May "}

DROP_COLS = {"sender_is_official", "url_count", "link_has_at"}


def claimed_brand(row):
    blob = (row["subject"] + " " + row["body"]).lower()
    for brand, domain in BRAND_DOMAIN:
        if brand.lower() in blob:
            return brand, domain
    return None, None


def main():
    with open(SRC, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    print(f"loaded {len(rows)} rows from {SRC}")
    print("  ", dict(Counter(r["label_text"] for r in rows)))

    repaired = months = orders = 0
    brands_hit = Counter()

    for row in rows:
        # --- 3. truncated months ---
        for bad, good in MONTH_FIX.items():
            if bad in row["subject"]:
                row["subject"] = row["subject"].replace(bad, good)
                months += 1

        # --- 4. order number in subject vs body ---
        m = re.search(r"Order #(\w+)", row["subject"])
        if m:
            want = m.group(1)
            new_body, n = re.subn(r"Order #\w+", f"Order #{want}", row["body"])
            if n and new_body != row["body"]:
                row["body"] = new_body
                orders += 1

        # --- 1 & 2. brand/domain repair, LEGITIMATE rows only ---
        if row["label"] != "0":
            continue
        brand, correct = claimed_brand(row)
        if correct is None:
            continue
        current = host_of(row["urls"].split(",")[0])
        if current == correct:
            continue
        # rewrite the wrong domain wherever it appears
        row["sender"] = row["sender"].replace(current, correct)
        row["body"] = row["body"].replace(current, correct)
        row["urls"] = correct
        repaired += 1
        brands_hit[brand] += 1

    # --- drop exact duplicates ---
    seen, deduped = set(), []
    for r in rows:
        key = (r["subject"], r["body"])
        if key in seen:
            continue
        seen.add(key)
        deduped.append(r)
    dropped = len(rows) - len(deduped)

    # --- recompute every feature with features.py ---
    base_cols = ["source_dataset", "sender", "receiver", "date", "subject",
                 "body", "urls"]
    out_cols = base_cols + FEATURE_ORDER + ["label", "label_text"]

    out = []
    for r in deduped:
        # feed subject and body the way the API will see them: one blob whose
        # first line is the subject
        feats = extract_features(r["subject"] + "\n" + r["body"], r["sender"])
        rec = {c: r[c] for c in base_cols}
        for k in FEATURE_ORDER:
            v = feats[k]
            rec[k] = int(v) if float(v).is_integer() else v
        rec["label"] = r["label"]
        rec["label_text"] = r["label_text"]
        out.append(rec)

    with open(DST, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=out_cols)
        w.writeheader()
        w.writerows(out)

    print(f"\n  repaired brand/domain mismatch : {repaired} rows")
    for b, n in brands_hit.most_common(8):
        print(f"      {b:22} {n}")
    print(f"  fixed truncated months         : {months} rows")
    print(f"  fixed order-number mismatch    : {orders} rows")
    print(f"  dropped exact duplicates       : {dropped} rows")
    print(f"  dropped leaky/dead columns     : {sorted(DROP_COLS)}")
    print(f"\nwrote {len(out)} rows x {len(out_cols)} cols to {DST}")
    print("  ", dict(Counter(r["label_text"] for r in out)))


if __name__ == "__main__":
    main()
