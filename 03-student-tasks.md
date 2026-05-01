# Hospital DB - Final Project Task Sheet (Part 1)

**Course**: Advanced Database
**Submission**: Live demo on your running dashboard app.

This is Part 1 - Indexes. Part 2 (Concurrency) is in `06-concurrency-tasks.md`. Part 3 (Backup & Recovery) will come later.

No Word documents, no screenshots, no written reports. You open the app in front of the instructor and walk through your indexes.

## Setup

Full steps are in `README.md`. The short version:

1. Clone the repo, then `pip install flask psycopg2-binary`.
2. Run `01a-schema-hospital-slow.sql` in pgAdmin.
3. Run `02-data-generation.sql` inside `hospital_slow` (about 6M rows).
4. Disconnect from `hospital_slow`, connect to `postgres`, then run:
   `CREATE DATABASE hospital_fast TEMPLATE hospital_slow;`
5. Set your password in `dashboard/app.py` and run `python app.py`.
6. Open http://localhost:5000.

Both databases must show identical row counts on the Overview tab before you start the actual work.

## What you do

### 1. Read the business case

Open `05-business-case.md`. It is written as quotes from hospital staff about things that are slow or painful in their day. Hidden in those quotes are 15 separate performance problems that the right indexes can fix. Your job is to find them.

### 2. Create 10 indexes (plus up to 5 bonus)

You need 10 indexes that solve 10 of the problems from the report.

The app enforces this minimum mix on the required 10:

- at least 5 regular (single column, no `WHERE`)
- at least 3 composite (two or more columns)
- at least 2 partial (has a `WHERE` clause, e.g. `WHERE paid_at IS NULL`)

The Index Lab tab has 15 slots. Slots 1-10 are required. Slots 11-15 are bonus - if you catch more problems in the report and fix them, you get extra credit, but they are optional.

### 3. Fill in the 4 fields for each index in the Index Lab

For every slot you use, the app asks you to enter:

1. **Problem name** - short title for what you're solving, in your own words.
2. **Justification from the business case** - paste the quote or paragraph from `05-business-case.md` that points to this problem. This is how you show you understood why the index is needed, not just that you wrote one.
3. **CREATE INDEX statement** - the SQL that creates the index on `hospital_fast`.
4. **Test query** - a `SELECT` that filters on the same column(s) so PostgreSQL will actually use the index.

Don't use `LIMIT` in your test query. It changes the planner's cost model and can push it to a Parallel Seq Scan instead of your index - making it look like your index did nothing.

When you click Create Index, the app runs the SQL on `hospital_fast` and checks that the index exists in `pg_indexes`.

### 4. Verify in the Performance Lab

Switch to the Performance Lab tab. Every index you created shows up as `Query 1`, `Query 2`, etc., labelled with the problem name you typed.

For each one:

- Click the query button.
- Click Run on Both Databases.
- Check the result. `hospital_slow` should show Seq Scan (or a Bitmap with a high cost). `hospital_fast` should show Index Scan or Bitmap Index Scan using your index. The speedup should be clearly above 1x, usually 10x or more.

If `hospital_fast` still shows Seq Scan, the test query isn't hitting the index. Usual reasons:

- You used `LIMIT`.
- The `WHERE` clause doesn't match the indexed columns.
- For partial indexes, the `WHERE` in your query doesn't match the predicate the index was built with.
- For `LIKE 'prefix%'` on text columns, you probably need `text_pattern_ops` in the index definition.

Fix the index or the query and run it again.

### 5. Cross-check in the Index Inspector

Open the Index Inspector tab.

- `hospital_slow`: 0 custom indexes.
- `hospital_fast`: all the ones you created, each labelled with its matching problem name.

## What "done" looks like for Part 1

- 10 validated indexes in the Index Lab (at least 5 regular, 3 composite, 2 partial), each with a problem name, a quote from the business case, a CREATE INDEX, and a test query.
- Every one shows a real speedup in the Performance Lab.
- Index Inspector shows 0 on slow and 10+ on fast.
- Bonus slots filled in if you went further.

That's Part 1. Part 2 (Concurrency) is in `06-concurrency-tasks.md`.
