# Syncing the Site Database from Airtable

**Airtable is the source of truth.** This repo's `index.html` is a published view of it.
Sync is manual / on-demand (no token, no schedule) — just ask Claude to "sync the site database",
or run the steps below.

## What sync does
`sync.py` refreshes the four accommodation fields (village / villageOperator / villageType /
capacity) on existing sites from Airtable, adds any new Airtable site-type records, excludes
FM/builder operator companies and "N/A (Indirect…)" placeholders, and preserves Site-DB-only
records (e.g. east-coast / LNG sites not in Airtable). It is conservative and idempotent.

## One-command procedure (Claude session)
1. **Export Airtable** — via the Airtable MCP, `list_records_for_table`:
   - base `appf49C30tIS3TkHp`, table `tbl6WfiSuU5oQIWqZ`
   - filter: Type is any of `Owner-operator site` / `Village operator` (choice IDs
     `selbirmev7gRc8vj0`, `selUQtsbYK7fRI39J`), `pageSize` 200, **all fields**.
   - The result exceeds the token limit and is auto-saved to a `tool-results/*.txt` file — use that path.
2. **Run:** `python sync.py <that-export.json> --push`
   - writes `index.html`, copies it to the vault, commits, and pushes to `main`.
   - GitHub Pages rebuilds ~1 min later at https://brayden-1014.github.io/simplex-site-database/

Run without `--push` first if you want to preview the change (`git diff --stat`).

## Notes
- Requires `gh`/git auth configured (already set up for Brayden-1014).
- `sync.py` only auto-syncs accommodation fields + new sites. Operator/region/status changes on
  *existing* sites are not auto-propagated (rare) — ask Claude if one needs updating.
- Field IDs and rules are documented at the top of `sync.py`.
