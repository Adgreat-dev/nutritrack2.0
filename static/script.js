/* ═══════════════════════════════════════════
   VerifAI — script.js
   Page routing · Auth validation · Analyzer logic · Results UI · PDF Export
   ═══════════════════════════════════════════ */

// ── Page Router ──────────────────────────────────────────────────────────────

const PAGES = ['landing', 'login', 'signup', 'analyzer'];

function showPage(name) {
    PAGES.forEach(p => {
        const el = document.getElementById(`page-${p}`);
        if (el) el.classList.toggle('hidden', p !== name);
    });

    // Show/hide main navbar (only on landing)
    const navbar = document.getElementById('navbar');
    if (navbar) navbar.style.display = name === 'landing' ? '' : 'none';

    // Scroll to top
    window.scrollTo({ top: 0 });

    // If going to analyzer, reset to upload state
    if (name === 'analyzer') resetAnalyzer();

    // Clear auth errors when switching pages
    clearAuthErrors();
}

function toggleMenu() {
    const links = document.getElementById('nav-links');
    if (links) links.classList.toggle('open');
}

// ── Google Auth placeholder ───────────────────────────────────────────────────

function handleGoogleAuth() {
    // TODO: Replace with real Google OAuth flow
    // e.g. firebase.auth().signInWithPopup(googleProvider)
    showPage('analyzer');
}

// ── Auth Validation ───────────────────────────────────────────────────────────

function clearAuthErrors() {
    document.querySelectorAll('.auth-error').forEach(el => {
        el.textContent = '';
        el.classList.remove('visible');
    });
    document.querySelectorAll('.auth-input').forEach(el => el.classList.remove('input-error'));
}

function showFieldError(fieldEl, errorEl, message) {
    if (fieldEl) fieldEl.classList.add('input-error');
    if (errorEl) {
        errorEl.textContent = message;
        errorEl.classList.add('visible');
    }
}

function validateEmail(email) {
    return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
}

function handleLogin() {
    clearAuthErrors();
    const emailInput = document.getElementById('login-email');
    const passInput = document.getElementById('login-password');
    const emailErr = document.getElementById('login-email-error');
    const passErr = document.getElementById('login-password-error');

    let valid = true;

    if (!emailInput.value.trim()) {
        showFieldError(emailInput, emailErr, 'Email address is required.');
        valid = false;
    } else if (!validateEmail(emailInput.value.trim())) {
        showFieldError(emailInput, emailErr, 'Please enter a valid email address.');
        valid = false;
    }

    if (!passInput.value) {
        showFieldError(passInput, passErr, 'Password is required.');
        valid = false;
    } else if (passInput.value.length < 6) {
        showFieldError(passInput, passErr, 'Password must be at least 6 characters.');
        valid = false;
    }

    if (valid) showPage('analyzer');
}

function handleSignup() {
    clearAuthErrors();
    const nameInput = document.getElementById('signup-name');
    const emailInput = document.getElementById('signup-email');
    const passInput = document.getElementById('signup-password');
    const nameErr = document.getElementById('signup-name-error');
    const emailErr = document.getElementById('signup-email-error');
    const passErr = document.getElementById('signup-password-error');

    let valid = true;

    if (!nameInput.value.trim()) {
        showFieldError(nameInput, nameErr, 'Full name is required.');
        valid = false;
    }

    if (!emailInput.value.trim()) {
        showFieldError(emailInput, emailErr, 'Email address is required.');
        valid = false;
    } else if (!validateEmail(emailInput.value.trim())) {
        showFieldError(emailInput, emailErr, 'Please enter a valid email address.');
        valid = false;
    }

    if (!passInput.value) {
        showFieldError(passInput, passErr, 'Password is required.');
        valid = false;
    } else if (passInput.value.length < 8) {
        showFieldError(passInput, passErr, 'Password must be at least 8 characters.');
        valid = false;
    }

    if (valid) showPage('analyzer');
}

// ── Analyzer State ────────────────────────────────────────────────────────────

let allIngredients = [];
let lastAnalysisData = null;

function resetAnalyzer() {
    allIngredients = [];
    lastAnalysisData = null;
    const uploadEl = document.getElementById('analyzer-upload');
    const loadingEl = document.getElementById('analyzer-loading');
    const resultEl = document.getElementById('analyzer-result');
    const fileInput = document.getElementById('file-input');

    if (uploadEl) uploadEl.classList.remove('hidden');
    if (loadingEl) loadingEl.classList.add('hidden');
    if (resultEl) resultEl.classList.add('hidden');
    if (fileInput) fileInput.value = '';

    // Reset loading steps
    document.querySelectorAll('.lstep').forEach(el => {
        el.classList.remove('active', 'done');
    });
}

// ── Loading Step Animation ────────────────────────────────────────────────────

const STEPS = [
    { id: 'lstep-1', label: 'Reading label...', ms: 600 },
    { id: 'lstep-2', label: 'Classifying ingredients...', ms: 1400 },
    { id: 'lstep-3', label: 'Verifying claims...', ms: 2400 },
    { id: 'lstep-4', label: 'Computing safety score...', ms: 3400 },
];

function runLoadingSteps() {
    const subEl = document.getElementById('loading-step');
    STEPS.forEach((step, i) => {
        setTimeout(() => {
            if (i > 0) {
                const prev = document.getElementById(STEPS[i - 1].id);
                if (prev) { prev.classList.remove('active'); prev.classList.add('done'); }
            }
            const curr = document.getElementById(step.id);
            if (curr) curr.classList.add('active');
            if (subEl) subEl.textContent = step.label;
        }, step.ms);
    });
}

// ── Drop Zone ─────────────────────────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', () => {

    const dropZone = document.getElementById('drop-zone');
    const fileInput = document.getElementById('file-input');
    if (!dropZone || !fileInput) return;

    dropZone.addEventListener('click', () => fileInput.click());

    dropZone.addEventListener('dragover', e => {
        e.preventDefault();
        dropZone.classList.add('dragover');
    });
    dropZone.addEventListener('dragleave', () => dropZone.classList.remove('dragover'));

    dropZone.addEventListener('drop', e => {
        e.preventDefault();
        dropZone.classList.remove('dragover');
        if (e.dataTransfer.files?.[0]) handleFile(e.dataTransfer.files[0]);
    });

    fileInput.addEventListener('change', e => {
        if (e.target.files?.[0]) handleFile(e.target.files[0]);
    });

    document.getElementById('reset-btn')?.addEventListener('click', resetAnalyzer);
    document.getElementById('download-pdf-btn')?.addEventListener('click', downloadPDF);
});

// ── Handle File Upload ────────────────────────────────────────────────────────

async function handleFile(file) {
    if (!file.type.startsWith('image/')) {
        alert('Please upload an image file (PNG, JPG, or WEBP).');
        return;
    }

    document.getElementById('analyzer-upload').classList.add('hidden');
    document.getElementById('analyzer-loading').classList.remove('hidden');
    runLoadingSteps();

    const formData = new FormData();
    formData.append('image', file);

    try {
        const res = await fetch('/api/analyze', { method: 'POST', body: formData });
        if (!res.ok) throw new Error(`Server error: ${res.status}`);
        const data = await res.json();
        lastAnalysisData = data;
        setTimeout(() => renderResults(data), 500);
    } catch (err) {
        console.error(err);
        alert('Something went wrong during analysis. Please try again.');
        resetAnalyzer();
    }
}

// ── Render Results ────────────────────────────────────────────────────────────

function renderResults(data) {
    document.getElementById('analyzer-loading').classList.add('hidden');
    document.getElementById('analyzer-result').classList.remove('hidden');

    document.getElementById('product-name').textContent = data.productName || 'Unknown Product';
    document.getElementById('result-category').textContent = data.category || 'Product';

    const score = Math.min(100, Math.max(0, data.score || 0));
    const scoreCircle = document.getElementById('score-circle');
    const scoreText = document.getElementById('score-text');
    const verdictEl = document.getElementById('score-verdict');

    let color = 'var(--bad)';
    let verdict = 'Caution';
    if (score >= 70) { color = 'var(--good)'; verdict = 'Healthy'; }
    else if (score >= 40) { color = 'var(--neutral)'; verdict = 'Moderate'; }

    setTimeout(() => {
        const circumference = 263.9;
        scoreCircle.style.strokeDashoffset = circumference - (circumference * score / 100);
        scoreCircle.style.stroke = color;

        let current = 0;
        const step = Math.max(1, Math.ceil(score / 40));
        const timer = setInterval(() => {
            current = Math.min(current + step, score);
            scoreText.textContent = current;
            if (current >= score) clearInterval(timer);
        }, 40);

        scoreText.style.color = color;
        if (verdictEl) { verdictEl.textContent = verdict; verdictEl.style.color = color; }
    }, 80);

    const ingredients = data.ingredients || [];
    allIngredients = ingredients;

    const counts = { good: 0, neutral: 0, bad: 0 };
    ingredients.forEach(ing => { if (counts[ing.status] !== undefined) counts[ing.status]++; });
    document.getElementById('count-good').textContent = counts.good;
    document.getElementById('count-neutral').textContent = counts.neutral;
    document.getElementById('count-bad').textContent = counts.bad;

    renderIngredients('all');

    const claimsList = document.getElementById('claims-list');
    claimsList.innerHTML = '';
    const claims = data.claims || [];
    if (claims.length === 0) {
        claimsList.innerHTML = '<li class="item-card neutral"><div class="item-desc">No verifiable marketing claims detected on this label.</div></li>';
    } else {
        claims.forEach((claim, i) => {
            const statusClass = claim.isReal ? 'true' : 'false';
            const label = claim.isReal ? 'Verified' : 'Misleading';
            const li = document.createElement('li');
            li.className = `item-card ${statusClass}`;
            li.style.animationDelay = `${i * 0.05}s`;
            li.innerHTML = `
                <div class="item-header">
                    <span class="item-title">"${escapeHTML(claim.claim)}"</span>
                    <span class="item-badge ${statusClass}-bg">${label}</span>
                </div>
                <div class="item-desc">${escapeHTML(claim.explanation)}</div>
            `;
            claimsList.appendChild(li);
        });
    }

    switchTab('ingredients', document.querySelector('[data-tab="ingredients"]'));
}

// ── Ingredient Rendering + Filter ────────────────────────────────────────────

function renderIngredients(filter) {
    const list = document.getElementById('ingredients-list');
    list.innerHTML = '';

    const filtered = filter === 'all'
        ? allIngredients
        : allIngredients.filter(i => i.status === filter);

    if (filtered.length === 0) {
        list.innerHTML = `<li class="item-card neutral"><div class="item-desc">No ${filter === 'all' ? '' : filter + ' '}ingredients found.</div></li>`;
        return;
    }

    filtered.forEach((ing, i) => {
        const li = document.createElement('li');
        li.className = `item-card ${ing.status}`;
        li.style.animationDelay = `${i * 0.04}s`;
        li.innerHTML = `
            <div class="item-header">
                <span class="item-title">${escapeHTML(ing.name)}</span>
                <span class="item-badge ${ing.status}-bg">${capitalise(ing.status)}</span>
            </div>
            <div class="item-desc">${escapeHTML(ing.reason)}</div>
        `;
        list.appendChild(li);
    });
}

function filterIngredients(filter, btn) {
    document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
    if (btn) btn.classList.add('active');
    renderIngredients(filter);
}

// ── Tab Switcher ──────────────────────────────────────────────────────────────

function switchTab(tabName, btn) {
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
    if (btn) btn.classList.add('active');
    document.querySelectorAll('.tab-content').forEach(p => p.classList.add('hidden'));
    const panel = document.getElementById(`tab-${tabName}`);
    if (panel) panel.classList.remove('hidden');
}

// ── PDF Download ──────────────────────────────────────────────────────────────

async function downloadPDF() {
    if (!lastAnalysisData) return;

    const btn = document.getElementById('download-pdf-btn');
    const originalHTML = btn.innerHTML;
    btn.innerHTML = `<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/></svg> Generating...`;
    btn.disabled = true;

    // Dynamically load jsPDF if not already present
    if (!window.jspdf) {
        await new Promise((resolve, reject) => {
            const script = document.createElement('script');
            script.src = 'https://cdnjs.cloudflare.com/ajax/libs/jspdf/2.5.1/jspdf.umd.min.js';
            script.onload = resolve;
            script.onerror = reject;
            document.head.appendChild(script);
        });
    }

    const { jsPDF } = window.jspdf;
    const doc = new jsPDF({ unit: 'mm', format: 'a4' });
    const data = lastAnalysisData;

    const pageW = 210;
    const pageH = 297;
    const margin = 18;
    const contentW = pageW - margin * 2;
    let y = 0;

    // ── Colours ──
    const C = {
        teal: [13, 148, 136],
        tealLight: [204, 251, 241],
        good: [16, 185, 129],
        goodBg: [209, 250, 229],
        bad: [239, 68, 68],
        badBg: [254, 226, 226],
        neutral: [245, 158, 11],
        neutralBg: [254, 243, 199],
        dark: [13, 17, 23],
        gray: [75, 85, 99],
        lightGray: [156, 163, 175],
        border: [229, 231, 235],
        white: [255, 255, 255],
        pageBg: [249, 250, 251],
    };

    function setFill(rgb) { doc.setFillColor(...rgb); }
    function setDraw(rgb) { doc.setDrawColor(...rgb); }
    function setTxt(rgb) { doc.setTextColor(...rgb); }
    function setFont(style, size) { doc.setFont('helvetica', style); doc.setFontSize(size); }

    function checkPageBreak(needed = 12) {
        if (y + needed > pageH - 20) {
            doc.addPage();
            drawPageBg();
            y = margin;
        }
    }

    function drawPageBg() {
        setFill(C.pageBg);
        doc.rect(0, 0, pageW, pageH, 'F');
    }

    // ── PAGE 1 — HEADER ──────────────────────────────────────────────────────

    drawPageBg();

    // Teal header band
    setFill(C.teal);
    doc.rect(0, 0, pageW, 52, 'F');

    // Logo mark (rounded square)
    setFill([255, 255, 255, 0.18]);
    doc.roundedRect(margin, 10, 10, 10, 2, 2, 'F');
    setTxt(C.white);
    setFont('bold', 8);
    doc.text('V', margin + 2.8, 17.5);

    // Brand name
    setTxt(C.white);
    setFont('bold', 20);
    doc.text('VerifAI', margin + 14, 19);
    setFont('normal', 8);
    doc.setTextColor(204, 251, 241);
    doc.text('Know Your Ingredients', margin + 14, 25);

    // Report title (right side)
    setFont('bold', 11);
    setTxt(C.white);
    doc.text('INGREDIENT ANALYSIS REPORT', pageW - margin, 16, { align: 'right' });
    setFont('normal', 8);
    doc.setTextColor(204, 251, 241);
    const now = new Date();
    doc.text(`Generated: ${now.toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' })}`, pageW - margin, 22, { align: 'right' });

    y = 60;

    // ── PRODUCT IDENTITY BOX ──
    setFill(C.white);
    setDraw(C.border);
    doc.setLineWidth(0.3);
    doc.roundedRect(margin, y, contentW, 30, 4, 4, 'FD');

    // Category badge
    const catText = data.category || 'Product';
    setFont('bold', 7);
    const catW = doc.getTextWidth(catText) + 6;
    setFill(C.tealLight);
    doc.roundedRect(margin + 5, y + 5, catW, 6, 1.5, 1.5, 'F');
    setTxt(C.teal);
    doc.text(catText.toUpperCase(), margin + 8, y + 9.5);

    // Product name
    setFont('bold', 16);
    setTxt(C.dark);
    const productName = data.productName || 'Unknown Product';
    doc.text(productName, margin + 5, y + 21);

    y += 38;

    // ── SCORE SECTION ──
    const score = Math.min(100, Math.max(0, data.score || 0));
    let scoreColor = C.bad;
    let verdict = 'Caution';
    let verdictBg = C.badBg;
    if (score >= 70) { scoreColor = C.good; verdict = 'Healthy'; verdictBg = C.goodBg; }
    else if (score >= 40) { scoreColor = C.neutral; verdict = 'Moderate'; verdictBg = C.neutralBg; }

    // Score card
    setFill(C.white);
    setDraw(C.border);
    doc.roundedRect(margin, y, contentW, 46, 4, 4, 'FD');

    // Score circle (drawn with arc approximation)
    const cx = margin + 28, cy = y + 23, r = 16;
    // Background circle
    doc.setLineWidth(3);
    setDraw(C.border);
    doc.circle(cx, cy, r, 'S');
    // Progress arc (filled circle with white center trick)
    setDraw(scoreColor);
    doc.setLineWidth(3);
    // Draw partial arc via many small lines
    const pct = score / 100;
    const startAngle = -Math.PI / 2;
    const endAngle = startAngle + pct * 2 * Math.PI;
    const steps = 80;
    for (let i = 0; i < steps; i++) {
        const a1 = startAngle + (i / steps) * (endAngle - startAngle);
        const a2 = startAngle + ((i + 1) / steps) * (endAngle - startAngle);
        if (a2 > endAngle) break;
        doc.line(
            cx + r * Math.cos(a1), cy + r * Math.sin(a1),
            cx + r * Math.cos(a2), cy + r * Math.sin(a2)
        );
    }
    // Score number
    setFont('bold', 18);
    setTxt(scoreColor);
    doc.text(String(score), cx, cy + 3, { align: 'center' });

    // Score label
    setFont('normal', 7);
    setTxt(C.lightGray);
    doc.text('/ 100', cx, cy + 8.5, { align: 'center' });

    // Verdict + label (right of circle)
    const labelX = margin + 56;
    setFont('bold', 15);
    setTxt(scoreColor);
    doc.text(verdict, labelX, y + 20);

    setFont('normal', 8);
    setTxt(C.gray);
    doc.text('Overall Safety Score', labelX, y + 27);

    // Stat pills — right side
    const ingredients = data.ingredients || [];
    const counts = { good: 0, neutral: 0, bad: 0 };
    ingredients.forEach(ing => { if (counts[ing.status] !== undefined) counts[ing.status]++; });

    const pillW = 28, pillH = 18, pillStartX = pageW - margin - (pillW * 3 + 8);
    const pillData = [
        { label: 'Good', count: counts.good, bg: C.goodBg, fg: [6, 95, 70] },
        { label: 'Neutral', count: counts.neutral, bg: C.neutralBg, fg: [146, 64, 14] },
        { label: 'Caution', count: counts.bad, bg: C.badBg, fg: [153, 27, 27] },
    ];
    pillData.forEach((p, i) => {
        const px = pillStartX + i * (pillW + 4);
        const py = y + 14;
        setFill(p.bg);
        setDraw([...p.bg]);
        doc.roundedRect(px, py, pillW, pillH, 3, 3, 'FD');
        setFont('bold', 11);
        setTxt(p.fg);
        doc.text(String(p.count), px + pillW / 2, py + 8, { align: 'center' });
        setFont('normal', 6);
        doc.text(p.label.toUpperCase(), px + pillW / 2, py + 14, { align: 'center' });
    });

    y += 54;

    // ── SCORE INTERPRETATION BOX ──
    checkPageBreak(20);
    setFill([...verdictBg]);
    setDraw(scoreColor);
    doc.setLineWidth(0.4);
    doc.roundedRect(margin, y, contentW, 16, 3, 3, 'FD');
    // Left accent bar
    setFill(scoreColor);
    doc.roundedRect(margin, y, 3, 16, 1.5, 1.5, 'F');

    setFont('bold', 8);
    setTxt(scoreColor);
    const interpTitle = score >= 70 ? 'HEALTHY PRODUCT' : score >= 40 ? 'MODERATE CONCERN' : 'HIGH CONCERN';
    doc.text(interpTitle, margin + 8, y + 6.5);
    setFont('normal', 7.5);
    setTxt(C.gray);
    const interpText = score >= 70
        ? 'This product has a favorable ingredient profile. Most components are beneficial or safe for regular use.'
        : score >= 40
            ? 'This product contains a mix of safe and questionable ingredients. Use with awareness of flagged components.'
            : 'This product contains several concerning ingredients. Review flagged items carefully before regular use.';
    doc.text(interpText, margin + 8, y + 12.5, { maxWidth: contentW - 14 });
    y += 24;

    // ── INGREDIENTS SECTION ──────────────────────────────────────────────────

    checkPageBreak(20);

    // Section header
    setFont('bold', 11);
    setTxt(C.dark);
    doc.text('Ingredient Breakdown', margin, y + 7);
    setFont('normal', 7.5);
    setTxt(C.lightGray);
    doc.text(`${ingredients.length} ingredient${ingredients.length !== 1 ? 's' : ''} analysed`, margin, y + 13);
    // Divider
    setDraw(C.border);
    doc.setLineWidth(0.3);
    doc.line(margin, y + 16, pageW - margin, y + 16);
    y += 22;

    ingredients.forEach((ing) => {
        const cardH = 22 + (doc.splitTextToSize(ing.reason || '', contentW - 22).length * 4.5);
        checkPageBreak(cardH + 4);

        const statusColors = {
            good: { bg: C.goodBg, bar: C.good, fg: [6, 95, 70], label: 'GOOD' },
            neutral: { bg: C.neutralBg, bar: C.neutral, fg: [146, 64, 14], label: 'NEUTRAL' },
            bad: { bg: C.badBg, bar: C.bad, fg: [153, 27, 27], label: 'CAUTION' },
        };
        const sc = statusColors[ing.status] || statusColors.neutral;

        // Card bg
        setFill(C.white);
        setDraw(C.border);
        doc.setLineWidth(0.3);
        doc.roundedRect(margin, y, contentW, cardH, 3, 3, 'FD');

        // Status bar
        setFill(sc.bar);
        doc.roundedRect(margin, y, 3, cardH, 1.5, 1.5, 'F');

        // Ingredient name
        setFont('bold', 9);
        setTxt(C.dark);
        doc.text(ing.name || 'Unknown', margin + 8, y + 7);

        // Status badge
        const badgeText = sc.label;
        setFont('bold', 6);
        const bw = doc.getTextWidth(badgeText) + 6;
        const bx = pageW - margin - bw - 2;
        setFill(sc.bg);
        setDraw([...sc.bg]);
        doc.roundedRect(bx, y + 2.5, bw, 6, 1.5, 1.5, 'FD');
        setTxt(sc.fg);
        doc.text(badgeText, bx + 3, y + 6.8);

        // Reason text
        setFont('normal', 7.5);
        setTxt(C.gray);
        const lines = doc.splitTextToSize(ing.reason || '', contentW - 22);
        doc.text(lines, margin + 8, y + 13);

        y += cardH + 4;
    });

    // ── CLAIMS SECTION ───────────────────────────────────────────────────────

    const claims = data.claims || [];

    checkPageBreak(30);

    y += 4;
    setFont('bold', 11);
    setTxt(C.dark);
    doc.text('Marketing Claims Fact-Check', margin, y + 7);
    setFont('normal', 7.5);
    setTxt(C.lightGray);

    const verifiedCount = claims.filter(c => c.isReal).length;
    const misleadCount = claims.length - verifiedCount;
    doc.text(`${verifiedCount} verified · ${misleadCount} misleading`, margin, y + 13);

    setDraw(C.border);
    doc.setLineWidth(0.3);
    doc.line(margin, y + 16, pageW - margin, y + 16);
    y += 22;

    if (claims.length === 0) {
        checkPageBreak(14);
        setFill(C.neutralBg);
        setDraw(C.border);
        doc.roundedRect(margin, y, contentW, 12, 3, 3, 'FD');
        setFont('normal', 8);
        setTxt(C.gray);
        doc.text('No verifiable marketing claims detected on this label.', margin + 6, y + 7.5);
        y += 18;
    } else {
        claims.forEach((claim) => {
            const isVerified = claim.isReal;
            const sc = isVerified
                ? { bg: C.goodBg, bar: C.good, fg: [6, 95, 70], label: 'VERIFIED' }
                : { bg: C.badBg, bar: C.bad, fg: [153, 27, 27], label: 'MISLEADING' };

            const claimLines = doc.splitTextToSize(`"${claim.claim}"`, contentW - 22);
            const explanationLines = doc.splitTextToSize(claim.explanation || '', contentW - 22);
            const cardH = 8 + (claimLines.length * 5) + 3 + (explanationLines.length * 4.5) + 4;

            checkPageBreak(cardH + 4);

            setFill(C.white);
            setDraw(C.border);
            doc.setLineWidth(0.3);
            doc.roundedRect(margin, y, contentW, cardH, 3, 3, 'FD');

            setFill(sc.bar);
            doc.roundedRect(margin, y, 3, cardH, 1.5, 1.5, 'F');

            // Claim quote
            setFont('bold', 8.5);
            setTxt(C.dark);
            doc.text(claimLines, margin + 8, y + 7);

            // Badge
            setFont('bold', 6);
            const bw = doc.getTextWidth(sc.label) + 6;
            const bx = pageW - margin - bw - 2;
            setFill(sc.bg);
            setDraw([...sc.bg]);
            doc.roundedRect(bx, y + 2.5, bw, 6, 1.5, 1.5, 'FD');
            setTxt(sc.fg);
            doc.text(sc.label, bx + 3, y + 6.8);

            // Explanation
            const expY = y + 8 + claimLines.length * 5;
            setFont('normal', 7.5);
            setTxt(C.gray);
            doc.text(explanationLines, margin + 8, expY);

            y += cardH + 4;
        });
    }

    // ── FOOTER — every page ───────────────────────────────────────────────────

    const totalPages = doc.internal.getNumberOfPages();
    for (let i = 1; i <= totalPages; i++) {
        doc.setPage(i);
        // Footer bar
        setFill(C.white);
        setDraw(C.border);
        doc.setLineWidth(0.3);
        doc.line(margin, pageH - 14, pageW - margin, pageH - 14);
        setFont('normal', 7);
        setTxt(C.lightGray);
        doc.text('VerifAI — AI-powered ingredient analysis · verifai.app', margin, pageH - 8);
        doc.text(`Page ${i} of ${totalPages}`, pageW - margin, pageH - 8, { align: 'right' });
    }

    // ── SAVE ─────────────────────────────────────────────────────────────────

    const filename = `VerifAI_Report_${(productName).replace(/[^a-z0-9]/gi, '_').slice(0, 30)}_${now.getFullYear()}${String(now.getMonth() + 1).padStart(2, '0')}${String(now.getDate()).padStart(2, '0')}.pdf`;
    doc.save(filename);

    btn.innerHTML = originalHTML;
    btn.disabled = false;
}

// ── Helpers ───────────────────────────────────────────────────────────────────

function escapeHTML(str) {
    if (!str) return '';
    return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;');
}

function capitalise(str) {
    return str ? str.charAt(0).toUpperCase() + str.slice(1) : '';
}