"""
Hospital DB — Advanced Database Final Project Dashboard
=======================================================
Two-database comparison app:
  hospital_slow  →  no custom indexes (only PKs)
  hospital_fast  →  student's optimized version (with indexes)

Run:
    pip install flask psycopg2-binary
    python app.py
    Open: http://localhost:5000
"""

from flask import Flask, jsonify, request, render_template_string
import psycopg2
import psycopg2.extras
import psycopg2.errorcodes
import threading
import subprocess
import time
import os

app = Flask(__name__)

# ─────────────────────────────────────────────────────────────────────────────
#  DATABASE CONFIG — Change password if needed
# ─────────────────────────────────────────────────────────────────────────────
BASE = {
    "host":     "localhost",
    "port":     5432,
    "user":     "postgres",
    "password": "admin",      # ← your postgres password
}

DB_SLOW = {**BASE, "dbname": "hospital_slow"}   # no custom indexes
DB_FAST = {**BASE, "dbname": "hospital_fast"}   # student's optimized DB


def get_conn(cfg):
    return psycopg2.connect(**cfg)


def run_query(cfg, sql, params=None):
    """Returns (rows, elapsed_ms, error_message)."""
    try:
        conn = get_conn(cfg)
        conn.autocommit = True
        cur  = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        t0   = time.time()
        if params:
            cur.execute(sql, params)
        else:
            cur.execute(sql)
        ms   = round((time.time() - t0) * 1000, 1)
        rows = [dict(r) for r in cur.fetchall()]
        cur.close(); conn.close()
        return rows, ms, None
    except Exception as e:
        return [], 0, str(e)



def run_explain(cfg, sql, params=None):
    """Returns (plan_text, elapsed_ms, error)."""
    try:
        conn = get_conn(cfg)
        conn.autocommit = True
        cur  = conn.cursor()
        t0   = time.time()
        if params:
            cur.execute("EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT) " + sql, params)
        else:
            cur.execute("EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT) " + sql)
        ms   = round((time.time() - t0) * 1000, 1)
        plan = "\n".join(r[0] for r in cur.fetchall())
        cur.close(); conn.close()
        return plan, ms, None
    except Exception as e:
        return "", 0, str(e)



# ─────────────────────────────────────────────────────────────────────────────
#  PRESET QUERIES FOR PERFORMANCE LAB
# ─────────────────────────────────────────────────────────────────────────────
PRESET_QUERIES = {}  # Removed — queries now come from student Index Lab


# ─────────────────────────────────────────────────────────────────────────────
#  API: PERFORMANCE RUN — run any SQL on both DBs simultaneously
# ─────────────────────────────────────────────────────────────────────────────
@app.route("/api/performance/run", methods=["POST"])
def api_performance_run():
    data  = request.get_json() or {}
    sql   = data.get("sql",   "").strip()
    if not sql:
        return jsonify({"ok": False, "error": "No SQL provided."})
    # Safety: SELECT only
    if not sql.lower().lstrip().startswith("select"):
        return jsonify({"ok": False, "error": "Only SELECT queries are allowed."})

    results = {}
    def _run(cfg, key):
        plan, ms, err = run_explain(cfg, sql)
        scan = ""
        for s in ["Index Only Scan","Bitmap Heap Scan","Index Scan","Seq Scan"]:
            if s in plan:
                scan = s; break
        results[key] = {"ms": ms, "plan": plan, "err": err, "scan_type": scan}

    import threading as _t
    ta = _t.Thread(target=_run, args=(DB_SLOW, "slow"))
    tb = _t.Thread(target=_run, args=(DB_FAST, "fast"))
    ta.start(); tb.start(); ta.join(); tb.join()

    slow_ms = results["slow"]["ms"]
    fast_ms = results["fast"]["ms"]
    speedup = round(slow_ms / fast_ms, 1) if fast_ms > 0 else None
    return jsonify({"ok": True, "slow": results["slow"], "fast": results["fast"], "speedup": speedup})

# ─────────────────────────────────────────────────────────────────────────────
#  API: STATS
# ─────────────────────────────────────────────────────────────────────────────
@app.route("/api/stats")
def api_stats():
    sql = """
        SELECT
            (SELECT COUNT(*) FROM patients)     AS patients,
            (SELECT COUNT(*) FROM doctors)      AS doctors,
            (SELECT COUNT(*) FROM appointments) AS appointments,
            (SELECT COUNT(*) FROM lab_results)  AS lab_results,
            (SELECT COUNT(*) FROM billing)      AS billing,
            (SELECT COUNT(*) FROM billing WHERE paid_at IS NULL) AS unpaid
    """
    slow_rows, slow_ms, slow_err = run_query(DB_SLOW, sql)
    fast_rows, fast_ms, fast_err = run_query(DB_FAST, sql)
    return jsonify({
        "slow": slow_rows[0] if slow_rows else None,
        "fast": fast_rows[0] if fast_rows else None,
        "slow_err": slow_err, "fast_err": fast_err
    })


# ─────────────────────────────────────────────────────────────────────────────
#  API: PERFORMANCE COMPARISON
# ─────────────────────────────────────────────────────────────────────────────
@app.route("/api/compare/<qid>")
def api_compare(qid):
    if qid not in PRESET_QUERIES:
        return jsonify({"error": "Unknown query id"}), 400

    q    = PRESET_QUERIES[qid]
    sql  = q["sql"]

    results = {}

    def run_both():
        # Run in background threads simultaneously
        slow_result = {}
        fast_result = {}

        def do_slow():
            plan, ms, err = run_explain(DB_SLOW, sql)
            slow_result.update({"plan": plan, "ms": ms, "err": err})

        def do_fast():
            plan, ms, err = run_explain(DB_FAST, sql)
            fast_result.update({"plan": plan, "ms": ms, "err": err})

        t1 = threading.Thread(target=do_slow)
        t2 = threading.Thread(target=do_fast)
        t1.start(); t2.start()
        t1.join();  t2.join()
        results["slow"] = slow_result
        results["fast"] = fast_result

    run_both()

    slow = results["slow"]
    fast = results["fast"]

    speedup = None
    if fast["ms"] and fast["ms"] > 0 and slow["ms"]:
        speedup = round(slow["ms"] / fast["ms"], 1)

    return jsonify({
        "label":       q["label"],
        "description": q["description"],
        "index_hint":  q["index_hint"],
        "slow": {"ms": slow["ms"], "plan": slow["plan"], "err": slow["err"]},
        "fast": {"ms": fast["ms"], "plan": fast["plan"], "err": fast["err"]},
        "speedup": speedup
    })


# ─────────────────────────────────────────────────────────────────────────────
#  API: CONCURRENT BOOKING SIMULATION
# ─────────────────────────────────────────────────────────────────────────────
@app.route("/api/concurrent-book", methods=["POST"])
def api_concurrent_book():
    """
    Fires two simultaneous booking attempts for the same doctor + time slot.
    One should succeed, one should fail (or both succeed if no protection).
    Returns both results including PostgreSQL error messages.
    """
    data = request.get_json() or {}
    db_key = data.get("db", "slow")
    cfg = DB_SLOW if db_key == "slow" else DB_FAST

    # Pick a real doctor and a future time slot
    slot_time = "2026-12-01 10:00:00"
    doctor_id = 1
    bookings = [
        {"patient_id": 1, "name": "Patient A"},
        {"patient_id": 2, "name": "Patient B"},
    ]

    results = [None, None]

    def attempt_booking(index, patient_id, patient_name):
        try:
            conn = get_conn(cfg)
            conn.autocommit = False
            cur  = conn.cursor()

            # Check if slot exists — lock it
            cur.execute("""
                SELECT id FROM appointments
                WHERE doctor_id = %s
                  AND scheduled_at = %s
                  AND status = 'scheduled'
                FOR UPDATE NOWAIT
            """, [doctor_id, slot_time])
            existing = cur.fetchone()

            if existing:
                conn.rollback()
                results[index] = {
                    "patient":  patient_name,
                    "status":   "REJECTED",
                    "reason":   f"Slot already taken (appointment id={existing[0]})",
                    "pg_error": None,
                    "color":    "red"
                }
                return

            time.sleep(0.05)  # small delay so both threads overlap

            cur.execute("""
                INSERT INTO appointments
                    (patient_id, doctor_id, scheduled_at, status)
                VALUES (%s, %s, %s, 'scheduled')
                RETURNING id
            """, [patient_id, doctor_id, slot_time])
            new_id = cur.fetchone()[0]
            conn.commit()
            results[index] = {
                "patient":  patient_name,
                "status":   "SUCCESS",
                "reason":   f"Appointment created (id={new_id})",
                "pg_error": None,
                "color":    "green"
            }

        except psycopg2.errors.LockNotAvailable as e:
            try: conn.rollback()
            except: pass
            results[index] = {
                "patient":  patient_name,
                "status":   "BLOCKED",
                "reason":   "Could not acquire lock — another booking is in progress",
                "pg_error": str(e).strip(),
                "color":    "amber"
            }
        except Exception as e:
            try: conn.rollback()
            except: pass
            results[index] = {
                "patient":  patient_name,
                "status":   "ERROR",
                "reason":   "Database error",
                "pg_error": str(e).strip(),
                "color":    "red"
            }

    # Fire both simultaneously
    t1 = threading.Thread(target=attempt_booking, args=(0, bookings[0]["patient_id"], bookings[0]["name"]))
    t2 = threading.Thread(target=attempt_booking, args=(1, bookings[1]["patient_id"], bookings[1]["name"]))
    t1.start(); t2.start()
    t1.join();  t2.join()

    # Count how many succeeded
    succeeded = sum(1 for r in results if r and r["status"] == "SUCCESS")

    # Clean up the test booking(s) so it can be run again
    try:
        conn = get_conn(cfg)
        conn.autocommit = True
        cur = conn.cursor()
        cur.execute("DELETE FROM appointments WHERE doctor_id=%s AND scheduled_at=%s AND status='scheduled'",
                    [doctor_id, slot_time])
        conn.close()
    except:
        pass

    return jsonify({
        "slot":      f"Doctor #{doctor_id} @ {slot_time}",
        "results":   results,
        "succeeded": succeeded,
        "verdict":   "⚠️ RACE CONDITION — both bookings succeeded!" if succeeded == 2
                     else "✅ Conflict handled correctly — only one booking accepted" if succeeded == 1
                     else "❌ Both bookings failed"
    })


# ─────────────────────────────────────────────────────────────────────────────
#  API: DEADLOCK SIMULATION
# ─────────────────────────────────────────────────────────────────────────────
@app.route("/api/deadlock", methods=["POST"])
def api_deadlock():
    """
    Creates a real deadlock between two database sessions.
    Session 1: locks billing id=1, then tries rooms id=1
    Session 2: locks rooms  id=1, then tries billing id=1
    PostgreSQL detects and kills one — we catch the error and return it.
    """
    data   = request.get_json() or {}
    db_key = data.get("db", "slow")
    cfg    = DB_SLOW if db_key == "slow" else DB_FAST

    log = []
    results = [None, None]

    def session_1():
        try:
            conn = get_conn(cfg)
            conn.autocommit = False
            cur  = conn.cursor()
            log.append("🔵 Session 1: BEGIN")
            cur.execute("UPDATE rooms SET capacity = capacity WHERE id = 1")
            log.append("🔵 Session 1: Locked rooms id=1")
            time.sleep(0.3)   # wait so Session 2 can grab billing
            log.append("🔵 Session 1: Trying to lock billing id=1 …")
            cur.execute("UPDATE billing SET discount = discount WHERE id = 1")
            conn.commit()
            log.append("🔵 Session 1: COMMIT (survived)")
            results[0] = {"session": "Session 1", "outcome": "SURVIVED", "color": "green", "pg_error": None}
        except psycopg2.errors.DeadlockDetected as e:
            try: conn.rollback()
            except: pass
            log.append("🔵 Session 1: ❌ DEADLOCK — rolled back")
            results[0] = {"session": "Session 1", "outcome": "DEADLOCK — rolled back by PostgreSQL",
                          "color": "red", "pg_error": str(e).strip()}
        except Exception as e:
            try: conn.rollback()
            except: pass
            results[0] = {"session": "Session 1", "outcome": "ERROR", "color": "red", "pg_error": str(e).strip()}

    def session_2():
        time.sleep(0.1)  # let session 1 get its lock first
        try:
            conn = get_conn(cfg)
            conn.autocommit = False
            cur  = conn.cursor()
            log.append("🟡 Session 2: BEGIN")
            cur.execute("UPDATE billing SET discount = discount WHERE id = 1")
            log.append("🟡 Session 2: Locked billing id=1")
            time.sleep(0.3)
            log.append("🟡 Session 2: Trying to lock rooms id=1 …")
            cur.execute("UPDATE rooms SET capacity = capacity WHERE id = 1")
            conn.commit()
            log.append("🟡 Session 2: COMMIT (survived)")
            results[1] = {"session": "Session 2", "outcome": "SURVIVED", "color": "green", "pg_error": None}
        except psycopg2.errors.DeadlockDetected as e:
            try: conn.rollback()
            except: pass
            log.append("🟡 Session 2: ❌ DEADLOCK — rolled back")
            results[1] = {"session": "Session 2", "outcome": "DEADLOCK — rolled back by PostgreSQL",
                          "color": "red", "pg_error": str(e).strip()}
        except Exception as e:
            try: conn.rollback()
            except: pass
            results[1] = {"session": "Session 2", "outcome": "ERROR", "color": "red", "pg_error": str(e).strip()}

    t1 = threading.Thread(target=session_1)
    t2 = threading.Thread(target=session_2)
    t1.start(); t2.start()
    t1.join();  t2.join()

    deadlock_occurred = any(r and "DEADLOCK" in r["outcome"] for r in results if r)

    return jsonify({
        "log":              log,
        "results":          results,
        "deadlock_occurred": deadlock_occurred,
        "explanation": (
            "PostgreSQL detected a circular wait: Session 1 held rooms and waited for billing, "
            "while Session 2 held billing and waited for rooms. "
            "PostgreSQL automatically chose one victim and rolled it back."
        ) if deadlock_occurred else "No deadlock detected — try again."
    })


# ─────────────────────────────────────────────────────────────────────────────
#  API: BACKUP
# ─────────────────────────────────────────────────────────────────────────────
@app.route("/api/backup", methods=["POST"])
def api_backup():
    data   = request.get_json() or {}
    db_key = data.get("db", "slow")
    dbname = "hospital_slow" if db_key == "slow" else "hospital_fast"
    outfile = f"C:\\{dbname}_backup.sql"

    pg_bin = r"C:\Program Files\PostgreSQL\18\bin\pg_dump.exe"
    if not os.path.exists(pg_bin):
        # Try to find pg_dump in PATH
        pg_bin = "pg_dump"

    cmd = [pg_bin, "-U", BASE["user"], "-f", outfile, dbname]
    env = {**os.environ, "PGPASSWORD": BASE["password"]}

    try:
        t0 = time.time()
        result = subprocess.run(cmd, env=env, capture_output=True, text=True, timeout=120)
        ms = round((time.time() - t0) * 1000)
        if result.returncode == 0:
            size = os.path.getsize(outfile) if os.path.exists(outfile) else 0
            return jsonify({
                "success": True,
                "file":    outfile,
                "size_mb": round(size / 1024 / 1024, 2),
                "time_ms": ms,
                "message": f"Backup of '{dbname}' completed in {ms}ms → {outfile} ({round(size/1024/1024,2)} MB)"
            })
        else:
            return jsonify({"success": False, "error": result.stderr})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


# ─────────────────────────────────────────────────────────────────────────────
#  API: INDEXES — list current indexes on a DB
# ─────────────────────────────────────────────────────────────────────────────

@app.route("/api/indexes/<db_key>")
def api_indexes(db_key):
    cfg = DB_SLOW if db_key == "slow" else DB_FAST
    sql = """
        SELECT indexname, tablename, indexdef
        FROM pg_indexes
        WHERE schemaname = 'public'
          AND indexname NOT LIKE '%_pkey'
        ORDER BY tablename, indexname
    """
    rows, ms, err = run_query(cfg, sql)
    return jsonify({"indexes": rows, "count": len(rows), "err": err})


# ─────────────────────────────────────────────────────────────────────────────
#  API: CREATE / DROP INDEX — run from within the app
# ─────────────────────────────────────────────────────────────────────────────
@app.route("/api/create-index", methods=["POST"])
def api_create_index():
    data   = request.get_json() or {}
    sql    = data.get("sql", "").strip()
    db_key = data.get("db", "fast")
    cfg    = DB_SLOW if db_key == "slow" else DB_FAST

    if not sql:
        return jsonify({"ok": False, "error": "No SQL provided."})

    lowered = sql.lower().lstrip()
    if not (lowered.startswith("create index") or
            lowered.startswith("create unique index") or
            lowered.startswith("drop index")):
        return jsonify({"ok": False,
                        "error": "Only CREATE INDEX or DROP INDEX statements are allowed here."})
    try:
        conn = get_conn(cfg)
        conn.autocommit = True
        cur  = conn.cursor()
        cur.execute(sql)
        cur.close(); conn.close()
        action = "created" if "create" in lowered else "dropped"
        return jsonify({"ok": True,
                        "message": f"Index {action} successfully on hospital_{db_key}."})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e).strip()})


# ─────────────────────────────────────────────────────────────────────────────
#  API: SQL SANDBOX — run any SQL on both DBs simultaneously
# ─────────────────────────────────────────────────────────────────────────────
@app.route("/api/sandbox", methods=["POST"])
def api_sandbox():
    data = request.get_json() or {}
    sql  = data.get("sql", "").strip()
    dbs  = data.get("dbs", ["slow", "fast"])  # which DBs to run on

    if not sql:
        return jsonify({"error": "No SQL provided"}), 400

    # Safety: block destructive statements
    lowered = sql.lower()
    forbidden = ["drop ", "truncate ", "delete ", "alter ", "create index", "drop index"]
    for f in forbidden:
        if f in lowered:
            return jsonify({"error": f"Blocked: '{f.strip()}' statements are not allowed in the sandbox."}), 400

    results = {}

    def run_on(db_key):
        cfg = DB_SLOW if db_key == "slow" else DB_FAST
        # Try EXPLAIN ANALYZE first
        plan, plan_ms, plan_err = run_explain(cfg, sql)
        # Then run the actual query for results
        rows, query_ms, query_err = run_query(cfg, sql)
        results[db_key] = {
            "ms":        query_ms,
            "plan":      plan if not plan_err else "",
            "plan_ms":   plan_ms,
            "rows":      rows[:20],   # cap at 20 for display
            "row_count": len(rows),
            "err":       query_err or plan_err
        }

    threads = []
    for db_key in dbs:
        t = threading.Thread(target=run_on, args=(db_key,))
        threads.append(t)
        t.start()
    for t in threads:
        t.join()

    speedup = None
    if "slow" in results and "fast" in results:
        s_ms = results["slow"]["ms"]
        f_ms = results["fast"]["ms"]
        if f_ms and f_ms > 0 and s_ms:
            speedup = round(s_ms / f_ms, 1)

    return jsonify({"results": results, "speedup": speedup})


# ─────────────────────────────────────────────────────────────────────────────
#  API: TRANSACTION VISUALIZER — persistent session-based transactions
# ─────────────────────────────────────────────────────────────────────────────
txn_sessions  = {}   # {session_id: {conn, cur, db, log, status}}
txn_lock      = threading.Lock()


def _get_txn(sid):
    with txn_lock:
        return txn_sessions.get(sid)


def _close_txn(sid):
    with txn_lock:
        s = txn_sessions.pop(sid, None)
    if s:
        try: s["conn"].close()
        except: pass


@app.route("/api/txn/begin", methods=["POST"])
def txn_begin():
    data   = request.get_json() or {}
    sid    = data.get("session_id")
    db_key = data.get("db", "slow")
    iso    = data.get("isolation", "READ COMMITTED")
    cfg    = DB_SLOW if db_key == "slow" else DB_FAST

    # Close any existing session with this ID
    _close_txn(sid)

    try:
        conn = get_conn(cfg)
        conn.autocommit = False
        cur  = conn.cursor()
        cur.execute(f"SET TRANSACTION ISOLATION LEVEL {iso}")
        with txn_lock:
            txn_sessions[sid] = {
                "conn": conn, "cur": cur,
                "db": db_key, "iso": iso,
                "log": [f"BEGIN ({iso})"],
                "status": "open"
            }
        return jsonify({"ok": True, "message": f"Transaction started on hospital_{db_key} ({iso})",
                        "log": [f"BEGIN ({iso})"], "status": "open"})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)})


@app.route("/api/txn/execute", methods=["POST"])
def txn_execute():
    data = request.get_json() or {}
    sid  = data.get("session_id")
    sql  = data.get("sql", "").strip()

    s = _get_txn(sid)
    if not s:
        return jsonify({"ok": False, "error": "No open transaction. Click BEGIN first."})
    if s["status"] != "open":
        return jsonify({"ok": False, "error": f"Transaction is already {s['status']}."})

    try:
        cur = s["cur"]
        cur.execute(sql)
        try:
            rows = cur.fetchall()
            row_str = f"{len(rows)} row(s) returned" if rows else "OK"
            preview = [list(r) for r in rows[:10]]
        except:
            row_str = f"{cur.rowcount} row(s) affected"
            preview = []
        msg = f"→ {sql[:60]}{'…' if len(sql)>60 else ''} [{row_str}]"
        s["log"].append(msg)
        return jsonify({"ok": True, "message": msg, "preview": preview,
                        "log": s["log"], "status": s["status"]})
    except Exception as e:
        err_msg = str(e).strip()
        s["log"].append(f"❌ ERROR: {err_msg}")
        # Transaction is now aborted — must rollback before doing anything else
        s["status"] = "error"
        return jsonify({"ok": False, "error": err_msg, "log": s["log"], "status": "error"})


@app.route("/api/txn/commit", methods=["POST"])
def txn_commit():
    data = request.get_json() or {}
    sid  = data.get("session_id")
    s    = _get_txn(sid)
    if not s:
        return jsonify({"ok": False, "error": "No open transaction."})
    try:
        s["conn"].commit()
        s["log"].append("✅ COMMIT — changes are now permanent")
        s["status"] = "committed"
        log = s["log"][:]
        _close_txn(sid)
        return jsonify({"ok": True, "message": "COMMIT successful", "log": log, "status": "committed"})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)})


@app.route("/api/txn/rollback", methods=["POST"])
def txn_rollback():
    data = request.get_json() or {}
    sid  = data.get("session_id")
    s    = _get_txn(sid)
    if not s:
        return jsonify({"ok": False, "error": "No open transaction."})
    try:
        s["conn"].rollback()
        s["log"].append("↩️ ROLLBACK — all changes undone")
        s["status"] = "rolled_back"
        log = s["log"][:]
        _close_txn(sid)
        return jsonify({"ok": True, "message": "ROLLBACK complete", "log": log, "status": "rolled_back"})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)})


@app.route("/api/txn/status", methods=["GET"])
def txn_status():
    sid = request.args.get("session_id")
    s   = _get_txn(sid)
    if not s:
        return jsonify({"status": "idle", "log": []})
    return jsonify({"status": s["status"], "db": s["db"], "iso": s["iso"], "log": s["log"]})


# ─────────────────────────────────────────────────────────────────────────────
#  API: INDEX LAB — create index + validate via EXPLAIN on hospital_fast
# ─────────────────────────────────────────────────────────────────────────────
@app.route("/api/index-lab/run", methods=["POST"])
def api_index_lab_run():
    data       = request.get_json() or {}
    create_sql = data.get("create_sql", "").strip()
    test_query = data.get("test_query", "").strip()
    index_name = data.get("index_name", "").strip()

    if not create_sql:
        return jsonify({"ok": False, "error": "No CREATE INDEX statement provided."})
    if not test_query:
        return jsonify({"ok": False, "error": "No test query provided."})

    # Only allow CREATE INDEX / DROP INDEX
    lowered = create_sql.lower().lstrip()
    if not (lowered.startswith("create index") or lowered.startswith("create unique index")):
        return jsonify({"ok": False, "error": "Only CREATE INDEX statements are allowed here."})

    result = {"ok": True, "index_created": False, "create_error": None,
              "plan": "", "ms": 0, "scan_type": "", "index_used": False,
              "rows_returned": 0, "query_error": None}

    # Step 1: Create the index on hospital_fast
    try:
        conn = get_conn(DB_FAST)
        conn.autocommit = True
        cur  = conn.cursor()
        # Inject IF NOT EXISTS so re-runs don’t fail
        safe_sql = create_sql
        if "if not exists" not in lowered:
            safe_sql = safe_sql.replace(
                next(k for k in ["CREATE UNIQUE INDEX", "CREATE INDEX"]
                     if k.lower() in lowered),
                ("CREATE UNIQUE INDEX IF NOT EXISTS" if "unique" in lowered
                 else "CREATE INDEX IF NOT EXISTS"),
                1
            )
        cur.execute(safe_sql)
        # Auto-run ANALYZE on the indexed table so planner stats are fresh
        import re as _re
        _m = _re.search(r'\bON\s+(\w+)\s*\(', safe_sql, _re.IGNORECASE)
        if _m:
            cur.execute(f'ANALYZE {_m.group(1)}')
        cur.close(); conn.close()
        result["index_created"] = True
    except Exception as e:
        result["ok"]            = False
        result["create_error"]  = str(e).strip()
        return jsonify(result)

    # Step 2: EXPLAIN ANALYZE the test query on hospital_fast
    plan, ms, err = run_explain(DB_FAST, test_query)
    result["ms"]  = ms

    if err:
        result["query_error"] = err
        return jsonify(result)

    result["plan"] = plan

    # Detect scan type
    for scan in ["Index Only Scan", "Bitmap Heap Scan", "Index Scan", "Seq Scan"]:
        if scan in plan:
            result["scan_type"] = scan
            break

    # Check if the student’s index name appears in the plan
    result["index_used"] = bool(index_name and index_name.lower() in plan.lower())

    # Row count
    rows, _, _ = run_query(DB_FAST, test_query)
    result["rows_returned"] = len(rows)

    return jsonify(result)


# ─────────────────────────────────────────────────────────────────────────────
#  HTML FRONTEND
# ─────────────────────────────────────────────────────────────────────────────
HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Hospital DB — Advanced Database Final Project</title>
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap');

*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}

:root{
  --bg:#070d1b;
  --bg2:#0c1527;
  --surface:#111e35;
  --surface2:#162040;
  --border:#1d2d4a;
  --border2:#233660;
  --slow:#ef4444;
  --fast:#10b981;
  --accent:#3b82f6;
  --amber:#f59e0b;
  --purple:#a855f7;
  --text:#e2e8f0;
  --muted:#64748b;
  --muted2:#94a3b8;
  --r:14px;
  --r-sm:8px;
  --mono:'JetBrains Mono',monospace;
}

body{font-family:'Inter',sans-serif;background:var(--bg);color:var(--text);min-height:100vh}

/* ── NAV ── */
nav{
  background:linear-gradient(135deg,#0f2044 0%,#071024 100%);
  border-bottom:1px solid var(--border);
  padding:0 28px;
  display:flex;align-items:center;gap:0;
  position:sticky;top:0;z-index:100;
}
.nav-brand{
  font-size:1rem;font-weight:800;letter-spacing:-0.5px;
  padding:18px 24px 18px 0;
  border-right:1px solid var(--border);
  margin-right:8px;
  white-space:nowrap;
}
.nav-brand span{color:var(--accent)}
.nav-tabs{display:flex;gap:2px;flex:1;overflow-x:auto;scrollbar-width:none}
.nav-tabs::-webkit-scrollbar{display:none}
.tab{
  padding:18px 18px;font-size:0.8rem;font-weight:600;
  color:var(--muted);cursor:pointer;white-space:nowrap;
  border-bottom:2px solid transparent;
  transition:color .2s,border-color .2s;
}
.tab:hover{color:var(--text)}
.tab.active{color:var(--accent);border-bottom-color:var(--accent)}
.nav-badge{
  font-size:0.68rem;font-weight:700;padding:3px 10px;
  border-radius:999px;
  background:rgba(59,130,246,0.12);
  border:1px solid rgba(59,130,246,0.25);
  color:var(--accent);
  margin-left:auto;white-space:nowrap;
}

/* ── PAGES ── */
.page{display:none;padding:28px 24px;max-width:1380px;margin:0 auto}
.page.active{display:block}

/* ── SECTION TITLE ── */
.sec{
  font-size:0.7rem;font-weight:700;letter-spacing:.1em;
  text-transform:uppercase;color:var(--muted);
  margin-bottom:16px;padding-bottom:10px;
  border-bottom:1px solid var(--border);
}

/* ── GRID ── */
.grid-2{display:grid;grid-template-columns:1fr 1fr;gap:18px}
.grid-3{display:grid;grid-template-columns:repeat(3,1fr);gap:14px}
.grid-auto{display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:14px}
@media(max-width:900px){.grid-2,.grid-3{grid-template-columns:1fr}}

/* ── CARD ── */
.card{
  background:var(--surface);
  border:1px solid var(--border);
  border-radius:var(--r);
  padding:22px;
}
.card-title{font-size:.85rem;font-weight:700;margin-bottom:4px}
.card-sub{font-size:.72rem;color:var(--muted);margin-bottom:16px;line-height:1.5}

/* ── STAT MINI ── */
.stat-mini{
  background:var(--surface);border:1px solid var(--border);border-radius:var(--r);
  padding:18px 20px;transition:border-color .2s,transform .2s;
}
.stat-mini:hover{border-color:var(--border2);transform:translateY(-2px)}
.stat-mini .lbl{font-size:.68rem;font-weight:600;color:var(--muted);text-transform:uppercase;letter-spacing:.07em;margin-bottom:8px}
.stat-mini .val{font-size:2rem;font-weight:800}
.stat-mini .sub{font-size:.68rem;color:var(--muted);margin-top:4px}
.c-blue{color:var(--accent)}
.c-green{color:var(--fast)}
.c-red{color:var(--slow)}
.c-amber{color:var(--amber)}
.c-purple{color:var(--purple)}

/* ── DB LABELS ── */
.db-label{
  display:inline-flex;align-items:center;gap:6px;
  font-size:.7rem;font-weight:700;letter-spacing:.05em;text-transform:uppercase;
  padding:4px 10px;border-radius:999px;
}
.db-slow{background:rgba(239,68,68,.12);border:1px solid rgba(239,68,68,.3);color:var(--slow)}
.db-fast{background:rgba(16,185,129,.12);border:1px solid rgba(16,185,129,.3);color:var(--fast)}
.dot{width:6px;height:6px;border-radius:50%;background:currentColor}

/* ── COMPARE PANEL ── */
.compare-grid{display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-top:16px}
.compare-side{
  background:var(--bg2);border:1px solid var(--border);
  border-radius:var(--r);padding:20px;
}
.compare-side.slow-side{border-color:rgba(239,68,68,.25)}
.compare-side.fast-side{border-color:rgba(16,185,129,.25)}
.timing-big{font-size:2.8rem;font-weight:800;line-height:1;margin:12px 0 4px}
.timing-unit{font-size:.75rem;color:var(--muted);font-weight:500}

/* ── SPEED BAR ── */
.bar-row{margin-top:14px}
.bar-label{font-size:.68rem;color:var(--muted);margin-bottom:5px;display:flex;justify-content:space-between}
.bar-track{height:8px;background:rgba(255,255,255,.06);border-radius:999px;overflow:hidden}
.bar-fill{height:100%;border-radius:999px;transition:width 1s cubic-bezier(.16,1,.3,1)}
.bar-slow .bar-fill{background:var(--slow)}
.bar-fast .bar-fill{background:var(--fast)}

/* ── SPEEDUP BADGE ── */
.speedup-badge{
  text-align:center;padding:16px;margin-top:16px;
  background:linear-gradient(135deg,rgba(16,185,129,.08),rgba(59,130,246,.08));
  border:1px solid rgba(16,185,129,.2);border-radius:var(--r-sm);
}
.speedup-num{font-size:2.5rem;font-weight:800;color:var(--fast)}
.speedup-lbl{font-size:.72rem;color:var(--muted);margin-top:2px}

/* ── QUERY SELECTOR ── */
.q-selector{display:flex;gap:10px;flex-wrap:wrap;margin-bottom:20px}
.q-btn{
  padding:10px 18px;border-radius:var(--r-sm);border:1px solid var(--border);
  background:var(--surface);color:var(--muted);font-size:.8rem;font-weight:600;
  cursor:pointer;transition:all .2s;font-family:inherit;
}
.q-btn:hover{border-color:var(--accent);color:var(--text)}
.q-btn.active{background:rgba(59,130,246,.12);border-color:var(--accent);color:var(--accent)}
.q-desc{
  background:rgba(59,130,246,.06);border:1px solid rgba(59,130,246,.15);
  border-radius:var(--r-sm);padding:12px 16px;margin-bottom:16px;
  font-size:.78rem;color:var(--muted2);line-height:1.6;
}
.q-hint{
  font-family:var(--mono);font-size:.72rem;color:var(--accent);
  margin-top:6px;
}

/* ── TERMINAL / EXPLAIN ── */
pre,code{font-family:var(--mono)}
.terminal{
  background:#030810;border:1px solid var(--border);border-radius:var(--r-sm);
  padding:14px 16px;font-size:.7rem;color:#94a3b8;
  overflow-x:auto;overflow-y:auto;max-height:260px;
  white-space:pre-wrap;line-height:1.6;
}
.terminal.tall{max-height:380px}

/* ── BUTTONS ── */
.btn{
  display:inline-flex;align-items:center;gap:8px;
  padding:10px 20px;border-radius:var(--r-sm);
  font-size:.82rem;font-weight:700;cursor:pointer;
  border:none;font-family:inherit;transition:all .2s;
}
.btn-primary{background:var(--accent);color:#fff}
.btn-primary:hover{opacity:.85}
.btn-danger{background:var(--slow);color:#fff}
.btn-danger:hover{opacity:.85}
.btn-success{background:var(--fast);color:#fff}
.btn-success:hover{opacity:.85}
.btn-ghost{background:transparent;border:1px solid var(--border);color:var(--muted2)}
.btn-ghost:hover{border-color:var(--text);color:var(--text)}
.btn:disabled{opacity:.4;cursor:not-allowed}
.btn-group{display:flex;gap:10px;flex-wrap:wrap;margin-bottom:20px;align-items:center}

/* ── RESULT BOX ── */
.result-box{
  border-radius:var(--r-sm);padding:16px 20px;
  font-size:.82rem;line-height:1.6;
  margin-top:14px;
}
.result-success{background:rgba(16,185,129,.08);border:1px solid rgba(16,185,129,.25);color:#6ee7b7}
.result-error  {background:rgba(239,68,68,.08); border:1px solid rgba(239,68,68,.25); color:#fca5a5}
.result-warn   {background:rgba(245,158,11,.08);border:1px solid rgba(245,158,11,.25);color:#fcd34d}
.result-info   {background:rgba(59,130,246,.08);border:1px solid rgba(59,130,246,.2); color:#93c5fd}

/* ── SESSION CARDS ── */
.session-grid{display:grid;grid-template-columns:1fr 1fr;gap:14px;margin-top:16px}
.session-card{
  border-radius:var(--r-sm);padding:18px;
  background:var(--bg2);border:1px solid var(--border);
}
.session-header{display:flex;align-items:center;justify-content:space-between;margin-bottom:10px}
.session-name{font-size:.8rem;font-weight:700}
.outcome-badge{
  font-size:.68rem;font-weight:700;padding:3px 10px;border-radius:999px;
}
.badge-success{background:rgba(16,185,129,.15);color:var(--fast)}
.badge-error  {background:rgba(239,68,68,.15);  color:var(--slow)}
.badge-warn   {background:rgba(245,158,11,.15); color:var(--amber)}
.pg-err{
  margin-top:10px;font-family:var(--mono);font-size:.68rem;
  color:#fca5a5;background:rgba(239,68,68,.06);
  border:1px solid rgba(239,68,68,.2);border-radius:6px;
  padding:10px;white-space:pre-wrap;
}

/* ── LOG ── */
.log-box{
  background:#030810;border:1px solid var(--border);border-radius:var(--r-sm);
  padding:14px;max-height:200px;overflow-y:auto;
  font-family:var(--mono);font-size:.72rem;color:#94a3b8;line-height:1.8;
}

/* ── INDEX TABLE ── */
.idx-table{width:100%;border-collapse:collapse;font-size:.76rem}
.idx-table th{
  text-align:left;padding:8px 10px;font-size:.65rem;font-weight:700;
  text-transform:uppercase;letter-spacing:.07em;color:var(--muted);
  border-bottom:1px solid var(--border);
}
.idx-table td{padding:8px 10px;border-bottom:1px solid rgba(29,45,74,.5);vertical-align:top}
.idx-table tr:last-child td{border-bottom:none}
.idx-table tr:hover td{background:rgba(59,130,246,.04)}
.idx-name{color:var(--accent);font-family:var(--mono)}
.idx-table-name{color:var(--muted2)}
.idx-def{font-family:var(--mono);font-size:.65rem;color:var(--muted);word-break:break-all}

/* ── BACKUP ── */
.backup-status{
  padding:14px 18px;border-radius:var(--r-sm);margin-top:14px;
  font-family:var(--mono);font-size:.75rem;line-height:1.7;
}

/* ── VERDICT ── */
.verdict{
  text-align:center;font-size:1.1rem;font-weight:800;
  padding:20px;border-radius:var(--r);margin-top:16px;
}
.verdict-ok  {background:rgba(16,185,129,.08);border:1px solid rgba(16,185,129,.25);color:var(--fast)}
.verdict-warn{background:rgba(245,158,11,.08);border:1px solid rgba(245,158,11,.25);color:var(--amber)}
.verdict-bad {background:rgba(239,68,68,.08); border:1px solid rgba(239,68,68,.25); color:var(--slow)}

/* ── DB TOGGLE ── */
.db-toggle{display:flex;gap:8px;margin-bottom:18px}
.db-toggle-btn{
  padding:8px 16px;border-radius:var(--r-sm);font-size:.75rem;font-weight:700;
  cursor:pointer;border:1px solid var(--border);background:var(--surface);
  color:var(--muted);font-family:inherit;transition:all .2s;
}
.db-toggle-btn.active-slow{background:rgba(239,68,68,.12);border-color:rgba(239,68,68,.35);color:var(--slow)}
.db-toggle-btn.active-fast{background:rgba(16,185,129,.12);border-color:rgba(16,185,129,.35);color:var(--fast)}

/* ── SPINNER ── */
.spin{display:inline-block;width:14px;height:14px;border:2px solid currentColor;
      border-top-color:transparent;border-radius:50%;animation:spin .7s linear infinite}
@keyframes spin{to{transform:rotate(360deg)}}

/* ── SCROLLBAR ── */
::-webkit-scrollbar{width:6px;height:6px}
::-webkit-scrollbar-track{background:transparent}
::-webkit-scrollbar-thumb{background:var(--border2);border-radius:3px}
</style>
</head>
<body>

<nav>
  <div class="nav-brand">🏥 Hospital<span>DB</span></div>
  <div class="nav-tabs">
    <div class="tab active" data-page="overview">📊 Overview</div>
    <div class="tab" data-page="indexlab">🧪 Index Lab</div>
    <div class="tab" data-page="performance">⚡ Performance Lab</div>
    <div class="tab" data-page="indexes">🗂 Index Inspector</div>
    <div class="tab" data-page="concurrency">🔀 Concurrency Lab</div>
    <div class="tab" data-page="deadlock">💥 Deadlock Lab</div>
    <div class="tab" data-page="backup">💾 Backup Lab</div>
    <div class="tab" data-page="sandbox">🔬 SQL Sandbox</div>
    <div class="tab" data-page="txn">📋 Tx Visualizer</div>
  </div>
  <div class="nav-badge">Advanced Database — Final Project</div>
</nav>

<!-- ══════════════════════════════════════════════════════ PAGE: OVERVIEW ══ -->
<div id="page-overview" class="page active">
  <div class="sec">Database Overview</div>
  <p style="font-size:.8rem;color:var(--muted);margin-bottom:20px">
    Both databases must have the same data. The only difference: <b style="color:var(--slow)">hospital_slow</b> has no custom indexes.
    <b style="color:var(--fast)">hospital_fast</b> has the student's optimized indexes.
  </p>
  <div class="grid-2" style="margin-bottom:28px">
    <div class="card">
      <div style="display:flex;align-items:center;gap:10px;margin-bottom:16px">
        <span class="db-label db-slow"><span class="dot"></span>hospital_slow</span>
        <span style="font-size:.72rem;color:var(--muted)">no custom indexes</span>
      </div>
      <div id="slow-stats"><div style="color:var(--muted);font-size:.8rem">Loading…</div></div>
    </div>
    <div class="card">
      <div style="display:flex;align-items:center;gap:10px;margin-bottom:16px">
        <span class="db-label db-fast"><span class="dot"></span>hospital_fast</span>
        <span style="font-size:.72rem;color:var(--muted)">student's optimized DB</span>
      </div>
      <div id="fast-stats"><div style="color:var(--muted);font-size:.8rem">Loading…</div></div>
    </div>
  </div>
  <div class="result-info" style="font-size:.78rem;line-height:1.7">
    <b>How to set up both databases:</b><br>
    1. Run <code>01-schema-setup.sql</code> twice — once creating <code>hospital_slow</code>, once creating <code>hospital_fast</code><br>
    2. Run <code>02-data-generation.sql</code> on both databases (same data, same volume)<br>
    3. Add your optimized indexes <b>only</b> on <code>hospital_fast</code><br>
    4. Check <b>Index Inspector</b> tab to verify: <code>hospital_slow</code> should show 0 custom indexes, <code>hospital_fast</code> should show 3+
  </div>
</div>

<!-- ══════════════════════════════════════════════════════ PAGE: PERFORMANCE ══ -->
<div id="page-performance" class="page">
  <div class="sec">⚡ Performance Lab — Your Index Queries vs Baseline</div>

  <div class="result-info" style="font-size:.78rem;margin-bottom:20px;line-height:1.8">
    Select a query below to compare its performance on <b style="color:var(--slow)">hospital_slow</b> (no indexes) vs
    <b style="color:var(--fast)">hospital_fast</b> (your indexes).
    <br><span style="color:var(--amber)">Go to Index Lab first — create and validate your queries, then come back here.</span>
  </div>

  <div class="q-selector" id="perf-selector"></div>

  <div id="perf-desc-box" style="display:none">
    <div class="q-desc" id="perf-q-desc"></div>
    <div class="btn-group" style="margin-top:14px">
      <button class="btn btn-primary" id="btn-perf-run" onclick="runSelectedPerf()">▶ Run on Both Databases</button>
      <span id="perf-run-status" style="font-size:.75rem;color:var(--muted)"></span>
    </div>
    <div class="compare-grid" id="perf-compare-grid" style="display:none;margin-top:16px">
      <div class="compare-side slow-side">
        <div class="db-label db-slow"><span class="dot"></span>hospital_slow</div>
        <div class="timing-big c-red" id="perf-slow-time">–</div>
        <div class="timing-unit" id="perf-slow-scan">milliseconds</div>
        <div class="bar-row bar-slow">
          <div class="bar-track"><div class="bar-fill" id="perf-slow-bar" style="width:0%"></div></div>
        </div>
      </div>
      <div class="compare-side fast-side">
        <div class="db-label db-fast"><span class="dot"></span>hospital_fast</div>
        <div class="timing-big c-green" id="perf-fast-time">–</div>
        <div class="timing-unit" id="perf-fast-scan">milliseconds</div>
        <div class="bar-row bar-fast">
          <div class="bar-track"><div class="bar-fill" id="perf-fast-bar" style="width:0%"></div></div>
        </div>
      </div>
    </div>
    <div id="perf-speedup-area" style="display:none">
      <div class="speedup-badge">
        <div class="speedup-num" id="perf-speedup-num">–</div>
        <div class="speedup-lbl">× faster with your index</div>
      </div>
    </div>
    <div class="grid-2" style="margin-top:20px;display:none" id="perf-plan-grid">
      <div>
        <div class="sec" style="margin-bottom:8px">EXPLAIN ANALYZE — hospital_slow</div>
        <div class="terminal tall" id="perf-slow-plan">Run a query to see the plan…</div>
      </div>
      <div>
        <div class="sec" style="margin-bottom:8px">EXPLAIN ANALYZE — hospital_fast</div>
        <div class="terminal tall" id="perf-fast-plan">Run a query to see the plan…</div>
      </div>
    </div>
  </div>
</div>

<!-- ══════════════════════════════════════════════════════ PAGE: CONCURRENCY ══ -->
<div id="page-concurrency" class="page">
  <div class="sec">Concurrency Lab — Double Booking Simulation</div>

  <div class="grid-2" style="margin-bottom:24px">
    <div class="card">
      <div class="card-title">🏥 What happens here?</div>
      <div class="card-sub">
        Two patients try to book the exact same doctor at the exact same time slot.
        Only one should succeed. This button fires <b>two simultaneous database requests</b>
        — if there's no protection, both succeed (a real data bug).
        If the transaction is designed correctly, one will be rejected.
      </div>
      <div class="card-sub" style="color:var(--amber)">
        <b>Target:</b> Doctor #1 @ 2026-12-01 10:00 AM
      </div>
    </div>
    <div class="card">
      <div class="card-title">📋 What to look for</div>
      <div class="card-sub" style="line-height:1.8">
        ✅ <b>Correct</b> — One booking succeeds, one is rejected or blocked<br>
        ⚠️ <b>Bug</b> — Both bookings succeed → double booking<br>
        💬 <b>PostgreSQL error</b> shown in the result cards below<br>
        🔔 The actual <code>psycopg2</code> / PostgreSQL message is displayed as-is
      </div>
    </div>
  </div>

  <div class="card-title" style="margin-bottom:12px">Test on which database?</div>
  <div class="db-toggle">
    <button class="db-toggle-btn active-slow" id="conc-slow-btn" onclick="setConcDb('slow')">
      🔴 hospital_slow
    </button>
    <button class="db-toggle-btn" id="conc-fast-btn" onclick="setConcDb('fast')">
      🟢 hospital_fast
    </button>
  </div>

  <div class="btn-group">
    <button class="btn btn-danger" id="btn-book" onclick="runConcurrent()">
      🚦 Simulate Double Booking
    </button>
    <span id="conc-status" style="font-size:.75rem;color:var(--muted)"></span>
  </div>

  <div id="conc-result" style="display:none">
    <div class="session-grid" id="conc-sessions"></div>
    <div class="verdict" id="conc-verdict"></div>
  </div>
</div>

<!-- ══════════════════════════════════════════════════════ PAGE: DEADLOCK ══ -->
<div id="page-deadlock" class="page">
  <div class="sec">Deadlock Lab</div>

  <div class="grid-2" style="margin-bottom:24px">
    <div class="card">
      <div class="card-title">💥 How the deadlock is triggered</div>
      <div class="card-sub" style="font-family:var(--mono);font-size:.72rem;line-height:2">
        Session 1: LOCK rooms id=1  →  wait for billing id=1<br>
        Session 2: LOCK billing id=1 →  wait for rooms id=1<br>
        <br>
        Circular dependency → PostgreSQL detects → kills one session
      </div>
    </div>
    <div class="card">
      <div class="card-title">📋 What to look for</div>
      <div class="card-sub" style="line-height:1.8">
        💬 <b>Real PostgreSQL error</b> message: <br>
        <code style="color:var(--slow);font-size:.7rem">ERROR: deadlock detected<br>DETAIL: Process N waits for ShareLock…</code><br><br>
        ✅ One session survives, one is rolled back automatically<br>
        📜 The event log shows the sequence of locks
      </div>
    </div>
  </div>

  <div class="card-title" style="margin-bottom:12px">Test on which database?</div>
  <div class="db-toggle">
    <button class="db-toggle-btn active-slow" id="dl-slow-btn" onclick="setDlDb('slow')">🔴 hospital_slow</button>
    <button class="db-toggle-btn" id="dl-fast-btn" onclick="setDlDb('fast')">🟢 hospital_fast</button>
  </div>

  <div class="btn-group">
    <button class="btn btn-danger" id="btn-deadlock" onclick="runDeadlock()">💥 Trigger Deadlock</button>
    <span id="dl-status" style="font-size:.75rem;color:var(--muted)"></span>
  </div>

  <div id="dl-result" style="display:none">
    <div class="sec" style="margin-bottom:8px">Event Log</div>
    <div class="log-box" id="dl-log"></div>

    <div class="session-grid" style="margin-top:16px" id="dl-sessions"></div>

    <div class="result-box result-info" style="margin-top:16px" id="dl-explanation"></div>
  </div>
</div>

<!-- ══════════════════════════════════════════════════════ PAGE: INDEXES ══ -->
<div id="page-indexes" class="page">
  <div class="sec">Index Inspector — What Indexes Exist on Each Database?</div>
  <p style="font-size:.78rem;color:var(--muted);margin-bottom:20px">
    <b style="color:var(--slow)">hospital_slow</b> should have 0 custom indexes (only primary keys).
    <b style="color:var(--fast)">hospital_fast</b> should have your 3+ optimized indexes.
    This tab proves the difference.
  </p>

  <div class="grid-2">
    <div class="card">
      <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:16px">
        <span class="db-label db-slow"><span class="dot"></span>hospital_slow</span>
        <button class="btn btn-ghost" style="padding:6px 12px;font-size:.72rem" onclick="loadIndexes('slow')">Refresh</button>
      </div>
      <div id="slow-indexes-count" style="font-size:.75rem;color:var(--muted);margin-bottom:12px">–</div>
      <table class="idx-table"><thead><tr><th>Index</th><th>Table</th><th>Powers</th><th>Definition</th></tr></thead>
        <tbody id="slow-indexes-body"><tr><td colspan="4" style="color:var(--muted)">Click Refresh</td></tr></tbody>
      </table>
    </div>
    <div class="card">
      <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:16px">
        <span class="db-label db-fast"><span class="dot"></span>hospital_fast</span>
        <button class="btn btn-ghost" style="padding:6px 12px;font-size:.72rem" onclick="loadIndexes('fast')">Refresh</button>
      </div>
      <div id="fast-indexes-count" style="font-size:.75rem;color:var(--muted);margin-bottom:12px">–</div>
      <table class="idx-table"><thead><tr><th>Index</th><th>Table</th><th>Powers</th><th>Definition</th></tr></thead>
        <tbody id="fast-indexes-body"><tr><td colspan="4" style="color:var(--muted)">Click Refresh</td></tr></tbody>
      </table>
    </div>
  </div>

  <!-- ── Create / Drop Index panel ── -->
  <div class="card" style="margin-top:20px">
    <div class="sec" style="margin-bottom:14px">➕ Create or Drop an Index</div>
    <div style="font-size:.75rem;color:var(--muted);margin-bottom:14px;line-height:1.7">
      Type a <code>CREATE INDEX</code> or <code>DROP INDEX</code> statement and run it directly against
      either database. The table above will refresh automatically to show the result.
    </div>

    <!-- DB selector -->
    <div style="display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin-bottom:12px">
      <label style="font-size:.75rem;color:var(--muted)">Target database:</label>
      <button id="idx-slow-btn" class="db-toggle-btn" onclick="setIdxDb('slow')">hospital_slow</button>
      <button id="idx-fast-btn" class="db-toggle-btn active-fast" onclick="setIdxDb('fast')">hospital_fast</button>
    </div>

    <!-- SQL textarea -->
    <textarea id="idx-sql" rows="3" style="
        width:100%;background:#030810;border:1px solid var(--border);
        border-radius:var(--r-sm);padding:12px 14px;color:var(--text);
        font-family:var(--mono);font-size:.75rem;line-height:1.7;resize:vertical;
        transition:border-color .2s;margin-bottom:12px"
      placeholder="CREATE INDEX idx_appointments_doctor ON appointments(doctor_id);
-- or --
DROP INDEX idx_appointments_doctor;"
      onfocus="this.style.borderColor='var(--accent)'"
      onblur="this.style.borderColor='var(--border)'"
    ></textarea>

    <div style="display:flex;align-items:center;gap:12px;flex-wrap:wrap">
      <button class="btn btn-primary" id="btn-idx-run" onclick="runCreateIndex()">▶ Run</button>
      <span id="idx-run-result" style="font-size:.75rem"></span>
    </div>
  </div>
</div>

<!-- ══════════════════════════════════════════════════════ PAGE: BACKUP ══ -->
<div id="page-backup" class="page">
  <div class="sec">Backup Lab</div>

  <div class="grid-2" style="margin-bottom:24px">
    <div class="card">
      <div class="card-title">💾 What this demonstrates</div>
      <div class="card-sub">
        Click the backup button to run a real <code>pg_dump</code> on the selected database.
        The app calls the <code>pg_dump</code> binary, shows the terminal output in real time,
        and displays the file size on disk.
      </div>
    </div>
    <div class="card">
      <div class="card-title">📋 The backup gap proof</div>
      <div class="card-sub" style="line-height:1.8">
        1. Take backup → note the file size<br>
        2. The backup captures data at <b>this exact moment</b><br>
        3. Any INSERT/UPDATE after this → not in the backup<br>
        4. Restoring brings you back to backup time
      </div>
    </div>
  </div>

  <div class="card-title" style="margin-bottom:12px">Choose database to back up:</div>
  <div class="db-toggle">
    <button class="db-toggle-btn active-slow" id="bk-slow-btn" onclick="setBkDb('slow')">🔴 hospital_slow</button>
    <button class="db-toggle-btn" id="bk-fast-btn" onclick="setBkDb('fast')">🟢 hospital_fast</button>
  </div>

  <div class="btn-group">
    <button class="btn btn-primary" id="btn-backup" onclick="runBackup()">💾 Run pg_dump</button>
    <span id="bk-status" style="font-size:.75rem;color:var(--muted)"></span>
  </div>

  <div id="bk-result" style="display:none">
    <div class="backup-status result-success" id="bk-output"></div>
  </div>
</div>

<!-- ══════════════════════════════════════════════════════ JS ══ -->
<script>
// ── Navigation ──
document.querySelectorAll('.tab').forEach(tab => {
  tab.addEventListener('click', () => {
    document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
    tab.classList.add('active');
    document.getElementById('page-' + tab.dataset.page).classList.add('active');
  });
});

const fmt = n => Number(n).toLocaleString();

// ── OVERVIEW ──
async function loadStats() {
  const r = await fetch('/api/stats').then(r => r.json());
  function renderStats(data, err, containerId) {
    const el = document.getElementById(containerId);
    if (err || !data) { el.innerHTML = `<div class="result-error" style="font-size:.75rem">Cannot connect: ${err||'unknown'}</div>`; return; }
    el.innerHTML = `
      <div class="grid-auto" style="gap:10px">
        ${[
          ['Patients',fmt(data.patients),'c-blue'],
          ['Doctors',fmt(data.doctors),'c-green'],
          ['Appointments',fmt(data.appointments),'c-amber'],
          ['Lab Results',fmt(data.lab_results),'c-purple'],
          ['Billing',fmt(data.billing),'c-blue'],
          ['Unpaid Bills',fmt(data.unpaid),'c-red'],
        ].map(([lbl,val,cls]) => `
          <div class="stat-mini">
            <div class="lbl">${lbl}</div>
            <div class="val ${cls}" style="font-size:1.4rem">${val}</div>
          </div>`).join('')}
      </div>`;
  }
  renderStats(r.slow, r.slow_err, 'slow-stats');
  renderStats(r.fast, r.fast_err, 'fast-stats');
}
loadStats();

function switchToIndexInspector(e) {
  if (e) e.preventDefault();
  const tab = document.querySelector('.tab[data-page="indexes"]');
  if (tab) tab.click();
  // loadIndexes will be called by the tab's click listener
}

// ── PERFORMANCE LAB (dynamic — loaded from Index Lab) ──
function renderPerfCard(slot, cardIdx) {
  const problemDesc = slot.scenario ? slot.scenario.trim() : `Problem #${cardIdx+1}`;
  const just = slot.justification ? slot.justification.trim() : '';
  const justPreview = just.length > 240 ? just.slice(0, 240).trimEnd() + '…' : just;
  return `<div class="card" style="margin-bottom:20px" id="perf-card-${cardIdx}">
  <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:12px;flex-wrap:wrap;gap:8px">
    <div style="font-size:.82rem;font-weight:700;color:var(--text);max-width:600px">${problemDesc}</div>
    <button class="btn btn-primary" onclick="runPerfCard(${cardIdx})" id="perf-run-${cardIdx}" style="padding:8px 18px">▶ Run on Both</button>
  </div>
  ${justPreview ? `<div style="font-size:.73rem;color:var(--muted);line-height:1.7;font-style:italic;margin-bottom:12px;padding:10px 14px;background:rgba(255,255,255,.02);border-left:3px solid var(--accent);border-radius:var(--r-sm)">"${justPreview}"</div>` : ''}
  <div style="font-size:.68rem;color:var(--muted);font-weight:700;text-transform:uppercase;letter-spacing:.08em;margin-bottom:4px">Index</div>
  <div style="font-family:var(--mono);font-size:.72rem;color:#60a5fa;margin-bottom:12px">${slot.createSql}</div>
  <div style="font-size:.68rem;color:var(--muted);font-weight:700;text-transform:uppercase;letter-spacing:.08em;margin-bottom:4px">Test Query</div>
  <div class="result-info" style="font-size:.72rem;font-family:var(--mono);margin-bottom:14px;white-space:pre-wrap">${slot.testQuery}</div>
  <div id="perf-result-${cardIdx}"></div>
</div>`;
}

let perfSlots = [];
let currentPerfIdx = -1;

function loadPerfQueries() {
  try {
    const saved = JSON.parse(localStorage.getItem(LAB_KEY));
    perfSlots = (saved || []).filter(s => s.testQuery && s.testQuery.trim());
  } catch(e) { perfSlots = []; }

  const sel = document.getElementById('perf-selector');
  const box = document.getElementById('perf-desc-box');

  if (!perfSlots.length) {
    sel.innerHTML = `<div style="color:var(--muted);font-size:.82rem;padding:20px 0">
      No queries yet. Go to the <b>Index Lab</b> tab, create and validate your indexes, then come back here.
    </div>`;
    box.style.display = 'none';
    return;
  }

  sel.innerHTML = perfSlots.map((s,i) =>
    `<button class="q-btn${i===0?' active':''}" onclick="selectPerfQuery(${i})">Query ${i+1}</button>`
  ).join('');
  selectPerfQuery(0);
}

function selectPerfQuery(i) {
  currentPerfIdx = i;
  document.querySelectorAll('#perf-selector .q-btn')
    .forEach((b,j) => b.classList.toggle('active', j===i));

  const slot  = perfSlots[i];
  const desc  = document.getElementById('perf-q-desc');
  const just  = slot.justification ? slot.justification.trim() : '';
  const justPreview = just.length > 200 ? just.slice(0,200).trimEnd()+'…' : just;

  desc.innerHTML = `
    <b>${slot.scenario || `Query ${i+1}`}</b><br>
    ${justPreview ? `<div style="font-size:.73rem;color:var(--muted);font-style:italic;margin:6px 0 10px;padding:8px 12px;border-left:3px solid var(--accent)">"${justPreview}"</div>` : ''}
    <div style="font-size:.68rem;color:var(--muted);font-weight:700;text-transform:uppercase;letter-spacing:.08em;margin-bottom:3px">Index</div>
    <code style="font-size:.72rem;color:#60a5fa">${slot.createSql}</code><br><br>
    <div style="font-size:.68rem;color:var(--muted);font-weight:700;text-transform:uppercase;letter-spacing:.08em;margin-bottom:3px">Test Query</div>
    <code style="font-size:.72rem;color:var(--text);white-space:pre-wrap">${slot.testQuery}</code>`;

  document.getElementById('perf-desc-box').style.display = 'block';
  // Reset results
  document.getElementById('perf-compare-grid').style.display = 'none';
  document.getElementById('perf-plan-grid').style.display = 'none';
  document.getElementById('perf-speedup-area').style.display = 'none';
  document.getElementById('perf-run-status').textContent = '';
}

async function runSelectedPerf() {
  const slot = perfSlots[currentPerfIdx];
  if (!slot) return;
  const btn = document.getElementById('btn-perf-run');
  btn.disabled = true;
  btn.innerHTML = '<span class="spin"></span> Running on both DBs…';
  document.getElementById('perf-run-status').textContent = '';
  document.getElementById('perf-compare-grid').style.display = 'none';
  document.getElementById('perf-plan-grid').style.display = 'none';
  document.getElementById('perf-speedup-area').style.display = 'none';

  const r = await fetch('/api/performance/run', {
    method:'POST', headers:{'Content-Type':'application/json'},
    body: JSON.stringify({sql: slot.testQuery})
  }).then(x => x.json());

  if (!r.ok) {
    document.getElementById('perf-run-status').innerHTML = `<span style="color:var(--slow)">${r.error}</span>`;
    btn.disabled = false; btn.innerHTML = '▶ Run on Both Databases'; return;
  }

  const slowMs = r.slow.ms, fastMs = r.fast.ms;
  const maxMs  = Math.max(slowMs, fastMs, 1);

  document.getElementById('perf-slow-time').textContent = slowMs.toLocaleString();
  document.getElementById('perf-fast-time').textContent = fastMs.toLocaleString();
  document.getElementById('perf-slow-scan').textContent = `ms — ${r.slow.scan_type||'–'}`;
  document.getElementById('perf-fast-scan').textContent = `ms — ${r.fast.scan_type||'–'}`;
  document.getElementById('perf-compare-grid').style.display = 'grid';
  setTimeout(() => {
    document.getElementById('perf-slow-bar').style.width = (slowMs/maxMs*100)+'%';
    document.getElementById('perf-fast-bar').style.width = (fastMs/maxMs*100)+'%';
  }, 50);

  if (r.speedup) {
    document.getElementById('perf-speedup-area').style.display = 'block';
    document.getElementById('perf-speedup-num').textContent = r.speedup + '×';
  }

  document.getElementById('perf-slow-plan').textContent = r.slow.err || r.slow.plan || '–';
  document.getElementById('perf-fast-plan').textContent = r.fast.err || r.fast.plan || '–';
  document.getElementById('perf-plan-grid').style.display = 'grid';

  btn.disabled = false; btn.innerHTML = '▶ Run on Both Databases';
}

document.querySelector('.tab[data-page="performance"]').addEventListener('click', loadPerfQueries);


// ── CONCURRENCY LAB ──
let concDb = 'slow';
function setConcDb(db) {
  concDb = db;
  document.getElementById('conc-slow-btn').className = 'db-toggle-btn' + (db==='slow' ? ' active-slow' : '');
  document.getElementById('conc-fast-btn').className = 'db-toggle-btn' + (db==='fast' ? ' active-fast' : '');
}

async function runConcurrent() {
  const btn = document.getElementById('btn-book');
  btn.disabled = true;
  btn.innerHTML = '<span class="spin"></span> Firing two simultaneous requests…';
  document.getElementById('conc-status').textContent = '';
  document.getElementById('conc-result').style.display = 'none';

  const r = await fetch('/api/concurrent-book', {
    method:'POST', headers:{'Content-Type':'application/json'},
    body: JSON.stringify({db: concDb})
  }).then(r => r.json());

  document.getElementById('conc-result').style.display = 'block';

  const colorMap = {green:'badge-success', red:'badge-error', amber:'badge-warn'};
  document.getElementById('conc-sessions').innerHTML = r.results.map((res,i) => `
    <div class="session-card">
      <div class="session-header">
        <div class="session-name">🙋 ${res.patient}</div>
        <span class="outcome-badge ${colorMap[res.color]||'badge-warn'}">${res.status}</span>
      </div>
      <div style="font-size:.78rem;color:var(--muted2)">${res.reason}</div>
      ${res.pg_error ? `<div class="pg-err">PostgreSQL says:\n${res.pg_error}</div>` : ''}
    </div>`).join('');

  const succeeded = r.succeeded;
  const vCls = succeeded === 1 ? 'verdict-ok' : succeeded === 2 ? 'verdict-bad' : 'verdict-warn';
  document.getElementById('conc-verdict').className = `verdict ${vCls}`;
  document.getElementById('conc-verdict').textContent = r.verdict;

  btn.disabled = false;
  btn.innerHTML = '🚦 Simulate Double Booking';
}

// ── DEADLOCK LAB ──
let dlDb = 'slow';
function setDlDb(db) {
  dlDb = db;
  document.getElementById('dl-slow-btn').className = 'db-toggle-btn' + (db==='slow' ? ' active-slow' : '');
  document.getElementById('dl-fast-btn').className = 'db-toggle-btn' + (db==='fast' ? ' active-fast' : '');
}

async function runDeadlock() {
  const btn = document.getElementById('btn-deadlock');
  btn.disabled = true;
  btn.innerHTML = '<span class="spin"></span> Creating deadlock…';
  document.getElementById('dl-result').style.display = 'none';

  const r = await fetch('/api/deadlock', {
    method:'POST', headers:{'Content-Type':'application/json'},
    body: JSON.stringify({db: dlDb})
  }).then(r => r.json());

  document.getElementById('dl-result').style.display = 'block';
  document.getElementById('dl-log').innerHTML = (r.log||[]).join('\n');

  const colorMap = {green:'badge-success', red:'badge-error'};
  document.getElementById('dl-sessions').innerHTML = (r.results||[]).map(res => {
    if (!res) return '';
    const isDeadlock = res.outcome.includes('DEADLOCK');
    return `
      <div class="session-card">
        <div class="session-header">
          <div class="session-name">${res.session}</div>
          <span class="outcome-badge ${isDeadlock?'badge-error':'badge-success'}">${isDeadlock?'💀 KILLED':'✅ SURVIVED'}</span>
        </div>
        <div style="font-size:.78rem;color:var(--muted2)">${res.outcome}</div>
        ${res.pg_error ? `<div class="pg-err">PostgreSQL error:\n${res.pg_error}</div>` : ''}
      </div>`;
  }).join('');

  const exEl = document.getElementById('dl-explanation');
  exEl.className = r.deadlock_occurred ? 'result-box result-info' : 'result-box result-warn';
  exEl.textContent = r.explanation;

  btn.disabled = false;
  btn.innerHTML = '💥 Trigger Deadlock';
}

// ── INDEX INSPECTOR ──
async function loadIndexes(dbKey) {
  const r = await fetch(`/api/indexes/${dbKey}`).then(r => r.json());
  const bodyId  = `${dbKey}-indexes-body`;
  const countId = `${dbKey}-indexes-count`;
  document.getElementById(countId).innerHTML =
    r.err ? `<span style="color:var(--slow)">Error: ${r.err}</span>` :
    `<b style="color:${dbKey==='slow'?'var(--slow)':'var(--fast)'}">${r.count} custom index${r.count!==1?'es':''}</b>` +
    (dbKey==='slow' && r.count===0 ? ' ✅ correct — no indexes here' :
     dbKey==='fast' && r.count>=10 ? ' ✅ student indexes found' :
     dbKey==='fast' && r.count<10  ? ' ⚠️ expected 10+ indexes' : '');

  // Build a map: indexName → "Query N" from the student's own Index Lab slots
  const slotColors = [
    'color:#60a5fa;background:rgba(59,130,246,.12);border:1px solid rgba(59,130,246,.3)',
    'color:#34d399;background:rgba(16,185,129,.12);border:1px solid rgba(16,185,129,.3)',
    'color:#c084fc;background:rgba(168,85,247,.12);border:1px solid rgba(168,85,247,.3)',
    'color:#f59e0b;background:rgba(245,158,11,.12);border:1px solid rgba(245,158,11,.3)',
    'color:#f87171;background:rgba(248,113,113,.12);border:1px solid rgba(248,113,113,.3)',
    'color:#38bdf8;background:rgba(56,189,248,.12);border:1px solid rgba(56,189,248,.3)',
    'color:#a3e635;background:rgba(163,230,53,.12);border:1px solid rgba(163,230,53,.3)',
  ];
  const labPowerMap = {};
  (typeof labSlots !== 'undefined' ? labSlots : []).forEach((s, i) => {
    if (s.indexName) {
      labPowerMap[s.indexName.toLowerCase()] = {
        label: `Query ${i+1}`,
        desc:  s.scenario ? s.scenario.slice(0, 50) + (s.scenario.length > 50 ? '…' : '') : '',
        color: slotColors[i % slotColors.length]
      };
    }
  });

  document.getElementById(bodyId).innerHTML = r.indexes.length === 0
    ? `<tr><td colspan="4" style="color:var(--muted);font-style:italic">No custom indexes found (only primary keys)</td></tr>`
    : r.indexes.map(idx => {
        const m = labPowerMap[idx.indexname.toLowerCase()];
        const badge = m
          ? `<span style="font-size:.65rem;font-weight:700;padding:2px 9px;border-radius:999px;${m.color}">${m.label}</span>
             <span style="font-size:.65rem;color:var(--muted);margin-left:5px">${m.desc}</span>`
          : `<span style="color:var(--muted);font-size:.7rem">—</span>`;
        return `
          <tr>
            <td class="idx-name">${idx.indexname}</td>
            <td class="idx-table-name">${idx.tablename}</td>
            <td>${badge}</td>
            <td class="idx-def">${idx.indexdef}</td>
          </tr>`;
      }).join('');
}

document.querySelector('.tab[data-page="indexes"]').addEventListener('click', () => {
  loadIndexes('slow');
  loadIndexes('fast');
});

// ── CREATE / DROP INDEX ──
let idxDb = 'fast';
function setIdxDb(db) {
  idxDb = db;
  document.getElementById('idx-slow-btn').className = 'db-toggle-btn' + (db==='slow' ? ' active-slow' : '');
  document.getElementById('idx-fast-btn').className = 'db-toggle-btn' + (db==='fast' ? ' active-fast' : '');
}

async function runCreateIndex() {
  const sql = document.getElementById('idx-sql').value.trim();
  const btn = document.getElementById('btn-idx-run');
  const out = document.getElementById('idx-run-result');

  if (!sql) { out.innerHTML = '<span style="color:var(--amber)">Write a CREATE INDEX or DROP INDEX statement first.</span>'; return; }

  btn.disabled = true;
  btn.innerHTML = '<span class="spin"></span>';
  out.textContent = '';

  const r = await fetch('/api/create-index', {
    method: 'POST', headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({sql, db: idxDb})
  }).then(x => x.json());

  if (r.ok) {
    out.innerHTML = `<span style="color:var(--fast)">✅ ${r.message}</span>`;
    loadIndexes(idxDb);   // auto-refresh the affected table
  } else {
    out.innerHTML = `<span style="color:var(--slow)">❌ ${r.error}</span>`;
  }

  btn.disabled = false;
  btn.innerHTML = '▶ Run';
}


// ── BACKUP LAB ──
let bkDb = 'slow';
function setBkDb(db) {
  bkDb = db;
  document.getElementById('bk-slow-btn').className = 'db-toggle-btn' + (db==='slow' ? ' active-slow' : '');
  document.getElementById('bk-fast-btn').className = 'db-toggle-btn' + (db==='fast' ? ' active-fast' : '');
}

async function runBackup() {
  const btn = document.getElementById('btn-backup');
  btn.disabled = true;
  btn.innerHTML = '<span class="spin"></span> Running pg_dump…';
  document.getElementById('bk-status').textContent = 'This may take 30–60 seconds…';
  document.getElementById('bk-result').style.display = 'none';

  const r = await fetch('/api/backup', {
    method:'POST', headers:{'Content-Type':'application/json'},
    body: JSON.stringify({db: bkDb})
  }).then(r => r.json());

  document.getElementById('bk-result').style.display = 'block';
  const el = document.getElementById('bk-output');
  if (r.success) {
    el.className = 'backup-status result-success';
    el.innerHTML = `✅ Backup complete!\n\nFile: ${r.file}\nSize: ${r.size_mb} MB\nTime: ${r.time_ms}ms\n\n${r.message}`;
  } else {
    el.className = 'backup-status result-error';
    el.textContent = '❌ Backup failed:\n\n' + r.error;
  }

  btn.disabled = false;
  btn.innerHTML = '💾 Run pg_dump';
  document.getElementById('bk-status').textContent = '';
}
</script>

<!-- ══════════════════════════════════════════════════════ PAGE: SQL SANDBOX ══ -->
<div id="page-sandbox" class="page">
  <div class="sec">🔬 SQL Sandbox — Run Any Query on Both Databases</div>

  <div class="result-info" style="font-size:.78rem;margin-bottom:20px;line-height:1.7">
    Type any <code>SELECT</code> query below. It runs on <b>both databases simultaneously</b> and shows timing + EXPLAIN ANALYZE side by side.
    <b>For the instructor:</b> type a custom query here during the demo to test the student on any scenario — they can't prepare for it in advance.
    <br><span style="color:var(--amber)">⚠️ DROP, DELETE, TRUNCATE, ALTER statements are blocked.</span>
  </div>

  <!-- Query presets -->
  <div style="font-size:.72rem;color:var(--muted);margin-bottom:8px;font-weight:600">QUICK PRESETS</div>
  <div style="display:flex;gap:8px;flex-wrap:wrap;margin-bottom:14px">
    <button class="btn btn-ghost" style="font-size:.72rem;padding:6px 12px"
      onclick="setSandboxSQL('SELECT p.name, COUNT(a.id) AS total FROM patients p JOIN appointments a ON a.patient_id=p.id GROUP BY p.id ORDER BY total DESC LIMIT 20')">
      Top patients by appointments
    </button>
    <button class="btn btn-ghost" style="font-size:.72rem;padding:6px 12px"
      onclick="setSandboxSQL('SELECT d.specialty, COUNT(a.id) AS total, AVG(b.amount) AS avg_bill FROM doctors d JOIN appointments a ON a.doctor_id=d.id JOIN billing b ON b.appointment_id=a.id WHERE b.paid_at IS NOT NULL GROUP BY d.specialty ORDER BY total DESC')">
      Revenue by specialty
    </button>
    <button class="btn btn-ghost" style="font-size:.72px;padding:6px 12px"
      onclick="setSandboxSQL('SELECT p.name, p.city, lr.test_name, lr.value, lr.taken_at FROM lab_results lr JOIN patients p ON lr.patient_id=p.id WHERE lr.test_name=\'Hemoglobin\' AND lr.taken_at >= NOW()-INTERVAL \'6 months\' ORDER BY lr.taken_at DESC LIMIT 30')">
      Hemoglobin results — 6 months
    </button>
    <button class="btn btn-ghost" style="font-size:.72rem;padding:6px 12px"
      onclick="setSandboxSQL('SELECT room_number, type, floor, capacity FROM rooms WHERE type=\'ICU\' ORDER BY floor')">
      All ICU rooms
    </button>
  </div>

  <!-- SQL Input -->
  <div style="position:relative;margin-bottom:14px">
    <textarea id="sandbox-sql" rows="5" style="
        width:100%;background:#030810;border:1px solid var(--border);
        border-radius:var(--r-sm);padding:14px 16px;color:var(--text);
        font-family:var(--mono);font-size:.78rem;line-height:1.7;resize:vertical;
        transition:border-color .2s;
      "
      placeholder="SELECT p.name, COUNT(a.id) AS appts&#10;FROM patients p&#10;JOIN appointments a ON a.patient_id = p.id&#10;GROUP BY p.id&#10;ORDER BY appts DESC&#10;LIMIT 20"
      onfocus="this.style.borderColor='var(--accent)'"
      onblur="this.style.borderColor='var(--border)'"
    ></textarea>
  </div>

  <!-- DB selector + Run -->
  <div style="display:flex;align-items:center;gap:12px;flex-wrap:wrap;margin-bottom:20px">
    <label style="font-size:.75rem;color:var(--muted);display:flex;align-items:center;gap:6px;cursor:pointer">
      <input type="checkbox" id="sb-slow" checked style="accent-color:var(--slow)">
      <span class="db-label db-slow" style="padding:3px 8px"><span class="dot"></span>hospital_slow</span>
    </label>
    <label style="font-size:.75rem;color:var(--muted);display:flex;align-items:center;gap:6px;cursor:pointer">
      <input type="checkbox" id="sb-fast" checked style="accent-color:var(--fast)">
      <span class="db-label db-fast" style="padding:3px 8px"><span class="dot"></span>hospital_fast</span>
    </label>
    <button class="btn btn-primary" id="btn-sandbox" onclick="runSandbox()">▶ Run Query</button>
    <span id="sandbox-status" style="font-size:.75rem;color:var(--muted)"></span>
  </div>

  <!-- Results -->
  <div id="sandbox-result" style="display:none">

    <!-- Speedup banner -->
    <div id="sb-speedup" style="display:none;margin-bottom:16px">
      <div class="speedup-badge">
        <div class="speedup-num" id="sb-speedup-num">–</div>
        <div class="speedup-lbl">× faster on hospital_fast</div>
      </div>
    </div>

    <!-- Side-by-side timing + plans -->
    <div class="compare-grid" id="sb-compare-grid"></div>

    <!-- Side-by-side data preview -->
    <div class="grid-2" style="margin-top:16px" id="sb-data-grid"></div>
  </div>
</div>

<!-- ══════════════════════════════════════════════════════ PAGE: TX VISUALIZER ══ -->
<div id="page-txn" class="page">
  <div class="sec">📋 Transaction Visualizer — Step-by-Step in Two Sessions</div>

  <div class="result-info" style="font-size:.78rem;margin-bottom:20px;line-height:1.7">
    Each panel is an <b>independent real database connection</b> with its own open transaction.
    Click steps in any order across both sessions to see blocking, isolation, and commit/rollback behavior.
    The transaction stays open on the server until you COMMIT or ROLLBACK.
  </div>

  <div style="font-size:.72rem;color:var(--amber);background:rgba(245,158,11,.07);border:1px solid rgba(245,158,11,.2);
              border-radius:var(--r-sm);padding:10px 14px;margin-bottom:20px">
    💡 <b>Try this:</b> Session A — BEGIN → UPDATE patient id=1 → (don't commit yet).
    Session B — BEGIN → try to UPDATE the same row → it will <b>BLOCK</b> because Session A holds the lock.
    Then COMMIT Session A and watch Session B unblock.
  </div>

  <div class="grid-2" id="txn-grid">

    <!-- SESSION A -->
    <div class="card" id="txn-card-a">
      <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:16px">
        <div style="display:flex;align-items:center;gap:10px">
          <div style="font-size:.95rem;font-weight:800">Session A</div>
          <span id="txn-a-status-badge" class="outcome-badge badge-warn">IDLE</span>
        </div>
      </div>

      <!-- Config row -->
      <div style="display:flex;gap:10px;align-items:center;margin-bottom:12px;flex-wrap:wrap">
        <select id="txn-a-db" style="background:var(--bg2);border:1px solid var(--border);
            border-radius:var(--r-sm);padding:7px 12px;color:var(--text);font-size:.75rem;font-family:inherit">
          <option value="slow">hospital_slow</option>
          <option value="fast">hospital_fast</option>
        </select>
        <select id="txn-a-iso" style="background:var(--bg2);border:1px solid var(--border);
            border-radius:var(--r-sm);padding:7px 12px;color:var(--text);font-size:.75rem;font-family:inherit">
          <option value="READ COMMITTED">READ COMMITTED</option>
          <option value="REPEATABLE READ">REPEATABLE READ</option>
          <option value="SERIALIZABLE">SERIALIZABLE</option>
        </select>
      </div>

      <!-- SQL input -->
      <textarea id="txn-a-sql" rows="3" style="
          width:100%;background:#030810;border:1px solid var(--border);
          border-radius:var(--r-sm);padding:10px;color:var(--text);
          font-family:var(--mono);font-size:.72rem;resize:vertical;margin-bottom:10px"
        placeholder="UPDATE patients SET city = 'Cairo' WHERE id = 1"></textarea>

      <!-- Action buttons -->
      <div style="display:flex;gap:8px;flex-wrap:wrap;margin-bottom:14px">
        <button class="btn btn-primary" style="padding:8px 14px;font-size:.75rem" onclick="txnAction('a','begin')">BEGIN</button>
        <button class="btn btn-ghost"   style="padding:8px 14px;font-size:.75rem" onclick="txnAction('a','execute')" id="txn-a-exec" disabled>EXECUTE</button>
        <button class="btn btn-success" style="padding:8px 14px;font-size:.75rem" onclick="txnAction('a','commit')"  id="txn-a-commit" disabled>COMMIT</button>
        <button class="btn btn-danger"  style="padding:8px 14px;font-size:.75rem" onclick="txnAction('a','rollback')" id="txn-a-rollback" disabled>ROLLBACK</button>
      </div>

      <!-- Response -->
      <div id="txn-a-response" style="margin-bottom:10px;min-height:32px"></div>

      <!-- Log -->
      <div style="font-size:.65rem;color:var(--muted);font-weight:700;text-transform:uppercase;letter-spacing:.08em;margin-bottom:6px">Transaction Log</div>
      <div class="log-box" id="txn-a-log">Idle — click BEGIN to start a transaction</div>
    </div>

    <!-- SESSION B -->
    <div class="card" id="txn-card-b">
      <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:16px">
        <div style="display:flex;align-items:center;gap:10px">
          <div style="font-size:.95rem;font-weight:800">Session B</div>
          <span id="txn-b-status-badge" class="outcome-badge badge-warn">IDLE</span>
        </div>
      </div>

      <div style="display:flex;gap:10px;align-items:center;margin-bottom:12px;flex-wrap:wrap">
        <select id="txn-b-db" style="background:var(--bg2);border:1px solid var(--border);
            border-radius:var(--r-sm);padding:7px 12px;color:var(--text);font-size:.75rem;font-family:inherit">
          <option value="slow">hospital_slow</option>
          <option value="fast">hospital_fast</option>
        </select>
        <select id="txn-b-iso" style="background:var(--bg2);border:1px solid var(--border);
            border-radius:var(--r-sm);padding:7px 12px;color:var(--text);font-size:.75rem;font-family:inherit">
          <option value="READ COMMITTED">READ COMMITTED</option>
          <option value="REPEATABLE READ">REPEATABLE READ</option>
          <option value="SERIALIZABLE">SERIALIZABLE</option>
        </select>
      </div>

      <textarea id="txn-b-sql" rows="3" style="
          width:100%;background:#030810;border:1px solid var(--border);
          border-radius:var(--r-sm);padding:10px;color:var(--text);
          font-family:var(--mono);font-size:.72rem;resize:vertical;margin-bottom:10px"
        placeholder="SELECT city FROM patients WHERE id = 1"></textarea>

      <div style="display:flex;gap:8px;flex-wrap:wrap;margin-bottom:14px">
        <button class="btn btn-primary" style="padding:8px 14px;font-size:.75rem" onclick="txnAction('b','begin')">BEGIN</button>
        <button class="btn btn-ghost"   style="padding:8px 14px;font-size:.75rem" onclick="txnAction('b','execute')" id="txn-b-exec" disabled>EXECUTE</button>
        <button class="btn btn-success" style="padding:8px 14px;font-size:.75rem" onclick="txnAction('b','commit')"  id="txn-b-commit" disabled>COMMIT</button>
        <button class="btn btn-danger"  style="padding:8px 14px;font-size:.75rem" onclick="txnAction('b','rollback')" id="txn-b-rollback" disabled>ROLLBACK</button>
      </div>

      <div id="txn-b-response" style="margin-bottom:10px;min-height:32px"></div>

      <div style="font-size:.65rem;color:var(--muted);font-weight:700;text-transform:uppercase;letter-spacing:.08em;margin-bottom:6px">Transaction Log</div>
      <div class="log-box" id="txn-b-log">Idle — click BEGIN to start a transaction</div>
    </div>

  </div>
</div>

<!-- ══════════════════════════════════════════════════════ PAGE: INDEX LAB ══ -->
<div id="page-indexlab" class="page">
  <div class="sec">🧪 Index Lab — Business Case Optimization</div>

  <div class="result-info" style="font-size:.78rem;margin-bottom:16px;line-height:1.8">
    Read <b>05-business-case.md</b> and identify performance problems. For each one you choose, describe it in your own words,
    paste the quote from the report, write your <code>CREATE INDEX</code> statement and a test query, then click <b>Create &amp; Validate</b>.
    <br>
    <span style="color:var(--amber)">Requirements: ≥ 10 validated &nbsp;|&nbsp; ≥ 2 partial &nbsp;|&nbsp; ≥ 3 composite &nbsp;|&nbsp; ≥ 5 regular</span>
    &nbsp;<span style="color:var(--muted);font-size:.72rem">— Slots 11–15 are optional bonus slots.</span>
  </div>

  <!-- Progress bar -->
  <div class="card" style="margin-bottom:20px;padding:16px 20px">
    <div style="display:flex;align-items:center;gap:16px;flex-wrap:wrap;margin-bottom:12px">
      <div style="font-size:.8rem;font-weight:700">Progress</div>
      <div style="flex:1;min-width:180px">
        <div class="bar-track" style="height:10px">
          <div class="bar-fill bar-fast" id="lab-progress-bar" style="width:0%;background:var(--fast)"></div>
        </div>
      </div>
      <div id="lab-progress-text" style="font-size:.8rem;font-weight:800;color:var(--fast)">0 / 10</div>
    </div>
    <div style="display:flex;gap:20px;flex-wrap:wrap;font-size:.72rem">
      <span>Regular: <b id="cnt-regular" style="color:#60a5fa">0</b> / 5</span>
      <span>Composite: <b id="cnt-composite" style="color:#c084fc">0</b> / 3</span>
      <span>Partial: <b id="cnt-partial" style="color:#34d399">0</b> / 2</span>
      <span style="margin-left:auto;color:var(--muted);font-size:.68rem">Progress is saved in your browser automatically</span>
    </div>
  </div>

  <!-- 10 Slots -->
  <div id="lab-slots"></div>
</div>

<script>
// ── SQL SANDBOX ──
function setSandboxSQL(sql) {
  document.getElementById('sandbox-sql').value = sql;
}

async function runSandbox() {
  const sql  = document.getElementById('sandbox-sql').value.trim();
  const slow = document.getElementById('sb-slow').checked;
  const fast = document.getElementById('sb-fast').checked;
  const dbs  = [...(slow?['slow']:[]), ...(fast?['fast']:[])];

  if (!sql)          { alert('Write a SQL query first.'); return; }
  if (!dbs.length)   { alert('Select at least one database.'); return; }

  const btn = document.getElementById('btn-sandbox');
  btn.disabled = true;
  btn.innerHTML = '<span class="spin"></span> Running…';
  document.getElementById('sandbox-status').textContent = '';
  document.getElementById('sandbox-result').style.display = 'none';

  const r = await fetch('/api/sandbox', {
    method:'POST', headers:{'Content-Type':'application/json'},
    body: JSON.stringify({sql, dbs})
  }).then(r => r.json());

  if (r.error) {
    document.getElementById('sandbox-status').innerHTML = `<span style="color:var(--slow)">${r.error}</span>`;
    btn.disabled = false; btn.innerHTML = '▶ Run Query'; return;
  }

  document.getElementById('sandbox-result').style.display = 'block';

  // Speedup
  const sbSpeedup = document.getElementById('sb-speedup');
  if (r.speedup && dbs.includes('slow') && dbs.includes('fast')) {
    sbSpeedup.style.display = 'block';
    document.getElementById('sb-speedup-num').textContent = r.speedup + '×';
  } else {
    sbSpeedup.style.display = 'none';
  }

  // Compare grid (timing + plan)
  const maxMs = Math.max(...dbs.map(d => r.results[d]?.ms || 0), 1);
  document.getElementById('sb-compare-grid').innerHTML = dbs.map(dbKey => {
    const res = r.results[dbKey];
    const color = dbKey === 'slow' ? 'var(--slow)' : 'var(--fast)';
    const label = dbKey === 'slow' ? 'hospital_slow' : 'hospital_fast';
    const scanType = (res.plan||'').match(/(Seq Scan|Index Scan|Bitmap Heap Scan|Index Only Scan)/)?.[1] || '–';
    const pct = Math.round((res.ms / maxMs) * 100);
    return `
      <div class="compare-side ${dbKey}-side">
        <div class="db-label db-${dbKey}"><span class="dot"></span>${label}</div>
        <div class="timing-big" style="color:${color}">${res.ms.toLocaleString()}</div>
        <div class="timing-unit">ms — ${scanType}</div>
        <div class="bar-row bar-${dbKey}">
          <div class="bar-track"><div class="bar-fill" style="width:0%" id="sb-bar-${dbKey}"></div></div>
        </div>
        <div style="margin-top:12px;font-size:.65rem;color:var(--muted);font-weight:700;text-transform:uppercase;letter-spacing:.08em">EXPLAIN ANALYZE</div>
        <div class="terminal" style="margin-top:6px;max-height:200px">${res.err || res.plan || '–'}</div>
      </div>`;
  }).join('');

  setTimeout(() => {
    dbs.forEach(d => {
      const bar = document.getElementById(`sb-bar-${d}`);
      if (bar) bar.style.width = Math.round((r.results[d].ms / maxMs)*100) + '%';
    });
  }, 50);

  // Data preview grid
  document.getElementById('sb-data-grid').innerHTML = dbs.map(dbKey => {
    const res = r.results[dbKey];
    if (!res.rows || !res.rows.length) return `
      <div><div class="sec" style="margin-bottom:8px">Data — ${dbKey}</div>
      <div style="color:var(--muted);font-size:.78rem">No rows returned</div></div>`;
    const cols = Object.keys(res.rows[0]);
    return `
      <div>
        <div class="sec" style="margin-bottom:8px">Data preview — hospital_${dbKey} (${res.row_count} rows, showing ≤20)</div>
        <div style="overflow-x:auto">
          <table class="idx-table">
            <thead><tr>${cols.map(c=>`<th>${c}</th>`).join('')}</tr></thead>
            <tbody>${res.rows.map(row=>`<tr>${cols.map(c=>`<td>${row[c]??''}</td>`).join('')}</tr>`).join('')}</tbody>
          </table>
        </div>
      </div>`;
  }).join('');

  btn.disabled = false; btn.innerHTML = '▶ Run Query';
}

// ── TRANSACTION VISUALIZER ──
const txnIDs = { a: 'txn-session-A-' + Math.random().toString(36).slice(2),
                 b: 'txn-session-B-' + Math.random().toString(36).slice(2) };

const statusCls = {
  idle:        'badge-warn',
  open:        'badge-success',
  committed:   'badge-success',
  rolled_back: 'badge-warn',
  error:       'badge-error'
};
const statusLabel = {
  idle:'IDLE', open:'IN TXN', committed:'COMMITTED', rolled_back:'ROLLED BACK', error:'ERROR'
};

function setTxnStatus(sess, status) {
  const badge = document.getElementById(`txn-${sess}-status-badge`);
  badge.className = `outcome-badge ${statusCls[status] || 'badge-warn'}`;
  badge.textContent = statusLabel[status] || status.toUpperCase();

  const isOpen = status === 'open';
  document.getElementById(`txn-${sess}-exec`).disabled     = !isOpen;
  document.getElementById(`txn-${sess}-commit`).disabled   = !isOpen;
  document.getElementById(`txn-${sess}-rollback`).disabled = !isOpen;

  const card = document.getElementById(`txn-card-${sess}`);
  card.style.borderColor = status === 'open'        ? 'rgba(59,130,246,.4)'
                         : status === 'committed'   ? 'rgba(16,185,129,.4)'
                         : status === 'rolled_back' ? 'rgba(245,158,11,.4)'
                         : status === 'error'       ? 'rgba(239,68,68,.4)'
                         : 'var(--border)';
}

function updateTxnLog(sess, log, status) {
  const el = document.getElementById(`txn-${sess}-log`);
  el.textContent = log.join('\n');
  el.scrollTop = el.scrollHeight;
  setTxnStatus(sess, status || 'idle');
}

async function txnAction(sess, action) {
  const sid  = txnIDs[sess];
  const db   = document.getElementById(`txn-${sess}-db`).value;
  const iso  = document.getElementById(`txn-${sess}-iso`).value;
  const sql  = document.getElementById(`txn-${sess}-sql`).value.trim();
  const resp = document.getElementById(`txn-${sess}-response`);

  resp.innerHTML = '<span class="spin" style="width:12px;height:12px"></span>';

  let r;
  if (action === 'begin') {
    r = await fetch('/api/txn/begin', {
      method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({session_id: sid, db, isolation: iso})
    }).then(x => x.json());
  } else if (action === 'execute') {
    if (!sql) { resp.innerHTML = '<span style="color:var(--amber);font-size:.75rem">Write a SQL statement first.</span>'; return; }
    r = await fetch('/api/txn/execute', {
      method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({session_id: sid, sql})
    }).then(x => x.json());
  } else if (action === 'commit') {
    r = await fetch('/api/txn/commit', {
      method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({session_id: sid})
    }).then(x => x.json());
  } else if (action === 'rollback') {
    r = await fetch('/api/txn/rollback', {
      method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({session_id: sid})
    }).then(x => x.json());
  }

  if (r.log) updateTxnLog(sess, r.log, r.status);

  if (r.ok) {
    const cls = r.status === 'committed' ? 'result-success'
              : r.status === 'rolled_back' ? 'result-warn'
              : 'result-info';
    resp.innerHTML = `<div class="result-box ${cls}" style="padding:8px 12px;font-size:.75rem;margin-top:0">${r.message}</div>`;

    // Show data preview if execute returned rows
    if (action === 'execute' && r.preview && r.preview.length) {
      const preview = r.preview.map(row => `<tr>${row.map(v=>`<td>${v??''}</td>`).join('')}</tr>`).join('');
      resp.innerHTML += `<div style="overflow-x:auto;margin-top:8px">
        <table class="idx-table"><tbody>${preview}</tbody></table>
      </div>`;
    }
  } else {
    resp.innerHTML = `<div class="pg-err" style="margin-top:0">❌ ${r.error}</div>`;
    if (r.status) setTxnStatus(sess, r.status);
  }
}

// ── INDEX LAB ──
const LAB_SCENARIOS = [
  { id:'BC-01', dept:'Reception',  hint:'Patient name search' },
  { id:'BC-02', dept:'Finance',    hint:'Unpaid bills report' },
  { id:'BC-03', dept:'Pharmacy',   hint:'Drug name lookup' },
  { id:'BC-04', dept:'Laboratory', hint:'Test results by type + date' },
  { id:'BC-05', dept:'Outpatient', hint:"Doctor's appointment schedule" },
  { id:'BC-06', dept:'Pathology',  hint:'Patient lab results by patient ID' },
  { id:'BC-07', dept:'Admissions', hint:'Room by type + floor' },
  { id:'BC-08', dept:'Scheduling', hint:'Active appointments only' },
  { id:'BC-09', dept:'Clinical',   hint:'Diagnosis by ICD code' },
  { id:'BC-10', dept:'Finance',    hint:'Payment method breakdown' },
  { id:'BC-11', dept:'Regional',   hint:'Patients by city' },
  { id:'BC-12', dept:'Outpatient', hint:'Patient appointment history' },
  { id:'BC-13', dept:'Laboratory', hint:'Recent lab results only' },
  { id:'BC-14', dept:'Admin/HR',   hint:'Doctors by specialty' },
  { id:'BC-15', dept:'Finance',    hint:'Billing by appointment + payment' },
];

const LAB_KEY = 'indexLab_v2';
const blankSlot = i => ({ id:i, scenario:'', justification:'', createSql:'',
  indexName:'', indexType:'', testQuery:'',
  status:'empty', scanType:'', queryMs:0, planSnippet:'', errorMsg:'', rowsReturned:0 });

let labSlots = (() => {
  try {
    const d2 = JSON.parse(localStorage.getItem(LAB_KEY));
    if (d2 && d2.length === 15) return d2;
    // Migrate from v1 (10 slots) by padding 5 blank slots
    const d1 = JSON.parse(localStorage.getItem('indexLab_v1'));
    if (d1 && d1.length === 10) {
      const migrated = [...d1, ...Array.from({length:5}, (_,i) => blankSlot(10+i))];
      localStorage.setItem(LAB_KEY, JSON.stringify(migrated));
      return migrated;
    }
  } catch(e){}
  return Array.from({length:15}, (_,i) => blankSlot(i));
})();

function saveLabSlots() { localStorage.setItem(LAB_KEY, JSON.stringify(labSlots)); }

function extractIndexName(sql) {
  const m = sql.match(/CREATE\s+(?:UNIQUE\s+)?INDEX\s+(?:IF\s+NOT\s+EXISTS\s+)?(\w+)/i);
  return m ? m[1] : '';
}

function detectIndexType(sql) {
  if (/\bWHERE\b/i.test(sql)) return 'partial';
  const m = sql.match(/ON\s+\w+\s*\(([^)]+)\)/i);
  if (m && m[1].split(',').filter(c=>c.trim()).length >= 2) return 'composite';
  return 'regular';
}

const typeStyle = {
  regular:   'color:#60a5fa;background:rgba(59,130,246,.12);border:1px solid rgba(59,130,246,.3)',
  composite: 'color:#c084fc;background:rgba(168,85,247,.12);border:1px solid rgba(168,85,247,.3)',
  partial:   'color:#34d399;background:rgba(16,185,129,.12);border:1px solid rgba(16,185,129,.3)',
};
const statusInfo = {
  empty:    { icon:'⬜', label:'Not started',    col:'var(--muted)' },
  running:  { icon:'⏳', label:'Running…',       col:'var(--amber)' },
  used:     { icon:'✅', label:'Index Confirmed', col:'var(--fast)'  },
  not_used: { icon:'⚠️', label:'Index Not Used', col:'var(--amber)' },
  error:    { icon:'❌', label:'Error',           col:'var(--slow)'  },
};

function typeBadgeHtml(type) {
  if (!type) return '';
  return `<span style="font-size:.62rem;font-weight:700;padding:2px 8px;border-radius:999px;${typeStyle[type]||''}">${type}</span>`;
}

function updateLabProgress() {
  const valid = labSlots.filter(s=>s.status==='used');
  const done  = valid.length;
  const req   = Math.min(done, 10);
  document.getElementById('lab-progress-bar').style.width = (req/10*100)+'%';
  document.getElementById('lab-progress-text').textContent = done > 10
    ? `${done} / 10 (+${done-10} bonus)` : `${done} / 10`;
  const ok = (v,min) => v>=min ? 'var(--fast)' : '#60a5fa';
  const r = valid.filter(s=>s.indexType==='regular').length;
  const c = valid.filter(s=>s.indexType==='composite').length;
  const p = valid.filter(s=>s.indexType==='partial').length;
  document.getElementById('cnt-regular').textContent=r;   document.getElementById('cnt-regular').style.color=ok(r,5);
  document.getElementById('cnt-composite').textContent=c; document.getElementById('cnt-composite').style.color=ok(c,3);
  document.getElementById('cnt-partial').textContent=p;   document.getElementById('cnt-partial').style.color=ok(p,2);
}

function labTa(id, rows, val, ph, cb) {
  return `<textarea id="${id}" rows="${rows}" oninput="${cb}"
    style="width:100%;margin-top:5px;background:#030810;border:1px solid var(--border);
           border-radius:var(--r-sm);padding:10px 12px;color:var(--text);font-family:var(--mono);
           font-size:.72rem;line-height:1.6;resize:vertical;transition:border .2s"
    placeholder="${ph}"
    onfocus="this.style.borderColor='var(--accent)'" onblur="this.style.borderColor='var(--border)'"
  >${val}</textarea>`;
}

function renderLabSlot(idx) {
  const s  = labSlots[idx];
  const si = statusInfo[s.status] || statusInfo.empty;
  const tb = typeBadgeHtml(s.indexType);

  const resultBlock = (s.status!=='empty' && s.status!=='running') ? `
    <div style="margin-top:14px;padding:12px 14px;background:#030810;border-radius:var(--r-sm);border:1px solid var(--border)">
      <div style="display:flex;gap:14px;flex-wrap:wrap;font-size:.72rem;margin-bottom:8px">
        <span>Scan: <b style="color:${s.scanType==='Seq Scan'?'var(--slow)':'var(--fast)'}">${s.scanType||'–'}</b></span>
        <span>Time: <b style="color:var(--fast)">${s.queryMs}ms</b></span>
        <span>Rows: <b>${s.rowsReturned}</b></span>
        ${s.indexName?`<span>Your index in plan: <b style="color:${s.status==='used'?'var(--fast)':'var(--slow)'}">${s.status==='used'?'✅ Yes':'⚠️ No'}</b></span>`:''}
      </div>
      ${s.status==='used' ? `<div style="margin-top:8px;font-size:.7rem;color:var(--fast)">
        ✅ Index <b>${s.indexName}</b> was created in <b>hospital_fast</b> and confirmed in the query plan.
        <span style="color:var(--muted)"> — </span>
        <a href="#" onclick="switchToIndexInspector(event)" style="color:#60a5fa;text-decoration:underline">View in Index Inspector →</a>
      </div>` : ''}
      ${s.errorMsg?`<div class="pg-err">${s.errorMsg}</div>`:''}
      ${s.planSnippet?`<pre style="font-size:.63rem;color:#94a3b8;line-height:1.6;max-height:150px;overflow:auto;white-space:pre-wrap;margin:0">${s.planSnippet.slice(0,800)}${s.planSnippet.length>800?'…':''}</pre>`:''}
    </div>` : '';

  return `<div class="card" style="margin-bottom:16px" id="lab-slot-${idx}">
  <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:14px;flex-wrap:wrap;gap:8px">
    <div style="display:flex;align-items:center;gap:10px">
      <span style="font-size:.95rem;font-weight:800;color:var(--muted2)">#${idx+1}</span>
      ${idx >= 10 ? `<span style="font-size:.62rem;font-weight:700;padding:2px 8px;border-radius:999px;color:#f59e0b;background:rgba(245,158,11,.12);border:1px solid rgba(245,158,11,.3)">Bonus</span>` : ''}
      <span style="font-size:.75rem;font-weight:700;color:${si.col}">${si.icon} ${si.label}</span>
      ${tb}
    </div>
    <button onclick="clearLabSlot(${idx})" style="font-size:.65rem;color:var(--muted);background:none;border:1px solid var(--border);cursor:pointer;padding:3px 10px;border-radius:4px"
      onmouseover="this.style.color='var(--slow)'" onmouseout="this.style.color='var(--muted)'">🗑 Clear</button>
  </div>
  <div style="margin-bottom:12px">
    <label style="font-size:.67rem;font-weight:700;color:var(--muted);text-transform:uppercase;letter-spacing:.08em">Problem you identified — describe it in your own words *</label>
    ${labTa(`lab-scenario-${idx}`,2,s.scenario,'e.g. "Reception staff search patients by name. The audit report says desk staff wait several uncomfortable seconds for each lookup during peak hours..."',`labField(${idx},'scenario',this.value)`)}
  </div>
  <div style="margin-bottom:12px">
    <label style="font-size:.67rem;font-weight:700;color:var(--muted);text-transform:uppercase;letter-spacing:.08em">Justification — paste exact paragraph from business case *</label>
    ${labTa(`lab-just-${idx}`,3,s.justification,'Paste the exact paragraph from 05-business-case.md that motivated this index...',`labField(${idx},'justification',this.value)`)}
  </div>
  <div style="margin-bottom:12px">
    <div style="display:flex;justify-content:space-between;align-items:center">
      <label style="font-size:.67rem;font-weight:700;color:var(--muted);text-transform:uppercase;letter-spacing:.08em">CREATE INDEX Statement *</label>
      ${s.indexName?`<span style="font-size:.65rem;color:var(--muted)">Detected: <b style="color:var(--text)">${s.indexName}</b> · ${tb}</span>`:''}
    </div>
    ${labTa(`lab-sql-${idx}`,2,s.createSql,'CREATE INDEX idx_patients_name ON patients(name);',`labSqlLive(${idx},this.value)`)}
  </div>
  <div style="margin-bottom:14px">
    <label style="font-size:.67rem;font-weight:700;color:var(--muted);text-transform:uppercase;letter-spacing:.08em">Test Query — must use the index you created *</label>
    ${labTa(`lab-query-${idx}`,3,s.testQuery,"SELECT * FROM patients WHERE name LIKE 'Ahmed%' LIMIT 50;",`labField(${idx},'testQuery',this.value)`)}
    ${s.indexType ? `<div style="margin-top:6px;padding:8px 12px;border-radius:var(--r-sm);border:1px solid rgba(255,255,255,.06);background:rgba(255,255,255,.02);font-size:.68rem;line-height:1.8;color:var(--muted)">
      ${s.indexType === 'regular' ? `💡 <b style="color:var(--text)">Regular index tip:</b> Your WHERE clause must filter on the exact indexed column.<br>
      ✅ <code style="color:#60a5fa">WHERE col = 'value'</code> &nbsp;or&nbsp; <code style="color:#60a5fa">WHERE col LIKE 'prefix%'</code><br>
      ❌ <code>LIKE '%value%'</code> — leading wildcard, index is ignored.<br>
      ⚠️ <b style="color:var(--amber)">Text column + LIKE?</b> You must add <code style="color:#fbbf24">text_pattern_ops</code>:<br>
      &nbsp;&nbsp;<code style="color:#fbbf24">CREATE INDEX name ON table(col <b>text_pattern_ops</b>);</code><br>
      Without it, PostgreSQL's locale settings prevent B-tree indexes from supporting LIKE.<br>
      🚫 <b style="color:var(--amber)">Avoid LIMIT in your test query.</b> With LIMIT, PostgreSQL may prefer a Parallel Seq Scan because getting "the first 50 rows" is sometimes cheaper that way. Remove LIMIT or use an exact match like <code>WHERE col = 'exact_value'</code> to force the planner to show the index.` :
      s.indexType === 'composite' ? `💡 <b style="color:var(--text)">Composite index tip:</b> Your WHERE clause must use the <b>leftmost column first</b>, then add more columns.<br>
      ✅ Index on <code style="color:#c084fc">(col_a, col_b)</code> → query with <code style="color:#c084fc">WHERE col_a = x AND col_b = y</code><br>
      ❌ Querying only the right column (<code>col_b</code> alone) will NOT use the composite index.<br>
      🚫 <b style="color:var(--amber)">Avoid LIMIT in your test query.</b> LIMIT changes the planner's cost model — it may choose Parallel Seq Scan over your index. Remove LIMIT to validate cleanly.` :
      `💡 <b style="color:var(--text)">Partial index tip:</b> Your query's WHERE clause must include the <b>exact same condition</b> as the index.<br>
      ✅ Index has <code style="color:#34d399">WHERE paid_at IS NULL</code> → query must also have <code style="color:#34d399">WHERE paid_at IS NULL</code><br>
      ❌ Without matching that condition, PostgreSQL ignores the partial index entirely.<br>
      🚫 <b style="color:var(--amber)">Avoid LIMIT in your test query.</b> LIMIT can cause the planner to prefer Seq Scan. Remove it for a clean validation.`}
    </div>` : ''}
  </div>
  <div style="display:flex;align-items:center;gap:14px;flex-wrap:wrap">
    <button class="btn btn-primary" id="lab-run-${idx}" onclick="runLabSlot(${idx})" style="padding:9px 22px">▶ Create &amp; Validate</button>
    <span style="font-size:.7rem;color:var(--muted)">Creates index + EXPLAIN ANALYZE on <b style="color:var(--fast)">hospital_fast</b></span>
  </div>
  ${resultBlock}
</div>`;
}

function renderLabAll() {
  document.getElementById('lab-slots').innerHTML = labSlots.map((_,i)=>renderLabSlot(i)).join('');
  updateLabProgress();
}

function labField(idx, field, val) { labSlots[idx][field]=val; saveLabSlots(); }

function labSqlLive(idx, val) {
  labSlots[idx].createSql = val;
  labSlots[idx].indexName = extractIndexName(val);
  labSlots[idx].indexType = detectIndexType(val);
  saveLabSlots();
}

async function runLabSlot(idx) {
  const scEl=document.getElementById(`lab-scenario-${idx}`), jEl=document.getElementById(`lab-just-${idx}`), sEl=document.getElementById(`lab-sql-${idx}`), qEl=document.getElementById(`lab-query-${idx}`);
  if(scEl) labSlots[idx].scenario=scEl.value;
  if(jEl) labSlots[idx].justification=jEl.value;
  if(sEl){ labSlots[idx].createSql=sEl.value; labSlots[idx].indexName=extractIndexName(sEl.value); labSlots[idx].indexType=detectIndexType(sEl.value); }
  if(qEl) labSlots[idx].testQuery=qEl.value;
  const s=labSlots[idx];

  if (!s.scenario.trim())      { alert('Describe the problem you identified first.');           return; }
  if (!s.justification.trim()) { alert('Paste the supporting quote from the audit report first.'); return; }
  if (!s.createSql.trim())     { alert('Write your CREATE INDEX statement.');                      return; }
  if (!s.testQuery.trim())     { alert('Write your test query.');                                   return; }

  const btn=document.getElementById(`lab-run-${idx}`);
  if(btn){btn.disabled=true;btn.innerHTML='<span class="spin"></span> Running…';}
  labSlots[idx].status='running'; saveLabSlots();

  try {
    const r=await fetch('/api/index-lab/run',{
      method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({create_sql:s.createSql,test_query:s.testQuery,index_name:s.indexName})
    }).then(x=>x.json());

    if(!r.ok){
      labSlots[idx].status='error';
      labSlots[idx].errorMsg=r.create_error||r.query_error||r.error||'Unknown error';
    } else {
      labSlots[idx].status      =r.index_used?'used':'not_used';
      labSlots[idx].scanType    =r.scan_type||'';
      labSlots[idx].queryMs     =r.ms||0;
      labSlots[idx].planSnippet =r.plan||'';
      labSlots[idx].rowsReturned=r.rows_returned||0;
      labSlots[idx].errorMsg    =r.query_error||'';
    }
  } catch(e){
    labSlots[idx].status='error';
    labSlots[idx].errorMsg='Network error: '+e.message;
  }

  saveLabSlots();
  const el=document.getElementById(`lab-slot-${idx}`);
  if(el) el.outerHTML=renderLabSlot(idx);
  updateLabProgress();
}

function clearLabSlot(idx){
  if(!confirm(`Clear slot #${idx+1}? The index stays in the database.`)) return;
  labSlots[idx]=blankSlot(idx); saveLabSlots();
  const el=document.getElementById(`lab-slot-${idx}`);
  if(el) el.outerHTML=renderLabSlot(idx);
  updateLabProgress();
}

document.querySelector('.tab[data-page="indexlab"]').addEventListener('click', renderLabAll);
</script>
</body>
</html>"""


@app.route("/")
def index():
    return render_template_string(HTML)


if __name__ == "__main__":
    print("\n" + "="*58)
    print("  🏥 Hospital DB — Advanced Database Final Project")
    print("  Open: http://localhost:5000")
    print("  Databases: hospital_slow  |  hospital_fast")
    print("="*58 + "\n")
    app.run(debug=True, port=5000)
