#!/usr/bin/env python3
"""
Sync the Simplex Site Database (index.html) from an Airtable Opportunities export.

Airtable is the source of truth for accommodation data and the target-account list.
This script is CONSERVATIVE and non-destructive:
  - For sites already in the Site DB (matched by name): refreshes the four
    accommodation fields (village / villageOperator / villageType / capacity)
    from Airtable. Everything else on the existing row is preserved.
  - For Airtable site-type records NOT yet in the Site DB: adds them as new rows.
  - FM/builder operator companies (Sodexo, Civeo, Compass, Ventia, ISS, Sirrom,
    BBB, Centurion Corp, Housing 101, Exact) and "N/A (Indirect ...)" placeholders
    are excluded (they are not physical sites).
  - Site-DB-only records (e.g. east-coast / LNG sites not in Airtable) are preserved.

Usage:
    python sync.py <airtable_export.json>            # writes index.html, prints diff summary
    python sync.py <airtable_export.json> --push     # also git commit + push + copy to vault

The Airtable export is the raw JSON from the Opportunities table filtered to
site-type records (Type = Owner-operator site OR Village operator), all fields.
Get it via the Airtable MCP (list_records_for_table) and save the tool result file.
See SYNC.md for the full one-command procedure.

Field IDs (Opportunities table tbl6WfiSuU5oQIWqZ in base appf49C30tIS3TkHp):
  name fld6nqfNu2ygAMhXr | operator fldgLVkue14o6uYkQ | commodity fldJeBDDotgWCgqX5
  region fldOZASaFoVQc00hg | state fldK8houZLV5MR93h | opportunityType fldQ9sKBx0PXg4lh5
  telcoNotes fldvoiXSARAgxdlVQ | village fld5tAAUtI0Hlyzk7 | villageOperator fld7GpubJ7W9b1fCq
  villageType fldNFI3nYv31R0A8X | capacity fldsLi9IjRVfQKpGt
"""
import re, json, sys, os, subprocess, datetime, shutil

HERE = os.path.dirname(os.path.abspath(__file__))
INDEX = os.path.join(HERE, "index.html")
VAULT_INDEX = r"C:/Users/brayd/Obsidian Vault/000 - Braydens Brain/01 - Work/Simplex Communications/05 Improvement/Initiatives/Simplex Intelligence/index.html"
TODAY = datetime.date.today().isoformat()

F = {"name":"fld6nqfNu2ygAMhXr","operator":"fldgLVkue14o6uYkQ","commodity":"fldJeBDDotgWCgqX5",
     "region":"fldOZASaFoVQc00hg","state":"fldK8houZLV5MR93h","opportunityType":"fldQ9sKBx0PXg4lh5",
     "telcoNotes":"fldvoiXSARAgxdlVQ","village":"fld5tAAUtI0Hlyzk7","villageOperator":"fld7GpubJ7W9b1fCq",
     "villageType":"fldNFI3nYv31R0A8X","capacity":"fldsLi9IjRVfQKpGt"}

norm = lambda s: re.sub(r'[^a-z0-9]', '', (s or '').lower())
region_map = lambda x: "Goldfields-Esperance" if x == "Goldfields" else x

def cell(cv, key):
    v = cv.get(F[key])
    return v["name"] if isinstance(v, dict) else (v or "")

def is_company(name, op):
    opl = op.lower()
    return (name.startswith("N/A (Indirect")
            or re.search(r'tier\s*[0-9]', opl)
            or any(s in opl for s in ["facilities management", "camp builder", "village fm"]))

def status_of(tn):
    t = tn.lower()
    if "administration" in t: return "Care & Maintenance"
    if any(s in t for s in ["care and maintenance","care & maintenance","suspended","temporarily closed"]): return "Care & Maintenance"
    if any(s in t for s in ["rehabilitation","closure","closed 20"]): return "Rehab / Closure"
    return "Active"

def main():
    if len(sys.argv) < 2:
        sys.exit("usage: python sync.py <airtable_export.json> [--push]")
    export, push = sys.argv[1], ("--push" in sys.argv)

    html = open(INDEX, encoding="utf-8").read()
    s = html.index("const data = [") + len("const data = ")
    e = html.index("\n];", s) + len("\n];")
    sites = json.loads(html[s:e].rstrip().rstrip(";"))
    prefix, suffix = html[:s], html[e:]

    at = json.load(open(export, encoding="utf-8"))["records"]
    by_name = {norm(r["name"]): r for r in sites}
    maxid = max(r["id"] for r in sites)

    refreshed = added = skipped = 0
    for r in at:
        cv = r["cellValuesByFieldId"]; name = cell(cv, "name"); op = cell(cv, "operator")
        if is_company(name, op):
            skipped += 1; continue
        existing = by_name.get(norm(name))
        if existing:
            if cell(cv, "village"):  # only refresh accommodation when Airtable has it
                before = {k: existing.get(k) for k in ("village","villageOperator","villageType","capacity")}
                existing["village"] = cell(cv, "village")
                existing["villageOperator"] = cell(cv, "villageOperator") or "Unknown"
                existing["villageType"] = cell(cv, "villageType")
                existing["capacity"] = cell(cv, "capacity")
                if any(before[k] != existing[k] for k in before):
                    existing["lastUpdated"] = TODAY; refreshed += 1
        else:
            maxid += 1; tn = cell(cv, "telcoNotes")
            sites.append({"id": maxid, "name": name, "operator": op or "TBC",
                "commodity": cell(cv,"commodity") or "Unknown", "region": region_map(cell(cv,"region")),
                "state": cell(cv,"state") or "WA", "status": status_of(tn),
                "village": cell(cv,"village") or "TBC", "villageOperator": cell(cv,"villageOperator") or "Unknown",
                "villageType": cell(cv,"villageType") or "TBC", "capacity": cell(cv,"capacity") or "TBC",
                "opportunityType": cell(cv,"opportunityType") or "Brownfields", "telcoNotes": tn,
                "source": "Airtable sync", "dateAdded": TODAY, "lastUpdated": TODAY})
            by_name[norm(name)] = sites[-1]; added += 1

    rows = ",\n".join("  " + json.dumps(r, ensure_ascii=False, separators=(",", ":")) for r in sites)
    json.loads("[\n" + rows + "\n]")  # validate
    open(INDEX, "w", encoding="utf-8").write(prefix + "[\n" + rows + "\n];" + suffix)
    print(f"records: {len(sites)} | refreshed: {refreshed} | added: {added} | skipped companies: {skipped}")

    if push:
        if os.path.exists(os.path.dirname(VAULT_INDEX)):
            shutil.copyfile(INDEX, VAULT_INDEX); print("vault copy updated")
        subprocess.run(["git", "-C", HERE, "add", "index.html"], check=True)
        if subprocess.run(["git", "-C", HERE, "diff", "--cached", "--quiet"]).returncode == 0:
            print("no changes to push")
        else:
            subprocess.run(["git","-C",HERE,"-c","user.name=Brayden Ainger",
                "-c","user.email=brayden.ainger@outlook.com","commit","-m",
                f"Sync Site DB from Airtable ({TODAY}): +{added} sites, {refreshed} refreshed"], check=True)
            subprocess.run(["git", "-C", HERE, "push", "origin", "main"], check=True)
            print("pushed")

if __name__ == "__main__":
    main()
