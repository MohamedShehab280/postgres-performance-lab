# Part 2 — Concurrency

Submission: live demo on your running app.

Assumes Part 1 is done and both databases are loaded.

## What you do

Reproduce 5 concurrency problems, then fix each one. For each:

1. Invent your own hospital scenario. Don't reuse the slide example.
2. Write SQL that causes the bug, in two sessions.
3. Run it in two pgAdmin tabs and watch it break.
4. Write SQL that fixes it.
5. Run the fix and confirm the bug is gone.
6. Explain why it broke and why your fix works.

Everything goes in the Transaction Lab tab. 5 slots, 8 fields each. Saved in your browser.

## The 5 problems

Pick the right tool yourself. Descriptions only state the symptom.

**1. Lost Update.** Two sessions read the same row, both write back. One write disappears.

**2. Non-Repeatable Read.** Same SELECT, same transaction, two different results.

**3. Phantom Read.** Same SELECT with a WHERE filter, same transaction, different number of rows.

**4. Dirty Read attempt.** Try to read another session's uncommitted change. It won't work in PostgreSQL — explain why.

**5. Deadlock.** Two sessions, each waiting on a lock the other holds. PostgreSQL kills one. Reproduce it, then rewrite both so it can't happen.

## Slot fields

1. **Hospital scenario** — one or two sentences in plain language describing the situation.
2. **Session A buggy SQL** — the statements you ran in tab A to cause the bug.
3. **Session B buggy SQL** — same for tab B.
4. **What went wrong** — what you actually saw: wrong final value, different row count, error message, etc.
5. **Session A fixed SQL** — your corrected version for tab A.
6. **Session B fixed SQL** — same for tab B.
7. **Why it broke** — one short paragraph, your own words.
8. **Why the fix works** — same.

## Where to run

Two pgAdmin Query Tool tabs on `hospital_slow`. Use the Copy buttons in each slot. Step order across the two sessions matters — plan it.

## Done

- 5 slots complete.
- Both buggy and fixed runs work live.
- Your two "why" answers are right.
- No scenario from the slides.
