# ICP data

One query, `soqlQuery` (about 1,350 rows, 840 KB; spills to a file, `shared/capture.py` follows it):

```
SELECT Id, Account.Name, CreatedDate, CloseDate, StageName, IsWon, IsClosed, Amount, Market__c, Sub_Market__c, Attribution_Source__c, Demo_Attribution__c, Account.Type, Account.NumberOfEmployees, Account.BillingState FROM Opportunity WHERE Type = 'New Business' AND CreatedDate >= 2025-01-01T00:00:00Z AND CreatedDate < <first day of the month after the pack month>T00:00:00Z ORDER BY CreatedDate LIMIT 2000
```
The Customer Marketing agent reads the same query, so the two can share one capture when they run on the same day.
`Custom_Source__c`, UTM and campaign fields cannot be grouped in SOQL: fetch rows and count in the script.
