const form = document.getElementById('predictor-form');
const submitBtn = document.getElementById('submit-btn');
const resultsCard = document.getElementById('results-card');
const resultsBody = document.getElementById('results-body');
const mobileResults = document.getElementById('mobile-results');
const resultCount = document.getElementById('result-count');
const statusMsg = document.getElementById('status-msg');

const branchSearch = document.getElementById('branch_search');
const branchList = document.getElementById('branch-list');
const branchCount = document.getElementById('branch-count');
const selectAllBtn = document.getElementById('select-all-branches');
const clearBranchesBtn = document.getElementById('clear-branches');

let currentResults = [];
let currentSort = { col: 'closing_rank', dir: 'asc' };

function updateBranchCount() {
    const n = branchList.querySelectorAll('input:checked').length;
    branchCount.textContent = `${n} selected`;
}

branchSearch.addEventListener('input', (e) => {
    const q = e.target.value.toLowerCase().trim();
    branchList.querySelectorAll('.branch-chip').forEach(chip => {
        const text = chip.textContent.toLowerCase();
        chip.classList.toggle('hidden', q && !text.includes(q));
    });
});

selectAllBtn.addEventListener('click', () => {
    branchList.querySelectorAll('.branch-chip:not(.hidden) input').forEach(cb => cb.checked = true);
    updateBranchCount();
});

clearBranchesBtn.addEventListener('click', () => {
    branchList.querySelectorAll('input:checked').forEach(cb => cb.checked = false);
    updateBranchCount();
});

branchList.addEventListener('change', updateBranchCount);

form.addEventListener('submit', async (e) => {
    e.preventDefault();
    await runQuery();
});

form.addEventListener('reset', () => {
    setTimeout(() => {
        updateBranchCount();
        resultsCard.hidden = true;
        statusMsg.textContent = '';
        statusMsg.className = 'status';
    }, 0);
});

async function runQuery() {
    const rank = parseInt(document.getElementById('rank').value, 10);
    if (!rank || rank < 1) {
        showError('Please enter a valid rank.');
        return;
    }

    const branches = Array.from(branchList.querySelectorAll('input:checked'))
        .map(cb => cb.value).join(',');

    const params = new URLSearchParams({
        year: document.getElementById('year').value,
        caste: document.getElementById('caste').value,
        gender: document.getElementById('gender').value,
        phase: document.getElementById('phase').value,
        rank: rank,
    });
    if (branches) params.set('branches', branches);

    submitBtn.disabled = true;
    submitBtn.innerHTML = '<span class="loading-spinner"></span>Searching…';
    statusMsg.textContent = '';
    statusMsg.className = 'status';

    try {
        const res = await fetch(`/predict?${params.toString()}`);
        const data = await res.json();

        if (!res.ok) {
            showError(data.error || `Server error (HTTP ${res.status})`);
            return;
        }

        currentResults = data.results;
        resultsCard.hidden = false;
        sortAndRender();
        resultCount.textContent = `(${data.count} ${data.count === 1 ? 'college' : 'colleges'})`;
        statusMsg.textContent = data.count === 500
            ? 'Showing first 500 results — narrow your filters for more precision.'
            : '';

        // Scroll to results on mobile
        if (window.innerWidth <= 540) {
            resultsCard.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
    } catch (err) {
        showError(`Request failed: ${err.message}`);
    } finally {
        submitBtn.disabled = false;
        submitBtn.textContent = 'Find Colleges';
    }
}

function showError(msg) {
    resultsCard.hidden = false;
    resultsBody.innerHTML = `<tr><td colspan="7" class="empty">${escapeHtml(msg)}</td></tr>`;
    mobileResults.innerHTML = `<div class="empty">${escapeHtml(msg)}</div>`;
    resultCount.textContent = '';
    statusMsg.textContent = msg;
    statusMsg.className = 'status error';
}

document.querySelectorAll('th.sortable').forEach(th => {
    th.addEventListener('click', () => {
        const col = th.dataset.sort;
        if (currentSort.col === col) {
            currentSort.dir = currentSort.dir === 'asc' ? 'desc' : 'asc';
        } else {
            currentSort.col = col;
            currentSort.dir = 'asc';
        }
        sortAndRender();
    });
});

function sortAndRender() {
    const { col, dir } = currentSort;
    const mul = dir === 'asc' ? 1 : -1;
    const sorted = [...currentResults].sort((a, b) => {
        const av = a[col], bv = b[col];
        if (typeof av === 'number' && typeof bv === 'number') return (av - bv) * mul;
        return String(av).localeCompare(String(bv)) * mul;
    });

    document.querySelectorAll('th.sortable').forEach(th => {
        th.classList.remove('sort-asc', 'sort-desc');
        if (th.dataset.sort === col) th.classList.add(`sort-${dir}`);
    });

    renderTable(sorted);
    renderMobileCards(sorted);
}

/* Desktop table rendering */
function renderTable(rows) {
    if (!rows.length) {
        resultsBody.innerHTML = `<tr><td colspan="7" class="empty">No colleges match these filters. Try widening the rank range or adding branches.</td></tr>`;
        return;
    }
    resultsBody.innerHTML = rows.map(r => `
    <tr>
      <td class="rank-cell">${r.closing_rank.toLocaleString()}</td>
      <td class="code-cell">${escapeHtml(r.inst_code)}</td>
      <td>${escapeHtml(r.institute_name)}</td>
      <td>${escapeHtml(r.place || '')}</td>
      <td><span class="code-cell">${escapeHtml(r.branch_code)}</span> ${escapeHtml(r.branch_name)}</td>
      <td><span class="phase-badge phase-${r.phase}">${phaseLabel(r.phase)}</span></td>
      <td>${escapeHtml(r.college_type || '')}</td>
    </tr>
  `).join('');
}

/* Mobile card rendering */
function renderMobileCards(rows) {
    if (!rows.length) {
        mobileResults.innerHTML = `<div class="empty">No colleges match these filters. Try widening the rank range or adding branches.</div>`;
        return;
    }
    mobileResults.innerHTML = rows.map(r => `
    <div class="mobile-result-card">
      <div class="college-name">${escapeHtml(r.institute_name)}</div>
      <div class="college-meta">
        <span class="meta-tag rank">Rank ${r.closing_rank.toLocaleString()}</span>
        <span class="meta-tag branch">${escapeHtml(r.branch_code)}</span>
        <span class="phase-badge phase-${r.phase}">${phaseLabel(r.phase)}</span>
      </div>
      <div class="bottom-row">
        <span>${escapeHtml(r.place || '')}${r.college_type ? ' · ' + escapeHtml(r.college_type) : ''}</span>
        <span class="code-cell" style="font-size:12px">${escapeHtml(r.inst_code)}</span>
      </div>
    </div>
  `).join('');
}

function phaseLabel(p) {
    return { phase1: 'Phase 1', phase2: 'Phase 2', final_phase: 'Final' }[p] || p;
}

function escapeHtml(s) {
    if (s == null) return '';
    return String(s)
        .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
}

updateBranchCount();