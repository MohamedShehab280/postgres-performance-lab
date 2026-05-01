# Hospital Management System — Complete Student Guide

**Course**: Advanced Database
**Project**: Hospital DB Dashboard

> This guide explains not just *what* to do, but *why* it works. Read it end to end before starting.

---

## Part 0 — The Big Picture

You are going to build two identical hospital databases. Same tables, same data, same volume. The only difference:

- `hospital_slow` — no custom indexes, only primary keys. Every query scans every row.
- `hospital_fast` — same data, but with the indexes you add. The same queries run much faster.

The dashboard app connects to both at the same time and runs your queries against both. You see the difference in real numbers, not theory.

The project is delivered in parts:

- **Part 1 - Indexes** (`03-student-tasks.md`). Read the IT audit report in `05-business-case.md`, find the performance problems hidden in the staff quotes, build indexes in the Index Lab, confirm each one in the Performance Lab, verify in the Index Inspector.
- **Part 2 - Concurrency** (`06-concurrency-tasks.md`). Reproduce the 5 classic concurrency bugs (Lost Update, Non-Repeatable Read, Phantom Read, Dirty Read attempt, Deadlock) in the Transaction Lab by inventing your own hospital scenarios, then fix each one.
- **Part 3 - Backup & Recovery.** Comes later.

---

## Part 1 — Setup

### How we set up the two databases

Running the data generator twice would give you *similar* but not *identical* rows, because the script uses randomness. So instead:

1. Generate the data once, on `hospital_slow`.
2. Tell PostgreSQL to clone the whole database: `CREATE DATABASE hospital_fast TEMPLATE hospital_slow;`. This copies it byte-for-byte in a few seconds.
3. Add your indexes only on `hospital_fast`.

One line of SQL, no terminal, no backup files. The `pg_dump` / `psql restore` workflow is covered later in Part 3 (Backup & Recovery), where it's the actual topic.

---

### Step 1: Create hospital_slow and its tables

Open **pgAdmin** and connect to the `postgres` database.

Open a Query Tool and run **`01a-schema-hospital-slow.sql`**.

This does two things:
1. `CREATE DATABASE hospital_slow`
2. Creates all 9 tables inside it

The 9 tables:

| Table | What it stores |
|---|---|
| `patients` | 500,000 patient records |
| `doctors` | 500 doctors |
| `rooms` | 100 hospital rooms |
| `appointments` | 2,000,000 booking records (the big table) |
| `diagnoses` | Diagnosis codes per appointment |
| `prescriptions` | Drugs prescribed per appointment |
| `lab_results` | 1,000,000 lab tests |
| `admissions` | Room admissions |
| `billing` | 1,200,000 billing records |

Verify the tables were created (connect to hospital_slow first):

```sql
SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'public'
ORDER BY table_name;
```

---

### Step 2: Generate data on hospital_slow

Connect to **`hospital_slow`** in pgAdmin and run `02-data-generation.sql`.

**This will take 5–10 minutes.** Do not close pgAdmin.

The script uses PostgreSQL's `generate_series()` to insert millions of rows — pure SQL, no Python or CSV files needed.

When finished, verify the counts:

```sql
SELECT
    (SELECT COUNT(*) FROM patients)     AS patients,
    (SELECT COUNT(*) FROM appointments) AS appointments,
    (SELECT COUNT(*) FROM lab_results)  AS lab_results,
    (SELECT COUNT(*) FROM billing)      AS billing;
```

Expected: ~500K patients, ~2M appointments, ~1M lab results, ~1.2M billing rows.

---

### Step 3: Clone hospital_slow into hospital_fast

In pgAdmin, disconnect from `hospital_slow` first. Right-click it in the tree and pick *Disconnect Database*. Any Query Tool tab pointing at it also counts as a connection, so close those.

Then connect to the `postgres` database, open a Query Tool, and run:

```sql
CREATE DATABASE hospital_fast TEMPLATE hospital_slow;
```

PostgreSQL copies the whole database for you. Takes a few seconds. When it's done:
- `hospital_fast` has the same 9 tables.
- `hospital_fast` has the exact same rows as `hospital_slow`.
- `hospital_fast` has no custom indexes yet. You add those in Step 5.

Verify by connecting to `hospital_fast` and running:

```sql
SELECT
    (SELECT COUNT(*) FROM patients)     AS patients,
    (SELECT COUNT(*) FROM appointments) AS appointments;
```

The numbers must match `hospital_slow`. If they do, the clone worked.

If you get `source database "hospital_slow" is being accessed by other users`, you still have a session open to it. Right-click it, *Disconnect Database*, close any open Query Tool tab, then try again.

The `pg_dump` / `psql` workflow is covered properly in Part 4.

---

### Step 4: Configure and run the app

Open `dashboard/app.py` in any text editor. Find this block:

```python
BASE = {
    "host":     "localhost",
    "port":     5432,
    "user":     "postgres",
    "password": "postgres",   # ← change this to your PostgreSQL password
}
```

Change the password to whatever you set when you installed PostgreSQL.

Open a terminal in the `dashboard/` folder and run:

```bash
pip install flask psycopg2-binary
python app.py
```

Open your browser and go to: **http://localhost:5000**

---

## Part 2 — Understanding Each Tab

---

### Tab 1: Overview

When the app loads, the Overview tab shows row counts from both databases side by side.

What to check:
- Both databases show the same numbers (for example, both show 500,000 patients).
- Both connect without errors.

If one shows an error, check your password in `app.py`, or make sure the database was actually created and has data.

This is your opening proof for the demo. Real row counts, read live from PostgreSQL.

---

### Tab 2: Index Lab

This is where you do the actual work. Every index you are required to build lives here.

There are 15 slots in total. The first 10 are required. Slots 11 to 15 are bonus — you only fill them if you found more problems in `05-business-case.md` and want the extra credit.

For each slot you use, the app asks you to fill in four fields:

1. **Problem name** — a short title for the issue you are solving, in your own words.
2. **Justification from the business case** — paste the actual quote or paragraph from `05-business-case.md` that points to this problem. This shows you understood why the index is needed, not just that you wrote one.
3. **CREATE INDEX statement** — the SQL that will run on `hospital_fast`.
4. **Test query** — a `SELECT` that filters on the same column(s) so PostgreSQL will actually use the index.

Don't use `LIMIT` in your test query. It changes the planner's cost model and often pushes it to a Parallel Seq Scan instead of your index, which makes it look like your index did nothing.

When you click Create Index, the app runs the SQL on `hospital_fast` and checks that the index shows up in `pg_indexes`. Your work is saved in the browser, so closing the tab won't lose it.

The app also enforces a minimum mix on the required 10:
- at least 5 regular (single column, no `WHERE`)
- at least 3 composite (two or more columns)
- at least 2 partial (has a `WHERE` clause, e.g. `WHERE paid_at IS NULL`)

When you have created an index, you can jump directly to the Performance Lab using the shortcut link that appears after success.

---

### Tab 3: Performance Lab

This is where you prove each index actually helps. Every index you built in the Index Lab shows up here as a button labelled with the problem name you wrote.

How to use it:

1. Click a query button (Query 1, Query 2, etc.).
2. The test query, the index, and your problem description appear.
3. Click Run on Both Databases.
4. Wait for both sides to finish.

What you'll see:

- Two timing numbers (for example `hospital_slow: 3,421 ms` vs `hospital_fast: 8 ms`).
- A speedup multiplier.
- The full EXPLAIN ANALYZE plan for each database.
- The scan type extracted from each plan.

**EXPLAIN ANALYZE in one paragraph.**

`EXPLAIN ANALYZE` shows the query execution plan — how PostgreSQL decided to fetch the data. The part you care about is the scan type:

| Scan type | What it means |
|---|---|
| Seq Scan | PostgreSQL reads every row in the table one by one. On a 2M-row table, this is slow. |
| Index Scan | PostgreSQL uses the index to jump straight to the matching rows. |
| Bitmap Heap Scan | PostgreSQL uses the index to find which pages contain matches, then reads only those pages. Good for queries that return many rows. |

On `hospital_slow` you will see Seq Scan. On `hospital_fast` you should see Index Scan or Bitmap Heap Scan using your index.

If `hospital_fast` still shows Seq Scan:

- You used `LIMIT`.
- Your `WHERE` doesn't match the indexed columns.
- For partial indexes, your `WHERE` doesn't include the same predicate the index was built with.
- For `LIKE 'prefix%'` on a text column, you probably need `text_pattern_ops` in the index definition.

Fix the index or the query and run it again.

---

### Tab 4: Index Inspector

Shows every custom index (excluding primary keys) on each database.

**Expected result:**
- `hospital_slow`: 0 custom indexes
- `hospital_fast`: one row for each index you built in the Index Lab

Click "Refresh" on both sides to load the current state.

**If hospital_slow shows indexes:** You may have accidentally created indexes on it. Drop them:
```sql
-- Connect to hospital_slow, then:
SELECT indexname FROM pg_indexes WHERE schemaname='public' AND indexname NOT LIKE '%_pkey';
-- Drop each one that appears
```

**If hospital_fast shows fewer indexes than you expected:** Go back to the Index Lab and re-create the missing ones.

---

### Tab 5: Transaction Lab (Part 2)

Where you do the Part 2 work. Five fixed slots, one per concurrency problem - Lost Update, Non-Repeatable Read, Phantom Read, Dirty Read attempt, Deadlock.

For each slot you fill in 8 fields:

1. Your hospital scenario (invent your own, do not reuse the slide example).
2. Session A buggy SQL.
3. Session B buggy SQL.
4. What went wrong (the bad outcome you saw).
5. Session A fixed SQL.
6. Session B fixed SQL.
7. Why the bug happened.
8. Why the fix works.

Each slot has **Copy Session A SQL** and **Copy Session B SQL** buttons that put the script on your clipboard. Paste each into its own pgAdmin Query Tool tab and run them step by step in the right order.

A slot's status badge moves from `Not started` to `In progress` to `Complete` as you fill it. The progress bar at the top shows `x / 5`. Everything is saved in your browser.

Full task description is in `06-concurrency-tasks.md`.

---

## Part 3 — Common Mistakes

**"Performance Lab shows the same speed on both databases."**
You probably added indexes to `hospital_slow` by accident, or forgot to run them on `hospital_fast`. Open Index Inspector — `hospital_slow` must show 0 custom indexes.

**"Performance Lab shows Seq Scan on `hospital_fast` too, even though I created the index."**
Usually one of:
- You used `LIMIT` in the test query.
- The `WHERE` clause doesn't match the indexed columns.
- For a partial index, your `WHERE` doesn't include the same predicate the index was built with.
- For `LIKE 'prefix%'` on a text column, you need `text_pattern_ops` in the index.

**"App crashes on startup with connection refused."**
PostgreSQL isn't running.
- Windows: `net start postgresql-x64-18` (match your version)
- macOS: `brew services start postgresql`
- Linux: `sudo systemctl start postgresql`

**"`CREATE DATABASE ... TEMPLATE` says source is being accessed by other users."**
Disconnect from `hospital_slow` in pgAdmin and close any Query Tool tab pointing at it, then try again.
