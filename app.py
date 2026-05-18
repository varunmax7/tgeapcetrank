"""
Flask backend for TG EAPCET Rank Predictor.
Routes:
    GET /                — form page (Step 5 will flesh out the template)
    GET /predict         — JSON: filters + paginated results
    GET /api/colleges    — JSON: flat list of matching colleges
    GET /api/branches    — JSON: branch dropdown data
    GET /api/meta        — JSON: caste/gender/phase/year choices

Query parameters for /predict and /api/colleges:
    caste      (required)  OC | BC_A | BC_B | BC_C | BC_D | BC_E |
                           SC_I | SC_II | SC_III | ST | EWS
    gender     (required)  BOYS | GIRLS
    year       (optional)  default 2025
    rank       (required)  student's EAPCET rank
    phase      (optional)  phase1 | phase2 | final_phase | all  (default: all)
    branches   (optional)  comma-separated branch codes (e.g. CSE,ECE,INF)

Run:
    python app.py
"""
import os
import sqlite3
from functools import wraps
from flask import Flask, request, jsonify, render_template, g, Response

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "database", "eapcet.db")

def init_analytics_db():
    try:
        # Ensure database directory exists
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
        db = sqlite3.connect(DB_PATH)
        db.execute('''
            CREATE TABLE IF NOT EXISTS search_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                rank INTEGER,
                caste TEXT,
                gender TEXT,
                phase TEXT,
                branches TEXT
            )
        ''')
        db.commit()
        db.close()
    except Exception as e:
        print(f"Error initializing analytics db: {e}")

init_analytics_db()

app = Flask(__name__)

# UI value -> DB value
CASTE_CHOICES = [
    ("OC", "OC"), ("BC_A", "BC-A"), ("BC_B", "BC-B"),
    ("BC_C", "BC-C"), ("BC_D", "BC-D"), ("BC_E", "BC-E"),
    ("SC_I", "SC-I"), ("SC_II", "SC-II"), ("SC_III", "SC-III"),
    ("ST", "ST"), ("EWS", "EWS"),
]
GENDER_CHOICES = [("BOYS", "Boys"), ("GIRLS", "Girls")]
PHASE_CHOICES = [
    ("phase1", "Phase 1"),
    ("phase2", "Phase 2"),
    ("final_phase", "Final Phase"),
    ("all", "All Phases"),
]
YEAR_CHOICES = [2025]

VALID_CASTES = {c for c, _ in CASTE_CHOICES}
VALID_GENDERS = {g for g, _ in GENDER_CHOICES}
VALID_PHASES = {p for p, _ in PHASE_CHOICES} - {"all"}


# ---------- DB helpers ----------
def get_db():
    db = getattr(g, "_db", None)
    if db is None:
        db = g._db = sqlite3.connect(DB_PATH)
        db.row_factory = sqlite3.Row
    return db


@app.teardown_appcontext
def close_db(exc):
    db = getattr(g, "_db", None)
    if db is not None:
        db.close()


# ---------- Validation ----------
def parse_filters(args):
    """Validate query params. Returns (filters_dict, error_message)."""
    try:
        year = int(args.get("year", 2025))
        rank = int(args.get("rank", 0))
    except (TypeError, ValueError):
        return None, "year and rank must be integers"

    caste = args.get("caste", "").strip()
    gender = args.get("gender", "").strip()
    phase = args.get("phase", "all").strip() or "all"
    branches_raw = args.get("branches", "").strip()
    branches = [b.strip() for b in branches_raw.split(",") if b.strip()] if branches_raw else []

    if caste not in VALID_CASTES:
        return None, f"caste must be one of: {sorted(VALID_CASTES)}"
    if gender not in VALID_GENDERS:
        return None, f"gender must be one of: {sorted(VALID_GENDERS)}"
    if phase != "all" and phase not in VALID_PHASES:
        return None, f"phase must be one of: {sorted(VALID_PHASES) + ['all']}"
    if rank < 1:
        return None, "rank must be >= 1"

    return {
        "year": year,
        "caste": caste,
        "gender": gender,
        "phase": phase,
        "rank": rank,
        "branches": branches,
    }, None


# ---------- Query ----------
def query_colleges(filters, limit=500):
    sql = [
        "SELECT inst_code, institute_name, place, dist_code,",
        "       co_education, college_type, branch_code, branch_name,",
        "       affiliated_to, phase, caste, gender, closing_rank, year",
        "FROM allotments",
        "WHERE caste = ? AND gender = ? AND year = ?",
        "  AND closing_rank >= ?",
    ]
    params = [
        filters["caste"], filters["gender"], filters["year"],
        filters["rank"],
    ]

    if filters["phase"] != "all":
        sql.append("  AND phase = ?")
        params.append(filters["phase"])

    if filters["branches"]:
        placeholders = ",".join("?" for _ in filters["branches"])
        sql.append(f"  AND branch_code IN ({placeholders})")
        params.extend(filters["branches"])

    sql.append("ORDER BY closing_rank ASC, inst_code ASC")
    sql.append(f"LIMIT {int(limit)}")

    cur = get_db().execute("\n".join(sql), params)
    return [dict(row) for row in cur.fetchall()]


# ---------- Routes ----------
@app.route("/")
def index():
    db = get_db()
    branches = [dict(r) for r in db.execute(
        "SELECT DISTINCT branch_code, branch_name FROM allotments ORDER BY branch_code"
    ).fetchall()]
    return render_template(
        "index.html",
        castes=CASTE_CHOICES, genders=GENDER_CHOICES,
        phases=PHASE_CHOICES, years=YEAR_CHOICES, branches=branches,
    )


@app.route("/predict")
def predict():
    filters, err = parse_filters(request.args)
    if err:
        return jsonify({"error": err}), 400
        
    # Log the user's search activity
    try:
        db = get_db()
        branches_str = ",".join(filters.get("branches", []))
        db.execute('''
            INSERT INTO search_logs (rank, caste, gender, phase, branches)
            VALUES (?, ?, ?, ?, ?)
        ''', (
            filters.get("rank"), 
            filters.get("caste"), 
            filters.get("gender"), 
            filters.get("phase"), 
            branches_str
        ))
        db.commit()
    except Exception as e:
        print(f"Error logging search activity: {e}")

    results = query_colleges(filters)
    return jsonify({"count": len(results), "filters": filters, "results": results})


@app.route("/api/colleges")
def api_colleges():
    filters, err = parse_filters(request.args)
    if err:
        return jsonify({"error": err}), 400
    return jsonify(query_colleges(filters))


@app.route("/api/branches")
def api_branches():
    rows = get_db().execute(
        "SELECT DISTINCT branch_code, branch_name FROM allotments ORDER BY branch_code"
    ).fetchall()
    return jsonify([dict(r) for r in rows])


@app.route("/api/meta")
def api_meta():
    return jsonify({
        "castes": [{"value": v, "label": l} for v, l in CASTE_CHOICES],
        "genders": [{"value": v, "label": l} for v, l in GENDER_CHOICES],
        "phases": [{"value": v, "label": l} for v, l in PHASE_CHOICES],
        "years": YEAR_CHOICES,
    })


# ---------- Admin / Analytics ----------
def check_auth(username, password):
    """Check if a username / password combination is valid."""
    return username == 'techmax' and password == 'mgitgriet123'

def authenticate():
    """Sends a 401 response that enables basic auth"""
    return Response(
    'Could not verify your access level for that URL.\n'
    'You have to login with proper credentials', 401,
    {'WWW-Authenticate': 'Basic realm="Login Required"'})

def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        if not auth or not check_auth(auth.username, auth.password):
            return authenticate()
        return f(*args, **kwargs)
    return decorated

@app.route("/admin")
@requires_auth
def admin():
    return render_template("admin.html")

@app.route("/admin/export/csv")
@requires_auth
def export_csv():
    import csv
    import io
    from flask import Response
    
    db = get_db()
    rows = db.execute("SELECT * FROM search_logs ORDER BY timestamp DESC").fetchall()
    
    si = io.StringIO()
    cw = csv.writer(si)
    
    if rows:
        cw.writerow(rows[0].keys())
        for row in rows:
            cw.writerow([row[col] for col in rows[0].keys()])
    else:
        cw.writerow(["id", "timestamp", "rank", "caste", "gender", "phase", "branches"])
        
    return Response(
        si.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment;filename=search_logs.csv"}
    )

@app.route("/api/analytics")
@requires_auth
def api_analytics():
    db = get_db()
    
    # Total searches
    total_searches = db.execute("SELECT COUNT(*) FROM search_logs").fetchone()[0]
    
    # Searches by caste
    castes = [dict(r) for r in db.execute("SELECT caste, COUNT(*) as count FROM search_logs GROUP BY caste").fetchall()]
    
    # Searches by gender
    genders = [dict(r) for r in db.execute("SELECT gender, COUNT(*) as count FROM search_logs GROUP BY gender").fetchall()]
    
    # Branches parsing
    branches_raw = [r[0] for r in db.execute("SELECT branches FROM search_logs WHERE branches != ''").fetchall()]
    branch_counts = {}
    for row in branches_raw:
        for branch in row.split(','):
            branch = branch.strip()
            if branch:
                branch_counts[branch] = branch_counts.get(branch, 0) + 1
                
    popular_branches = [{"branch": k, "count": v} for k, v in sorted(branch_counts.items(), key=lambda item: item[1], reverse=True)[:10]]
    
    # Daily trends (last 7 days)
    trends = [dict(r) for r in db.execute("SELECT date(timestamp) as date, COUNT(*) as count FROM search_logs GROUP BY date(timestamp) ORDER BY date(timestamp) DESC LIMIT 7").fetchall()]

    # Rank Ranges calculation
    ranks = [r[0] for r in db.execute("SELECT rank FROM search_logs WHERE rank IS NOT NULL").fetchall()]
    rank_ranges = {
        "1 - 10k": 0,
        "10k - 25k": 0,
        "25k - 50k": 0,
        "50k - 75k": 0,
        "75k - 100k": 0,
        "100k+": 0
    }
    for rank in ranks:
        try:
            r = int(rank)
            if r <= 10000: rank_ranges["1 - 10k"] += 1
            elif r <= 25000: rank_ranges["10k - 25k"] += 1
            elif r <= 50000: rank_ranges["25k - 50k"] += 1
            elif r <= 75000: rank_ranges["50k - 75k"] += 1
            elif r <= 100000: rank_ranges["75k - 100k"] += 1
            else: rank_ranges["100k+"] += 1
        except (ValueError, TypeError):
            pass

    return jsonify({
        "total_searches": total_searches,
        "castes": castes,
        "genders": genders,
        "popular_branches": popular_branches,
        "trends": trends[::-1],  # Chronological order
        "rank_ranges": rank_ranges
    })


if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 5001))
    debug = os.environ.get("RENDER") is None  # debug only locally
    app.run(host="0.0.0.0", port=port, debug=debug)