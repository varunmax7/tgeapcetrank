# 🎓 TG EAPCET Rank Predictor

> **Find the best engineering colleges you can get into based on your TG EAPCET rank.**

A web application that helps Telangana EAPCET aspirants discover which engineering colleges and branches they are eligible for, based on their rank, caste, gender, and preferred branches. Built using real **TG EAPCET 2025 last-rank (closing rank) data** across all counselling phases.

🔗 **Live Demo**: [tg-eapcet-rank-predictor.onrender.com](https://tg-eapcet-rank-predictor.onrender.com)

---

## 📌 Problem Statement

Every year, **~2 lakh+ students** appear for the Telangana EAPCET exam. After results are announced, the biggest challenge students face is:

> *"With my rank, which colleges and branches can I actually get?"*

Currently, students have to:
- Manually sift through **hundreds of pages** of PDF closing-rank statements released by TSCHE
- Cross-reference ranks across **3 counselling phases** (Phase 1, Phase 2, Final Phase)
- Filter by their specific **caste category** and **gender** — a tedious, error-prone process
- Rely on outdated or incomplete third-party tools

**This app solves that problem** by consolidating all official closing-rank data into a single, searchable, mobile-friendly interface where students simply enter their rank and instantly see every college + branch they qualify for.

---

## ✨ Features

- 🔍 **Instant Search** — Enter your rank and get results in milliseconds
- 🏫 **59,800+ Records** — Covering **173 colleges** across **46 branches**
- 📊 **Multi-Phase Data** — Includes Phase 1, Phase 2, and Final Phase closing ranks
- 🎯 **Smart Filters** — Filter by caste (OC, BC-A to BC-E, SC, ST, EWS), gender, phase, and branches
- 📱 **Mobile-Friendly** — Responsive design with touch-friendly card layout on phones
- ⚡ **Sortable Results** — Click any column header to sort by rank, college, branch, etc.
- 🔎 **Branch Search** — Quickly find and select specific branches (CSE, ECE, AI, etc.)

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|-----------|
| **Backend** | Python 3 + Flask |
| **Database** | SQLite3 (bundled, zero-config) |
| **Frontend** | Vanilla HTML, CSS, JavaScript |
| **Production Server** | Gunicorn |
| **Deployment** | Render (Free Tier) |

### Why This Stack?

- **Flask + SQLite** — Lightweight, zero-dependency backend. No external database server needed. The entire dataset fits in a ~2MB SQLite file bundled with the app.
- **Vanilla Frontend** — No heavy frameworks. The app loads instantly with zero JavaScript bundle overhead.
- **Gunicorn** — Production-grade WSGI server for reliable performance on Render.

---

## 📁 Project Structure

```
TG EAPCET Rank Predictor/
├── app.py                  # Flask application (routes, API, query logic)
├── requirements.txt        # Python dependencies
├── database/
│   └── eapcet.db           # SQLite database with all closing-rank data
├── static/
│   ├── style.css           # Responsive CSS with mobile breakpoints
│   └── app.js              # Client-side logic (search, sort, render)
├── templates/
│   └── index.html          # Jinja2 HTML template
├── scripts/                # (Dev only) Data extraction & DB build scripts
│   ├── extract_data.py     # PDF → CSV extraction using pdfplumber
│   ├── build_database.py   # CSV → SQLite database builder
│   └── verify_database.py  # Database integrity verification
└── data/                   # (Dev only) Raw PDFs and processed CSVs
    ├── raw/                # Original TSCHE PDF documents
    └── processed/          # Cleaned CSV files
```

---

## 🚀 Getting Started

### Prerequisites

- Python 3.8+
- pip

### Local Development

```bash
# 1. Clone the repository
git clone https://github.com/varunmax7/tgeapcetrank.git
cd tgeapcetrank

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run the development server
python app.py

# 4. Open in browser
# → http://localhost:5001
```

The app starts immediately — no database setup needed (SQLite DB is pre-built and included).

---

## 📡 API Documentation

The app exposes a RESTful JSON API alongside the web interface.

### `GET /predict`

Returns colleges matching the given filters.

**Parameters:**

| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `rank` | int | ✅ | Student's EAPCET rank |
| `caste` | string | ✅ | `OC`, `BC_A`, `BC_B`, `BC_C`, `BC_D`, `BC_E`, `SC_I`, `SC_II`, `SC_III`, `ST`, `EWS` |
| `gender` | string | ✅ | `BOYS` or `GIRLS` |
| `year` | int | ❌ | Default: `2025` |
| `phase` | string | ❌ | `phase1`, `phase2`, `final_phase`, or `all` (default: `all`) |
| `branches` | string | ❌ | Comma-separated branch codes (e.g., `CSE,ECE,INF`) |

**Example Request:**
```
GET /predict?rank=15000&caste=OC&gender=BOYS&phase=all
```

**Example Response:**
```json
{
  "count": 42,
  "filters": {
    "year": 2025,
    "caste": "OC",
    "gender": "BOYS",
    "phase": "all",
    "rank": 15000,
    "branches": []
  },
  "results": [
    {
      "inst_code": "JNTH",
      "institute_name": "JNTUH COLLEGE OF ENGINEERING HYDERABAD",
      "place": "KUKATPALLY",
      "branch_code": "CSE",
      "branch_name": "COMPUTER SCIENCE AND ENGINEERING",
      "phase": "final_phase",
      "closing_rank": 15234,
      "college_type": "UNIV",
      ...
    }
  ]
}
```

### `GET /api/branches`

Returns all available branches.

### `GET /api/meta`

Returns available filter options (castes, genders, phases, years).

---

## 🌐 Deployment (Render)

1. Push code to GitHub
2. Go to [render.com](https://render.com) → **New → Web Service**
3. Connect the GitHub repo
4. Configure:
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn app:app`
   - **Plan**: Free
5. Deploy 🚀

---

## 📊 Data Source

All closing-rank data is sourced from the **official TSCHE (Telangana State Council of Higher Education)** last-rank statements for TG EAPCET 2025 counselling:

- **Phase 1** closing ranks
- **Phase 2** closing ranks
- **Final Phase** closing ranks

The data was extracted from official PDF documents using `pdfplumber`, cleaned with `pandas`, and loaded into SQLite.

---

## ⚠️ Disclaimer

- Closing ranks shown are based on **TG EAPCET 2025 last-rank statements only**
- Actual cutoffs in future years **will differ** based on factors like number of applicants, seat availability, and policy changes
- **Special category seats** (PH, NCC, Sports, CAP) are **not included**
- This tool is for **reference and guidance only** — always verify with official TSCHE notifications

---

## 📄 License

This project is open source and available under the [MIT License](LICENSE).

---

## 🤝 Contributing

Contributions are welcome! If you'd like to:
- Add data for previous years
- Improve the UI/UX
- Add new features (college comparison, seat matrix, etc.)

Feel free to open an issue or submit a pull request.

---

<p align="center">
  Built with ❤️ for Telangana EAPCET aspirants
</p>
