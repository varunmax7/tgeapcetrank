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
from flask import Flask, request, jsonify, render_template, g

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "database", "eapcet.db")

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


if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 5001))
    debug = os.environ.get("RENDER") is None  # debug only locally
    app.run(host="0.0.0.0", port=port, debug=debug)