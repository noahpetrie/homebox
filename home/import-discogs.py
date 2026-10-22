# Import a Discogs record collection into Homebox as "Record" items, with covers.
#
# usage: python3 home/import-discogs.py <homebox url> <homebox token> <location name> [--dry-run]
#
# The Discogs personal access token is read from the macOS Keychain
# (security add-generic-password -a "$USER" -s discogs-token -w <token>).
# Safe to re-run after adding records on Discogs: releases already imported (matched by the
# "Discogs" field) are skipped. Creates the Record type and its default template if missing.
import io, json, os, re, subprocess, sys, time, urllib.request, uuid

BASE, TOK, LOCATION = sys.argv[1].rstrip("/") + "/api/v1", sys.argv[2], sys.argv[3]
DRY = "--dry-run" in sys.argv
DISCOGS_USER = "noahmadiba"
# Collection entries Discogs lists as digital files that are really vinyl: the vinyl release to use
# instead (the most common pressing; the colour variant may differ, so the item says to check).
VINYL_INSTEAD = {28511356: 29084410,   # Omar Apollo, Live For Me
                 33128820: 25979578}   # RAYE, My 21st Century Blues
RECORD_FIELDS = ["Artist", "Label", "Catalog #", "Released", "Original release", "Format", "Genre",
                 "Barcode", "Media condition", "Sleeve condition", "Discogs"]

HB = {"Authorization": "Bearer " + TOK}
DTOK = subprocess.run(["security", "find-generic-password", "-a", os.environ["USER"], "-s", "discogs-token", "-w"],
                      capture_output=True, text=True, check=True).stdout.strip()
DH = {"Authorization": f"Discogs token={DTOK}", "User-Agent": "HomeboxImport/1.0 +https://homebox.madiba.ca"}


def hb(method, path, body=None):
    data = json.dumps(body).encode() if body is not None else None
    r = urllib.request.urlopen(urllib.request.Request(BASE + path, method=method, data=data,
                                                      headers={**HB, "Content-Type": "application/json"}))
    t = r.read()
    return json.loads(t) if t else None


_last = [0.0]
def discogs(url, raw=False):
    # authenticated limit is 60 requests a minute
    time.sleep(max(0, 1.05 - (time.time() - _last[0])))
    _last[0] = time.time()
    r = urllib.request.urlopen(urllib.request.Request(url, headers=DH), timeout=60)
    return r.read() if raw else json.loads(r.read())


def upload_photo(entity_id, jpg, name):
    boundary = uuid.uuid4().hex
    body = io.BytesIO()
    for k, v in (("name", name), ("type", "photo"), ("primary", "true")):
        body.write(f'--{boundary}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode())
    body.write(f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="{name}"\r\n'
               f'Content-Type: image/jpeg\r\n\r\n'.encode() + jpg + f'\r\n--{boundary}--\r\n'.encode())
    urllib.request.urlopen(urllib.request.Request(f"{BASE}/entities/{entity_id}/attachments", method="POST",
                                                  data=body.getvalue(),
                                                  headers={**HB, "Content-Type": f"multipart/form-data; boundary={boundary}"}))


clean = lambda name: re.sub(r"\s\(\d+\)$", "", name)  # "America (2)" -> "America"


def artists(rel):
    out = ""
    for a in rel["artists"]:
        out += clean(a["name"]) + {"": ", ", ",": ", "}.get(a.get("join", ""), f" {a['join']} ")
    return re.sub(r"[ ,&]+$", "", out.strip())


def fmt(rel):
    parts = []
    for f in rel["formats"]:
        qty = f"{f['qty']} × " if f.get("qty", "1") not in ("1", "") else ""
        parts.append(qty + ", ".join([f["name"]] + f.get("descriptions", []) + ([f["text"].strip()] if f.get("text", "").strip() else [])))
    return "; ".join(parts)


def barcode(rel):
    for i in rel.get("identifiers", []):
        if i["type"] == "Barcode":
            digits = re.sub(r"\D", "", i["value"])
            if len(digits) in (12, 13):
                return digits
    return ""


def tracklist(rel, room):
    """The tracklist in at most `room` characters (Homebox notes hold 1000): without durations if
    needed, then cut off with a count of what's left."""
    for durations in (True, False):
        lines = []
        for t in rel.get("tracklist", []):
            if t.get("type_") == "heading":
                lines.append(f"— {t['title']} —")
            elif t.get("type_") == "track":
                lines.append(f"{t['position']}  {t['title']}" + (f" ({t['duration']})" if durations and t.get("duration") else ""))
        if len("\n".join(lines)) <= room:
            return "\n".join(lines)
    while lines and len("\n".join(lines)) + 40 > room:
        lines.pop()
    left = sum(1 for t in rel.get("tracklist", []) if t.get("type_") == "track") - sum(1 for l in lines if not l.startswith("—"))
    return "\n".join(lines + [f"… and {left} more tracks (see Discogs)"])


def main():
    # Record type + default template
    templates = {t["name"]: t for t in hb("GET", "/templates")}
    tpl = templates.get("Record defaults")
    types = {t["name"]: t for t in hb("GET", "/entity-types")}
    if not DRY:
        tpl = tpl or hb("POST", "/templates", {
            "name": "Record defaults", "description": "Fields for vinyl records", "notes": "",
            "defaultQuantity": 1, "defaultInsured": False, "defaultLifetimeWarranty": False,
            "includeWarrantyFields": False, "includePurchaseFields": True, "includeSoldFields": False,
            "fields": [{"type": "text", "name": f, "textValue": ""} for f in RECORD_FIELDS if f != "Discogs"]})
        if "Record" not in types:
            types["Record"] = hb("POST", "/entity-types", {"name": "Record", "isLocation": False, "icon": "",
                                                          "defaultTemplateId": tpl["id"]})
    record_type = types.get("Record", {}).get("id")

    loc = next((l for l in hb("GET", "/entities?pageSize=500&isLocation=true")["items"] if l["name"] == LOCATION), None)
    if not loc:
        sys.exit(f"no location named {LOCATION!r}")

    # releases already in Homebox, by their Discogs link
    done = set()
    if record_type:
        page = 1
        while True:
            d = hb("GET", f"/entities?entityTypeIds={record_type}&pageSize=100&page={page}")
            for e in d["items"]:
                full = hb("GET", f"/entities/{e['id']}")
                done |= {f["textValue"] for f in full["fields"] if f["name"] == "Discogs"}
            if page * 100 >= d["total"]:
                break
            page += 1

    collection, page = [], 1
    while True:
        d = discogs(f"https://api.discogs.com/users/{DISCOGS_USER}/collection/folders/0/releases?per_page=100&page={page}&sort=artist")
        collection += d["releases"]
        if page >= d["pagination"]["pages"]:
            break
        page += 1
    cond = {f["id"]: f["name"] for f in discogs(f"https://api.discogs.com/users/{DISCOGS_USER}/collection/fields")["fields"]}

    masters = {}
    for n, entry in enumerate(collection, 1):
        rid = VINYL_INSTEAD.get(entry["id"], entry["id"])
        link = f"https://www.discogs.com/release/{rid}"
        if link in done:
            continue
        rel = discogs(f"https://api.discogs.com/releases/{rid}")
        artist, title = artists(rel), rel["title"]
        label = rel["labels"][0] if rel.get("labels") else {}
        year = rel.get("year") or ""
        original = ""
        if rel.get("master_id"):
            if rel["master_id"] not in masters:
                masters[rel["master_id"]] = discogs(f"https://api.discogs.com/masters/{rel['master_id']}").get("year") or ""
            original = masters[rel["master_id"]]
        notes = {cond.get(x["field_id"], ""): x["value"] for x in entry.get("notes") or []}
        genre = ", ".join(rel.get("genres", [])) + (" — " + ", ".join(rel["styles"]) if rel.get("styles") else "")
        kind = next((d for d in ("Compilation", "Album", "EP", "Single") if d in fmt(rel)), "Record")
        when = original or year
        desc = f"{kind}{f' from {when}' if when else ''} by {artist}"
        if year and original and str(year) != str(original):
            desc += f" ({year} pressing)"
        desc += "."
        values = {
            "Artist": artist, "Label": clean(label.get("name", "")), "Catalog #": label.get("catno", "").replace("none", ""),
            "Released": str(year or ""), "Original release": str(original) if original and str(original) != str(year) else "",
            "Format": fmt(rel), "Genre": genre, "Barcode": barcode(rel),
            "Media condition": notes.get("Media Condition", ""), "Sleeve condition": notes.get("Sleeve Condition", ""),
            "Discogs": link,
        }
        extra = []
        if notes.get("Notes"):
            extra.append(notes["Notes"])
        if entry["id"] in VINYL_INSTEAD:
            extra.append("Discogs listed this as a digital download; the details are from the most common vinyl "
                         "pressing. Check the sleeve barcode and change the Discogs entry if it's a different one.")
        head = "\n\n".join(extra)
        tl = tracklist(rel, 1000 - len(head) - 2)
        notes_text = "\n\n".join(extra + ([tl] if tl else []))[:1000]
        name = f"{artist} — {title}"
        print(f"[{n}/{len(collection)}] {name} · {values['Format']} · {values['Label']} {values['Catalog #']}")
        if DRY:
            continue

        e = hb("POST", "/entities", {"name": name, "description": desc[:1000], "entityTypeId": record_type,
                                     "parentId": loc["id"], "quantity": 1, "tagIds": []})
        try:
            fill(e, full=hb("GET", f"/entities/{e['id']}"), name=name, desc=desc, record_type=record_type, loc=loc,
                 values=values, notes_text=notes_text, rel=rel)
        except Exception:
            hb("DELETE", f"/entities/{e['id']}")  # don't leave a half-made record behind (a re-run would skip it)
            raise


def fill(e, full, name, desc, record_type, loc, values, notes_text, rel):
    hb("PUT", f"/entities/{e['id']}", {
        **{k: full.get(k) for k in ("archived", "assetId", "insured", "lifetimeWarranty", "serialNumber",
                                    "purchaseDate", "purchaseFrom", "purchasePrice", "soldDate", "soldNotes",
                                    "soldPrice", "soldTo", "syncChildEntityLocations", "warrantyDetails",
                                    "warrantyExpires", "quantity")},
        "id": e["id"], "name": name, "description": desc, "entityTypeId": record_type, "parentId": loc["id"],
        "manufacturer": values["Label"], "modelNumber": values["Catalog #"], "notes": notes_text, "tagIds": [],
        "fields": [{"id": None, "name": k, "type": "text", "textValue": v, "numberValue": 0, "booleanValue": False}
                   for k, v in values.items() if v],
    })
    img = next((i for i in rel.get("images", []) if i["type"] == "primary"), (rel.get("images") or [None])[0])
    if img:
        upload_photo(e["id"], discogs(img["uri"], raw=True), "cover.jpg")
    else:
        print("   (no cover on Discogs)")


if __name__ == "__main__":
    main()
