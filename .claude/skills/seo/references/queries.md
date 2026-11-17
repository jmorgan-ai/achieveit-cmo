# SEO data

Feeds workbook: `read_resource` on `file:///<driveId>/<itemId>` from cmo-system `references/ids.md`, one sheet per call with
`startPage` = `endPage` = the sheet number. Large sheets spill to a file; `shared/capture.py` follows the pointer, so always capture
rather than copy.

| Input | Sheet | Capture |
|---|---|---|
| gsc_daily.txt | 7 GSC_Daily | `python3 $C --tool read_resource --text --match-contains uri=01IJF3MH7JFUTNS7AE3NGLRUZMTQX56HIL --match startPage=7 --out $W/in/gsc_daily.txt` |
| gsc_queries.txt | 8 GSC_Queries | same, `--match startPage=8 --out $W/in/gsc_queries.txt` (first page, about 190 KB, sorted by impressions) |
| gsc_pages.txt | 9 GSC_Pages | same, `--match startPage=9` |
| ga4_monthly.txt | 4 GA4_Monthly_Channel | same, `--match startPage=4` (optional) |
| feed_status.txt | 2 Feed_Status | same, `--match startPage=2` |

GSC_Daily keeps 90 days, so only full months inside that window are compared. GSC_Queries and GSC_Pages are the last 28 days.

## Semrush (project 23016017 "2025 Priorities")
- Site audit health: `execute_report` report `info`, params `{"project_id": 23016017}` (100 API units).
  Capture: `python3 $C --tool execute_report --match report=info --out $W/in/audit_info.json`.
- Optional rank tracking: `campaigns` `{"project_id": 23016017}` returns campaign `23016017_2656019` (achieveit.com, US, desktop,
  21 keywords); `tracking_overview_organic` takes `campaign_id`, `url` (`achieveit.com`) and optional `date_begin`/`date_end`
  (100 units). Capture to `$W/in/pt_overview.json`. The pack only notes it for now; findings from it are a later build.
- Budget: the Semrush account has about 49,000 API units left; one pack uses about 200.
