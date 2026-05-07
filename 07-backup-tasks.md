# Part 3 - Backup & Recovery

The point of this part is to show you understand the difference between the three recovery tools and when each one fits.

## The 3 tools

`pg_dump` restore. A snapshot of the database at the moment the dump ran.

`pg_basebackup` + WAL replay to the end. A full physical copy, plus every change recorded since.

PITR. Same as above, but you stop the WAL replay at a chosen second.

## Your task

Write the recovery for the four scenarios below. Three are given, one you invent.

For each scenario, write three short things:

1. Which tool fits this case and why, in one or two sentences.
2. The recovery plan, three to five short steps in order.
3. What is still lost after the recovery, and one policy change that would have prevented it.

No SQL, no full runbook. Just the thinking.

## Scenarios

### Scenario A

Wednesday 9 AM, a developer's migration script had a typo and ran `DROP TABLE prescriptions` on `hospital_fast`. Pharmacists noticed four hours later. The hospital takes one `pg_dump` per night at 2 AM. Nothing else.

### Scenario B

Sunday 4:47 PM, the database server's disk failed. PostgreSQL crashed. The hospital takes a weekly `pg_basebackup` and archives WAL files every minute to a separate disk. Around 17,000 transactions happened today. Bring the system back up with minimum data loss.

### Scenario C

Friday 11:23 AM, an admin ran `DELETE FROM appointments WHERE status = 'scheduled'` thinking they were on test, but they were on production. 6,200 upcoming appointments are gone. Last `pg_basebackup` was 9 hours ago. WAL archiving is on.

### Scenario D - your own

Invent your own hospital disaster. Be specific about what broke, when, and what backup tools were in place before the incident. Do not reuse A, B, C, or another student's invention.

## Done

All four scenarios answered. The tool you picked actually fits the scenario. Scenario D is plausible and not a copy.
