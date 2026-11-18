# Re-run switch

**Re-run: OFF** (report only, decided by Jonathan 2026-11-18; "build it so a re-run is easy").

To turn it ON, change this one line to `Re-run: ON` in a pull request that Jonathan merges. Nothing else needs to change: the Health skill already
reads `rerun.json` (task, trigger id, reason) and calls `fire_trigger` once per failed pack per day, same day only.
Rules when ON: never re-run a pack that posted; never more than once per task per day; Health posts that it did so; a task that fails again after
a re-run is left for a person.
