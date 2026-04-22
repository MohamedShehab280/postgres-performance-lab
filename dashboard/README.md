# Hospital Dashboard - Setup Guide

## Requirements
- Python 3.8+
- PostgreSQL 14+ running locally

## Install dependencies
```
pip install flask psycopg2-binary
```

## Set the password
Open `app.py` and change `BASE["password"]` to your postgres password:
```python
BASE = {
    "host":     "localhost",
    "port":     5432,
    "user":     "postgres",
    "password": "postgres",
}
```

## Run
```
python app.py
```
Open http://localhost:5000.

---

## Database setup (do this first)

### 1. Create hospital_slow
Run `01a-schema-hospital-slow.sql` in pgAdmin. Creates the database and the 9 empty tables.

### 2. Generate data
Connect to `hospital_slow` in pgAdmin, run `02-data-generation.sql`. Takes 5-10 minutes and produces around 6 million rows.

### 3. Clone into hospital_fast
Disconnect from `hospital_slow` (right-click, *Disconnect Database*), connect to `postgres`, and run:
```sql
CREATE DATABASE hospital_fast TEMPLATE hospital_slow;
```
A few seconds. `hospital_fast` now has the same rows as `hospital_slow`, no indexes yet.

---

## Before running the app

| Check | Where |
|---|---|
| hospital_slow: ~6M rows, 0 custom indexes | Index Inspector tab |
| hospital_fast: same row counts | Index Inspector / Overview |
| Performance Lab shows a speedup after you add indexes | Performance Lab tab |

---

## App Tabs

| Tab | What it shows |
|---|---|
| Overview | Row counts on both databases |
| Index Lab | Where you create and justify your indexes |
| Performance Lab | Side-by-side timing and EXPLAIN plans |
| Index Inspector | Custom indexes on each database |
| Concurrency Lab | Double-booking simulation (Part 2) |
| Deadlock Lab | Real deadlock with PostgreSQL's error (Part 3) |
| Backup Lab | Runs pg_dump (Part 4) |
| SQL Sandbox | Type any query, see both databases |
| Tx Visualizer | Step through BEGIN / EXECUTE / COMMIT / ROLLBACK |

---

## Troubleshooting

**`connection refused`** - PostgreSQL isn't running.

**`password authentication failed`** - Wrong password in `app.py`.

**`database does not exist`** - Run the setup steps above.

**Performance Lab shows the same speed on both** - Check Index Inspector. `hospital_slow` should have 0 custom indexes, `hospital_fast` should have yours.

**`source database "hospital_slow" is being accessed by other users`** - Right-click `hospital_slow` in pgAdmin, *Disconnect Database*, close any Query Tool tab pointing at it, then re-run the `CREATE DATABASE ... TEMPLATE` line.

**`database "hospital_fast" already exists`** - Drop and re-clone:
```sql
DROP DATABASE hospital_fast;
CREATE DATABASE hospital_fast TEMPLATE hospital_slow;
```
