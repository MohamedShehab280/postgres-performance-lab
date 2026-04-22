# Hospital Database - Advanced Database Final Project

Two PostgreSQL databases with the same 6 million rows. One has no custom indexes (`hospital_slow`), the other is the one where you add them (`hospital_fast`). A small Flask dashboard runs the same queries against both at once so you can actually see what indexes do.

## Files

| File | What it is |
|---|---|
| `00-student-guide.md` | Walkthrough of every tab in the dashboard. Read after setup. |
| `01a-schema-hospital-slow.sql` | Creates `hospital_slow` and its 9 tables. |
| `02-data-generation.sql` | Inserts ~6M rows. |
| `03-student-tasks.md` | What you actually have to do. |
| `05-business-case.md` | The IT audit report. 15 performance problems are hidden in it. |
| `PROJECT-BRIEF.md` | Overview of the full project. |
| `dashboard/app.py` | The Flask app. |

## What you need before you start

- PostgreSQL 14 or newer (https://www.postgresql.org/download/). Remember the `postgres` password you set during install.
- pgAdmin 4 (ships with the PostgreSQL installer).
- Python 3.8+ (https://www.python.org/downloads/).
- Git.

## After cloning

```bash
git clone https://github.com/<your-user>/<this-repo>.git
cd <this-repo>
pip install flask psycopg2-binary
```

### 1. Create `hospital_slow` and the tables

In pgAdmin, connect to the `postgres` database, open a Query Tool, and run `01a-schema-hospital-slow.sql`. This creates the database and the 9 empty tables.

### 2. Load the data into `hospital_slow`

Switch your pgAdmin connection to `hospital_slow` and run `02-data-generation.sql`. It takes 5-10 minutes. When it's done, check the counts:

```sql
SELECT
    (SELECT COUNT(*) FROM patients)     AS patients,
    (SELECT COUNT(*) FROM appointments) AS appointments,
    (SELECT COUNT(*) FROM lab_results)  AS lab_results,
    (SELECT COUNT(*) FROM billing)      AS billing;
```

You should see around 500K patients, 2M appointments, 1M lab results, 1.2M billing rows.

### 3. Clone it into `hospital_fast`

Instead of running the data generator twice (which gives you similar but not identical rows because of randomness), just copy the whole database. In pgAdmin, right-click `hospital_slow` and pick *Disconnect Database* first, then connect to `postgres` and run:

```sql
CREATE DATABASE hospital_fast TEMPLATE hospital_slow;
```

Takes a few seconds. Now both databases have the exact same rows. Run the COUNT query from step 2 against `hospital_fast` to confirm the numbers match.

If you get `source database "hospital_slow" is being accessed by other users`, you still have a session open to it somewhere. Close any Query Tool tab pointing at it and try again.

(The `pg_dump` / `psql restore` workflow is saved for Part 4.)

### 4. Set your password in the app

Open `dashboard/app.py`, find:

```python
BASE = {
    "host":     "localhost",
    "port":     5432,
    "user":     "postgres",
    "password": "admin",
}
```

Change `"admin"` to whatever password you set during the PostgreSQL install.

### 5. Run the app

```bash
cd dashboard
python app.py
```

Open http://localhost:5000. The Overview tab should load row counts from both databases. If it does, you're ready. Start reading `00-student-guide.md` and `03-student-tasks.md`.

## Things that commonly go wrong

**`connection refused`** - PostgreSQL service isn't running.
- Windows: `net start postgresql-x64-18` (replace 18 with your version).
- macOS: `brew services start postgresql`.
- Linux: `sudo systemctl start postgresql`.

**`password authentication failed`** - The password in `dashboard/app.py` doesn't match the one you set during install. Fix it in `BASE["password"]`.

**`source database "hospital_slow" is being accessed by other users`** - Something is still connected. Right-click `hospital_slow` in pgAdmin, *Disconnect Database*, close any open Query Tool tabs, try again.

**`database "hospital_fast" already exists`** - You ran the clone once already. Drop and redo:
```sql
DROP DATABASE hospital_fast;
CREATE DATABASE hospital_fast TEMPLATE hospital_slow;
```

**Port 5000 is already in use** - Change the last line of `app.py` to `app.run(port=5050)` and use http://localhost:5050.
