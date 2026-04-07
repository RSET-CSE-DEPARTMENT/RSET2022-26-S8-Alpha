/**
 * Case Scraper Admin Dashboard — Frontend Logic
 */

// ===== STATE =====
let cases = [];
let scrapePollingInterval = null;
let currentScrapeCNR = null;

// ===== DOM ELEMENTS =====
const caseTableBody = document.getElementById('caseTableBody');
const searchInput = document.getElementById('searchInput');
const totalCasesEl = document.getElementById('totalCases');
const addCaseBtn = document.getElementById('addCaseBtn');
const refreshBtn = document.getElementById('refreshBtn');

// Modal elements
const addCaseModal = document.getElementById('addCaseModal');
const addCaseForm = document.getElementById('addCaseForm');

// Scrape panel elements
const scrapePanel = document.getElementById('scrapePanel');
const scrapeMessage = document.getElementById('scrapeMessage');
const progressBar = document.getElementById('progressBar');
const captchaSection = document.getElementById('captchaSection');
const captchaImage = document.getElementById('captchaImage');
const captchaInput = document.getElementById('captchaInput');
const captchaSubmitBtn = document.getElementById('captchaSubmitBtn');

// Result panel
const resultPanel = document.getElementById('resultPanel');
const resultContent = document.getElementById('resultContent');

const toastContainer = document.getElementById('toastContainer');


// ===== TOAST =====
function showToast(message, type = 'info') {
    const icons = { success: '✓', error: '✕', info: 'ℹ' };
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.innerHTML = `<span>${icons[type] || 'ℹ'}</span> ${message}`;
    toastContainer.appendChild(toast);
    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateX(100%)';
        toast.style.transition = 'all 0.3s ease';
        setTimeout(() => toast.remove(), 300);
    }, 4000);
}


// ===== FETCH CASES =====
async function loadCases(search = '') {
    try {
        const url = search ? `/api/cases?search=${encodeURIComponent(search)}` : '/api/cases';
        const res = await fetch(url);
        const data = await res.json();

        if (data.success) {
            cases = data.cases;
            renderCases();
        } else {
            showToast(data.error || 'Failed to load cases', 'error');
        }
    } catch (err) {
        showToast('Connection error: ' + err.message, 'error');
    }
}


// ===== RENDER CASES TABLE =====
function renderCases() {
    totalCasesEl.textContent = cases.length;

    if (cases.length === 0) {
        caseTableBody.innerHTML = `
            <tr>
                <td colspan="6">
                    <div class="empty-state">
                        <div class="empty-icon">📂</div>
                        <p>No cases found. Add a new case to get started.</p>
                    </div>
                </td>
            </tr>
        `;
        return;
    }

    caseTableBody.innerHTML = cases.map(c => {
        const statusClass = c.case_status
            ? (c.case_status.toLowerCase().includes('disposed') ? 'active' : 'pending')
            : 'unknown';
        const statusLabel = c.case_status || 'Not Scraped';

        return `
            <tr>
                <td class="cnr-cell">${c.cnr_number || '—'}</td>
                <td>${c.district || '<span style="color:var(--text-muted)">—</span>'}</td>
                <td>${c.court || '<span style="color:var(--text-muted)">—</span>'}</td>
                <td><span class="case-status-chip ${statusClass}">${statusLabel}</span></td>
                <td>${c.next_hearing_date || '—'}</td>
                <td>
                    <div class="actions-cell">
                        <button class="btn btn-primary btn-sm" onclick="startScrape('${c._id}')"
                            ${(!c.district || !c.court) ? 'disabled title="Add district & court first"' : ''}>
                            ⚡ Scrape
                        </button>
                        ${c.scraped_data ? '<button class="btn btn-secondary btn-sm" onclick="viewResult(\'' + c._id + '\')">📄 View</button>' : ''}
                    </div>
                </td>
            </tr>
        `;
    }).join('');
}


// ===== ADD CASE MODAL =====
function openAddCaseModal() {
    addCaseModal.classList.add('active');
    document.getElementById('newCnr').focus();
}

function closeAddCaseModal() {
    addCaseModal.classList.remove('active');
    addCaseForm.reset();
}

async function handleAddCase(e) {
    e.preventDefault();
    const cnr = document.getElementById('newCnr').value.trim();
    const district = document.getElementById('newDistrict').value.trim();
    const court = document.getElementById('newCourt').value.trim();

    if (!cnr || !district || !court) {
        showToast('All fields are required.', 'error');
        return;
    }

    try {
        const res = await fetch('/api/cases', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ cnr_number: cnr, district, court }),
        });
        const data = await res.json();
        if (data.success) {
            showToast(data.message, 'success');
            closeAddCaseModal();
            loadCases();
        } else {
            showToast(data.error, 'error');
        }
    } catch (err) {
        showToast('Error adding case: ' + err.message, 'error');
    }
}


// ===== START SCRAPING =====
async function startScrape(caseId) {
    const caseObj = cases.find(c => c._id === caseId);
    if (!caseObj) return;

    if (!caseObj.district || !caseObj.court) {
        showToast('Please add district and court info first.', 'error');
        return;
    }

    currentScrapeCNR = caseObj.cnr_number;

    try {
        const res = await fetch('/api/scrape', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                district: caseObj.district,
                court: caseObj.court,
                cnr_number: caseObj.cnr_number,
            }),
        });
        const data = await res.json();

        if (data.success) {
            showToast('Scraping started!', 'info');
            showScrapePanel();
            startPolling();
        } else {
            showToast(data.error, 'error');
        }
    } catch (err) {
        showToast('Error starting scrape: ' + err.message, 'error');
    }
}


// ===== SCRAPE STATUS POLLING =====
function showScrapePanel() {
    scrapePanel.classList.add('active');
    captchaSection.classList.remove('active');
    resultPanel.classList.remove('active');
    progressBar.style.width = '20%';
}

function hideScrapePanel() {
    scrapePanel.classList.remove('active');
    captchaSection.classList.remove('active');
}

function startPolling() {
    if (scrapePollingInterval) clearInterval(scrapePollingInterval);
    scrapePollingInterval = setInterval(pollScrapeStatus, 1500);
}

function stopPolling() {
    if (scrapePollingInterval) {
        clearInterval(scrapePollingInterval);
        scrapePollingInterval = null;
    }
}

async function pollScrapeStatus() {
    try {
        const res = await fetch('/api/scrape-status');
        const data = await res.json();

        scrapeMessage.textContent = data.message || '';

        switch (data.status) {
            case 'running':
                progressBar.style.width = '60%';
                captchaSection.classList.remove('active');
                break;

            case 'waiting_captcha':
                progressBar.style.width = '40%';
                if (data.captcha_image && !captchaSection.classList.contains('active')) {
                    captchaImage.src = 'data:image/png;base64,' + data.captcha_image;
                    captchaSection.classList.add('active');
                    captchaInput.value = '';
                    captchaInput.focus();
                }
                break;

            case 'completed':
                progressBar.style.width = '100%';
                stopPolling();
                showToast('Scraping completed!', 'success');
                captchaSection.classList.remove('active');

                if (data.result) {
                    displayResult(data.result);
                    // Auto-save to MongoDB
                    saveResult(currentScrapeCNR, data.result);
                }

                setTimeout(() => hideScrapePanel(), 2000);
                loadCases(); // Refresh table
                break;

            case 'error':
                progressBar.style.width = '100%';
                progressBar.style.background = 'var(--danger)';
                stopPolling();
                showToast(data.error || 'Scraping failed.', 'error');
                setTimeout(() => {
                    hideScrapePanel();
                    progressBar.style.background = '';
                }, 3000);
                break;

            case 'idle':
                stopPolling();
                break;
        }
    } catch (err) {
        console.error('Polling error:', err);
    }
}


// ===== SUBMIT CAPTCHA =====
async function submitCaptcha() {
    const answer = captchaInput.value.trim();
    if (!answer) {
        showToast('Please enter the captcha code.', 'error');
        return;
    }

    captchaSubmitBtn.disabled = true;
    captchaSubmitBtn.innerHTML = '<span class="spinner"></span> Submitting...';

    try {
        const res = await fetch('/api/captcha', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ answer }),
        });
        const data = await res.json();
        if (data.success) {
            showToast('Captcha submitted!', 'success');
            captchaSection.classList.remove('active');
        } else {
            showToast(data.error, 'error');
        }
    } catch (err) {
        showToast('Error submitting captcha: ' + err.message, 'error');
    } finally {
        captchaSubmitBtn.disabled = false;
        captchaSubmitBtn.innerHTML = '✓ Submit';
    }
}


// ===== SAVE RESULT =====
async function saveResult(cnr, result) {
    try {
        await fetch('/api/save-result', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ cnr_number: cnr, result }),
        });
    } catch (err) {
        console.error('Failed to save result:', err);
    }
}


// ===== DISPLAY RESULTS =====
function displayResult(result) {
    resultPanel.classList.add('active');
    const scraped = result.scraped_data || {};
    let html = '';

    // Case Details
    if (scraped['Case Details'] && typeof scraped['Case Details'] === 'object') {
        html += buildResultCard('📋 Case Details', scraped['Case Details']);
    }

    // Party Details
    if (scraped['Party Details'] && Array.isArray(scraped['Party Details'])) {
        html += buildResultCardArray('👥 Party Details', scraped['Party Details']);
    } else if (scraped['Party Details'] && typeof scraped['Party Details'] === 'object') {
        html += buildResultCard('👥 Party Details', scraped['Party Details']);
    }

    // Case History
    if (scraped['Case History'] && Array.isArray(scraped['Case History'])) {
        html += buildResultCardArray('📅 Case History', scraped['Case History']);
    }

    // Filed IAs
    if (scraped['Filed IAs'] && Array.isArray(scraped['Filed IAs'])) {
        html += buildResultCardArray('📝 Filed IAs', scraped['Filed IAs']);
    }

    // Order Details
    if (scraped['Order Details'] && Array.isArray(scraped['Order Details'])) {
        html += buildResultCardArray('⚖ Order Details', scraped['Order Details']);
    }

    // Network data
    if (result.network_data && result.network_data.length > 0) {
        html += `
            <div class="result-card">
                <div class="result-card-header" onclick="toggleResultCard(this)">
                    <h4>🌐 Network Data (${result.network_data.length} packets)</h4>
                    <span class="chevron">▼</span>
                </div>
                <div class="result-card-body">
                    <pre style="color:var(--text-secondary); font-size:12px; overflow-x:auto; white-space:pre-wrap; word-break:break-all;">${JSON.stringify(result.network_data, null, 2)}</pre>
                </div>
            </div>
        `;
    }

    resultContent.innerHTML = html;
}

function buildResultCard(title, obj) {
    if (typeof obj === 'string') {
        return `<div class="result-card"><div class="result-card-header"><h4>${title}</h4></div><div class="result-card-body expanded"><p style="color:var(--text-muted)">${obj}</p></div></div>`;
    }
    const rows = Object.entries(obj)
        .map(([k, v]) => `<tr><td>${k}</td><td>${Array.isArray(v) ? v.join(', ') : v}</td></tr>`)
        .join('');
    return `
        <div class="result-card">
            <div class="result-card-header expanded" onclick="toggleResultCard(this)">
                <h4>${title}</h4>
                <span class="chevron">▼</span>
            </div>
            <div class="result-card-body expanded">
                <table class="result-table">${rows}</table>
            </div>
        </div>
    `;
}

function buildResultCardArray(title, arr) {
    if (!arr.length) return '';
    let content = '';
    arr.forEach((item, i) => {
        if (typeof item === 'object') {
            const rows = Object.entries(item)
                .map(([k, v]) => `<tr><td>${k}</td><td>${Array.isArray(v) ? v.join(', ') : v}</td></tr>`)
                .join('');
            content += `
                <div style="margin-bottom:12px; padding-bottom:12px; border-bottom:1px solid var(--border-glass);">
                    <div style="font-size:11px;color:var(--text-muted);margin-bottom:6px;font-weight:600;">#${i + 1}</div>
                    <table class="result-table">${rows}</table>
                </div>
            `;
        } else {
            content += `<p style="color:var(--text-secondary);margin-bottom:4px;">${item}</p>`;
        }
    });
    return `
        <div class="result-card">
            <div class="result-card-header" onclick="toggleResultCard(this)">
                <h4>${title} <span style="font-weight:400;color:var(--text-muted);font-size:12px;">(${arr.length})</span></h4>
                <span class="chevron">▼</span>
            </div>
            <div class="result-card-body">${content}</div>
        </div>
    `;
}

function toggleResultCard(header) {
    header.classList.toggle('expanded');
    const body = header.nextElementSibling;
    body.classList.toggle('expanded');
}


// ===== VIEW SAVED RESULT =====
function viewResult(caseId) {
    const caseObj = cases.find(c => c._id === caseId);
    if (!caseObj || !caseObj.scraped_data) {
        showToast('No scraped data found.', 'error');
        return;
    }
    displayResult({ scraped_data: caseObj.scraped_data, network_data: caseObj.network_data || [] });
    // Scroll to result
    resultPanel.scrollIntoView({ behavior: 'smooth', block: 'start' });
}


// ===== EVENT LISTENERS =====
document.addEventListener('DOMContentLoaded', () => {
    loadCases();

    searchInput.addEventListener('input', debounce((e) => {
        loadCases(e.target.value);
    }, 400));

    addCaseBtn.addEventListener('click', openAddCaseModal);
    refreshBtn.addEventListener('click', () => loadCases(searchInput.value));
    addCaseForm.addEventListener('submit', handleAddCase);

    captchaSubmitBtn.addEventListener('click', submitCaptcha);
    captchaInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') submitCaptcha();
    });

    // Close modal on overlay click
    addCaseModal.addEventListener('click', (e) => {
        if (e.target === addCaseModal) closeAddCaseModal();
    });

    // Escape key
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') closeAddCaseModal();
    });
});


// ===== UTILS =====
function debounce(fn, delay) {
    let timeout;
    return function (...args) {
        clearTimeout(timeout);
        timeout = setTimeout(() => fn.apply(this, args), delay);
    };
}
