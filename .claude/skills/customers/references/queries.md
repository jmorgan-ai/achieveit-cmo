# Customer Marketing data

Salesforce `soqlQuery` (read-only), won New Business since 2024 so older customers are included:
```
SELECT Id, Account.Name, CreatedDate, CloseDate, StageName, IsWon, IsClosed, Amount, Market__c, Sub_Market__c, Attribution_Source__c, Demo_Attribution__c, Account.PR_Status__c, Account.Public_Dashboard_Available__c, Account.Public_Dashboard_s__c FROM Opportunity WHERE Type = 'New Business' AND IsWon = true AND CloseDate >= 2024-01-01 ORDER BY CloseDate LIMIT 2000
```
Capture: `python3 $C --tool soqlQuery --text --match-contains q="IsWon = true AND CloseDate >= 2024-01-01" --out $W/in/opps.json`.

Optional, Buffer `list_posts` (read-only): organizationId 5a789d8d01a71cee3c1c5351, channelIds [6061c7c1edd0a87f33ed4ac9], status sent, dueAt window of the last 12 months, first 100, no metrics needed.
Capture: `python3 $C --tool list_posts --text --match-contains organizationId=5a789d8d --out $W/in/buffer_posts.json`.
Posts made directly on LinkedIn may be missing from Buffer, so "not featured" means "not seen in Buffer".

## Website pages (public, read with WebFetch)
- Customer stories: https://www.achieveit.com/resources/case-studies/ (about 15 shown; a "Load More" button hides the rest)
- Customer dashboards: https://www.achieveit.com/public-dashboards/ (24 shown; same button)
Save one line per customer, `Name | url`, to `$W/in/site_stories.txt` and `$W/in/site_dashboards.txt` (copy names exactly from the fetch result). For each of the first
eight candidates the script lists, a `WebSearch` for `site:achieveit.com "<account name>"` catches stories beyond the first batch; add any hit to `site_stories.txt`
and re-run the pack. If a page can't be read, leave that file out; the pack says so.
Salesforce PR status values: Can use name & logo, Logo/news release approved (cleared); Mention as client only (name only); Approval required, Pre-approval required (ask first);
To be determined, Not specified in contract (unknown); Cannot use (left out).
