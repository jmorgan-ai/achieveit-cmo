# Marketing Ops queries

Run with the Salesforce connector (`soqlQuery`). `Y` = the year of the month under review, `Y1` = Y - 1, `Y2` = Y - 2.
Never retype a result: capture each one to a file with `shared/capture.py` (the `--match-contains` text below picks the call).
Every result must say `"done": true`; if not, the script stops (exit 2).

## A. Opps for the pack -> `in/opps.json`
```sql
SELECT Id, Name, AccountId, Account.Name, CreatedDate, CloseDate, StageName, IsClosed, IsWon, Amount,
  Demo_Attribution__c, Attribution_Source__c, Primary_Campaign_Source_Name__c, Custom_Source__c, LeadSource, Lead_Source_Mentioned__c,
  Market__c, Owner.Name
FROM Opportunity
WHERE Type = 'New Business' AND CreatedDate >= Y1-01-01T00:00:00Z
  AND (Demo_Attribution__c != 'OSDR Sourced' OR Attribution_Source__c = 'Inbound'
       OR Primary_Campaign_Source_Name__c LIKE 'Demo%' OR Primary_Campaign_Source_Name__c LIKE 'Website%'
       OR Primary_Campaign_Source_Name__c LIKE '%Webinar%' OR (Market__c = null AND IsClosed = false))
ORDER BY CreatedDate LIMIT 2000
```
Capture: `--match-contains "q=(Market__c = null AND IsClosed = false)"`. About 400 rows; OSDR opps come in only when
they look inbound or need a field fixed (OSDR totals come from B).

## B. OSDR totals -> `in/osdr.json`
```sql
SELECT CALENDAR_YEAR(CreatedDate) y, IsClosed, IsWon, Attribution_Source__c, COUNT(Id) n, SUM(Amount) amt
FROM Opportunity
WHERE Type = 'New Business' AND CreatedDate >= Y1-01-01T00:00:00Z AND Demo_Attribution__c = 'OSDR Sourced'
GROUP BY CALENDAR_YEAR(CreatedDate), IsClosed, IsWon, Attribution_Source__c
```
Capture: `--match-contains "q=Attribution_Source__c, COUNT(Id) n, SUM(Amount) amt FROM"`.

## C. Lost new-business history, one call per close year -> `in/lost_<year>.json`
For each of Y2, Y1 and Y (daily: the current year and the two before):
```sql
SELECT Id, Name, AccountId, CloseDate, Demo_Attribution__c
FROM Opportunity
WHERE Type = 'New Business' AND IsClosed = true AND IsWon = false AND CALENDAR_YEAR(CloseDate) = <year>
ORDER BY CloseDate LIMIT 2000
```
Capture each: `--match-contains "q=CALENDAR_YEAR(CloseDate) = <year>" --out in/lost_<year>.json`.
One year is under 2,000 rows (2024 had about 950). If a year ever returns `"done": false`, the script stops; say so in
the run line so the query can be split (pull request).

## D. Daily: opps created since the last run -> `in/opps.json`
Same fields as A, all new-business opps:
```sql
SELECT Id, Name, AccountId, Account.Name, CreatedDate, CloseDate, StageName, IsClosed, IsWon, Amount,
  Demo_Attribution__c, Attribution_Source__c, Primary_Campaign_Source_Name__c, Custom_Source__c, LeadSource, Lead_Source_Mentioned__c,
  Market__c, Owner.Name
FROM Opportunity
WHERE Type = 'New Business' AND CreatedDate >= <SINCE>T12:00:00Z
ORDER BY CreatedDate LIMIT 500
```
`SINCE` = the previous weekday (Monday: the Friday before). Capture: `--match-contains "q=CreatedDate >= <SINCE>T12:00:00Z"`.

## E. MQLs by month -> `in/mql.json`
```sql
SELECT CALENDAR_YEAR(CreatedDate) y, CALENDAR_MONTH(CreatedDate) m, COUNT(Id) n, COUNT_DISTINCT(LeadOrContactId) d
FROM CampaignMember
WHERE CreatedDate >= Y1-01-01T00:00:00Z
  AND (Campaign.Name LIKE 'Demo - %' OR Campaign.Name LIKE 'Website - Product Tour%')
GROUP BY CALENDAR_YEAR(CreatedDate), CALENDAR_MONTH(CreatedDate)
ORDER BY CALENDAR_YEAR(CreatedDate), CALENDAR_MONTH(CreatedDate)
```
Capture: `--match-contains "q=COUNT_DISTINCT(LeadOrContactId) d FROM CampaignMember"`. The script uses `d` (distinct people).

## F. Budget sheet -> `in/budget.txt`
`read_resource` on `file:///<budget driveId>/<budget itemId>` (references/ids.md in cmo-system). The first call lists the
sheets; read the one named `<Y> Spend` with `startPage` = `endPage` = its number. The text must contain `## Sheet: <Y> Spend`.
Capture: `--tool read_resource --match-contains uri=<budget itemId> --match startPage=<n> --text --out in/budget.txt`.
If it can't be read, run without it: spend figures drop out and the post says so.
