/**
 * Client-Side Privacy-Preserving Frontend Application.
 * Communicates with FastAPI /api/process and /api/download endpoints.
 * Guarantees zero raw PII display or storage in browser state.
 */

document.addEventListener('DOMContentLoaded', () => {
    // ── DOM Elements ──────────────────────────────────────────
    const dropzone = document.getElementById('dropzone');
    const fileInput = document.getElementById('file-input');
    const filePreview = document.getElementById('file-preview');
    const fileNameDisplay = document.getElementById('file-name');
    const fileSizeDisplay = document.getElementById('file-size');
    const changeFileBtn = document.getElementById('change-file-btn');
    const processBtn = document.getElementById('process-btn');

    const progressSection = document.getElementById('progress-section');
    const progressBar = document.getElementById('progress-bar');
    const stepUpload = document.getElementById('step-upload');
    const stepDetect = document.getElementById('step-detect');
    const stepRedact = document.getElementById('step-redact');
    const stepComplete = document.getElementById('step-complete');

    const errorAlert = document.getElementById('error-alert');
    const errorTitle = document.getElementById('error-title');
    const errorMessage = document.getElementById('error-message');
    const closeErrorBtn = document.getElementById('close-error-btn');

    const resultSection = document.getElementById('result-section');
    const resultFilename = document.getElementById('result-filename');
    const downloadBtn = document.getElementById('download-btn');
    const totalDetectedVal = document.getElementById('metric-total-detected');
    const totalReplacedVal = document.getElementById('metric-total-replaced');
    const docValidVal = document.getElementById('metric-doc-valid');
    const piiCleanVal = document.getElementById('metric-pii-clean');
    const resetBtn = document.getElementById('reset-btn');

    let selectedFile = null;
    const MAX_SIZE_MB = 20;

    // All 9 canonical PII categories in display order
    const ALL_CATEGORIES = [
        'PERSON', 'EMAIL_ADDRESS', 'PHONE_NUMBER', 'ORGANIZATION',
        'ADDRESS', 'SSN', 'CREDIT_CARD', 'DATE_OF_BIRTH', 'IP_ADDRESS'
    ];

    // ── Drag & Drop ────────────────────────────────────────────
    ['dragenter', 'dragover'].forEach(eventName => {
        dropzone.addEventListener(eventName, (e) => {
            e.preventDefault(); e.stopPropagation();
            dropzone.classList.add('dragover');
        });
    });

    ['dragleave', 'drop'].forEach(eventName => {
        dropzone.addEventListener(eventName, (e) => {
            e.preventDefault(); e.stopPropagation();
            dropzone.classList.remove('dragover');
        });
    });

    dropzone.addEventListener('drop', (e) => {
        const files = e.dataTransfer.files;
        if (files && files.length > 0) handleFileSelection(files[0]);
    });

    dropzone.addEventListener('click', () => fileInput.click());
    dropzone.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); fileInput.click(); }
    });

    fileInput.addEventListener('change', (e) => {
        if (e.target.files && e.target.files.length > 0) handleFileSelection(e.target.files[0]);
    });

    changeFileBtn.addEventListener('click', resetSelection);
    closeErrorBtn.addEventListener('click', hideError);
    resetBtn.addEventListener('click', resetSelection);

    // ── File Handling ──────────────────────────────────────────
    function handleFileSelection(file) {
        hideError();
        if (!file.name.toLowerCase().endsWith('.docx')) {
            showError('Invalid File Format', 'Please select a valid Microsoft Word (.docx) document.');
            return;
        }
        const sizeMB = file.size / (1024 * 1024);
        if (sizeMB > MAX_SIZE_MB) {
            showError('File Too Large', `Selected file size (${sizeMB.toFixed(1)} MB) exceeds maximum allowed limit of ${MAX_SIZE_MB} MB.`);
            return;
        }
        selectedFile = file;
        fileNameDisplay.textContent = file.name;
        fileSizeDisplay.textContent = formatBytes(file.size);
        dropzone.classList.add('hidden');
        filePreview.classList.remove('hidden');
        processBtn.disabled = false;
    }

    function resetSelection() {
        selectedFile = null;
        fileInput.value = '';
        dropzone.classList.remove('hidden');
        filePreview.classList.add('hidden');
        processBtn.disabled = true;
        progressSection.classList.add('hidden');
        resultSection.classList.add('hidden');
        hideError();
    }

    // ── Process Document ───────────────────────────────────────
    processBtn.addEventListener('click', async () => {
        if (!selectedFile) return;
        processBtn.disabled = true;
        hideError();
        resultSection.classList.add('hidden');
        progressSection.classList.remove('hidden');

        updateProgressStage(1, 20);

        const formData = new FormData();
        formData.append('file', selectedFile);

        try {
            updateProgressStage(2, 50);

            const response = await fetch('/api/process', {
                method: 'POST',
                body: formData,
            });

            const data = await response.json();

            if (!response.ok) {
                const errMsg = typeof data.detail === 'object' && data.detail?.message
                    ? data.detail.message
                    : (data.message || 'Unable to process document. Please verify it is a valid DOCX file.');
                const errTitle = typeof data.detail === 'object' && data.detail?.error
                    ? data.detail.error : 'Processing Error';
                showError(errTitle, errMsg);
                progressSection.classList.add('hidden');
                processBtn.disabled = false;
                return;
            }

            updateProgressStage(3, 85);

            setTimeout(() => {
                updateProgressStage(4, 100);
                setTimeout(() => {
                    progressSection.classList.add('hidden');
                    displayResults(data);
                }, 300);
            }, 200);

        } catch (err) {
            console.error('Processing error:', err);
            showError('Unable to Process Document', 'Could not communicate with the local redaction server. Please verify server status and try again.');
            progressSection.classList.add('hidden');
            processBtn.disabled = false;
        }
    });

    // ── Progress Stages ────────────────────────────────────────
    function updateProgressStage(stageNum, percent) {
        progressBar.style.width = `${percent}%`;
        const steps = [stepUpload, stepDetect, stepRedact, stepComplete];
        steps.forEach((step, idx) => {
            if (idx + 1 < stageNum) step.className = 'step-item complete';
            else if (idx + 1 === stageNum) step.className = 'step-item active';
            else step.className = 'step-item';
        });
    }

    // ══════════════════════════════════════════════════════════
    //  DISPLAY RESULTS — 9 Sections
    // ══════════════════════════════════════════════════════════
    function displayResults(data) {

        // ① Sanitization Complete
        resultFilename.textContent = data.filename;
        downloadBtn.href = `/api/download/${data.download_id}`;

        // ② Executive Summary KPIs
        totalDetectedVal.textContent = data.total_detections;
        totalReplacedVal.textContent = data.replacements_applied;

        setStatus(docValidVal, data.validation.document_valid);
        setStatus(piiCleanVal, data.validation.original_pii_residual_check);

        // ③ Detection Matrix
        renderDetectionMatrix(data);

        // ④ Evaluation Matrix
        renderEvaluationMatrix(data);

        // ⑤ Overall Metrics
        renderOverallMetrics(data);

        // ⑥ Validation Matrix
        renderValidationMatrix(data);

        // ⑦ Processing Performance
        renderPerformanceTable(data);

        // ⑧ Error Analysis
        renderErrorAnalysis(data);

        resultSection.classList.remove('hidden');
        // Smooth scroll to result
        setTimeout(() => resultSection.scrollIntoView({ behavior: 'smooth', block: 'start' }), 100);
    }

    // ── ③ Detection Matrix ────────────────────────────────────
    function renderDetectionMatrix(data) {
        const tbody = document.getElementById('detection-tbody');
        tbody.innerHTML = '';
        const cats = data.detections || {};
        const totalReplaced = data.replacements_applied;
        const totalDetected = data.total_detections;

        ALL_CATEGORIES.forEach(cat => {
            const count = cats[cat] || 0;
            // Replacement ratio: proportional share of replacements per category
            const replaced = totalDetected > 0 ? Math.round((count / totalDetected) * totalReplaced) : 0;
            const tr = document.createElement('tr');
            tr.className = count > 0 ? 'row-active' : 'row-zero';
            tr.innerHTML = `
                <td><span class="cat-label ${count > 0 ? 'cat-active' : 'cat-zero'}">${fmtCat(cat)}</span></td>
                <td class="num-col"><span class="num-val ${count > 0 ? 'num-highlight' : ''}">${count}</span></td>
                <td class="num-col"><span class="num-val">${replaced}</span></td>
            `;
            tbody.appendChild(tr);
        });
    }

    // ── ④ Evaluation Matrix ──────────────────────────────────
    function renderEvaluationMatrix(data) {
        const eval_ = data.evaluation || {};
        const tbody = document.getElementById('eval-tbody');
        const badge = document.getElementById('eval-doc-badge');
        const note = document.getElementById('eval-note');

        tbody.innerHTML = '';

        if (eval_.available) {
            badge.textContent = 'CONTROLLED EVALUATION DOCUMENT';
            badge.className = 'eval-doc-badge eval-doc-controlled';
            note.textContent = 'Ground truth independently annotated. Precision/Recall/F1 computed from exact span matching.';
        } else {
            badge.textContent = 'USER-UPLOADED DOCUMENT';
            badge.className = 'eval-doc-badge eval-doc-user';
            note.textContent = eval_.ground_truth_unavailable_reason || 'No independent ground truth available for this document.';
        }

        const perCat = eval_.per_category || [];
        ALL_CATEGORIES.forEach(cat => {
            const m = perCat.find(x => x.category === cat) || {};
            const isNA = !eval_.available;

            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td><span class="cat-label ${(m.predicted_count > 0) ? 'cat-active' : 'cat-zero'}">${fmtCat(cat)}</span></td>
                <td class="num-col">${isNA ? '<span class="na-val">N/A</span>' : (m.ground_truth_count ?? 0)}</td>
                <td class="num-col"><span class="${(m.predicted_count > 0) ? 'num-highlight' : ''}">${m.predicted_count ?? 0}</span></td>
                <td class="num-col">${isNA ? '<span class="na-val">N/A</span>' : (m.tp ?? 0)}</td>
                <td class="num-col">${isNA ? '<span class="na-val">N/A</span>' : fmtErrorCell(m.fp ?? 0, 'fp')}</td>
                <td class="num-col">${isNA ? '<span class="na-val">N/A</span>' : fmtErrorCell(m.fn ?? 0, 'fn')}</td>
                <td class="num-col">${isNA ? '<span class="na-val">N/A</span>' : fmtPct(m.precision)}</td>
                <td class="num-col">${isNA ? '<span class="na-val">N/A</span>' : fmtPct(m.recall)}</td>
                <td class="num-col">${isNA ? '<span class="na-val">N/A</span>' : fmtPct(m.f1)}</td>
                <td class="num-col">${isNA ? '<span class="na-val">N/A</span>' : fmtPct(m.exact_span_match)}</td>
            `;
            tbody.appendChild(tr);
        });
    }

    // ── ⑤ Overall Metrics ─────────────────────────────────────
    function renderOverallMetrics(data) {
        const eval_ = data.evaluation || {};
        const accBox = document.getElementById('overall-accuracy');
        const accNote = document.getElementById('overall-accuracy-note');
        const grid = document.getElementById('overall-metrics-grid');

        // Accuracy — always N/A for span extraction tasks
        accBox.textContent = 'N/A';
        accNote.textContent = eval_.accuracy_note || 'N/A — True-negative population unavailable for sparse span extraction.';

        const metrics = [
            { label: 'Micro Precision', value: eval_.micro_precision, available: eval_.available },
            { label: 'Micro Recall',    value: eval_.micro_recall,    available: eval_.available },
            { label: 'Micro F1',        value: eval_.micro_f1,        available: eval_.available },
            { label: 'Macro Precision', value: eval_.macro_precision, available: eval_.available },
            { label: 'Macro Recall',    value: eval_.macro_recall,    available: eval_.available },
            { label: 'Macro F1',        value: eval_.macro_f1,        available: eval_.available },
            { label: 'Exact Span Match Ratio', value: eval_.overall_exact_match_ratio, available: eval_.available },
        ];

        grid.innerHTML = '';
        metrics.forEach(m => {
            const box = document.createElement('div');
            box.className = 'overall-metric-box';
            if (m.available && m.value !== null && m.value !== undefined) {
                const pct = (m.value * 100).toFixed(1);
                const cls = m.value >= 0.8 ? 'val-good' : m.value >= 0.5 ? 'val-warn' : 'val-bad';
                box.innerHTML = `
                    <span class="om-value ${cls}">${pct}%</span>
                    <span class="om-label">${m.label}</span>
                `;
            } else {
                box.innerHTML = `
                    <span class="om-value om-na">N/A</span>
                    <span class="om-label">${m.label}</span>
                    <span class="om-na-reason">Ground truth unavailable</span>
                `;
            }
            grid.appendChild(box);
        });
    }

    // ── ⑥ Validation Matrix ───────────────────────────────────
    function renderValidationMatrix(data) {
        const v = data.validation || {};
        const grid = document.getElementById('validation-grid');

        const checks = [
            { label: 'Document Structure',        pass: v.document_valid,               desc: 'Output DOCX is structurally valid' },
            { label: 'Residual PII Check',         pass: v.original_pii_residual_check,  desc: 'No original PII strings remain in output' },
            { label: 'Original File Integrity',    pass: v.original_file_hash_unchanged, desc: 'Input file SHA-256 hash unchanged' },
            { label: 'Output DOCX',                pass: v.document_valid,               desc: 'Redacted file is a valid DOCX container' },
            { label: 'Replacement Consistency',    pass: v.replacement_consistency,      desc: 'Replacements applied = detections count' },
        ];

        grid.innerHTML = '';
        checks.forEach(c => {
            const card = document.createElement('div');
            const passed = c.pass === true;
            card.className = `validation-card ${passed ? 'val-pass' : 'val-fail'}`;
            card.innerHTML = `
                <div class="val-icon">${passed ? '✓' : '✗'}</div>
                <div class="val-body">
                    <div class="val-label">${c.label}</div>
                    <div class="val-status">${passed ? 'PASS' : 'FAIL'}</div>
                    <div class="val-desc">${c.desc}</div>
                </div>
            `;
            grid.appendChild(card);
        });
    }

    // ── ⑦ Processing Performance ──────────────────────────────
    function renderPerformanceTable(data) {
        const t = data.timing_ms || {};
        const tbody = document.getElementById('perf-tbody');
        tbody.innerHTML = '';

        const stages = [
            { label: 'Parsing',    key: 'parsing' },
            { label: 'Detection',  key: 'detection' },
            { label: 'Mapping',    key: 'mapping' },
            { label: 'Redaction',  key: 'redaction' },
            { label: 'Validation', key: 'validation' },
            { label: 'Evaluation', key: 'evaluation' },
            { label: 'Total',      key: 'total', isTotal: true },
        ];

        stages.forEach(s => {
            const val = t[s.key];
            const tr = document.createElement('tr');
            tr.className = s.isTotal ? 'perf-total-row' : '';
            tr.innerHTML = `
                <td>${s.isTotal ? '<strong>' + s.label + '</strong>' : s.label}</td>
                <td class="num-col">
                    ${val !== undefined
                        ? `<span class="mono-val">${val.toFixed ? val.toFixed(2) : val}</span>`
                        : '<span class="na-val">—</span>'
                    }
                </td>
            `;
            tbody.appendChild(tr);
        });
    }

    // ── ⑧ Error Analysis ──────────────────────────────────────
    function renderErrorAnalysis(data) {
        const eval_ = data.evaluation || {};
        const container = document.getElementById('error-analysis-content');
        container.innerHTML = '';

        if (!eval_.available) {
            container.innerHTML = `
                <div class="na-block">
                    <span class="na-icon">ℹ</span>
                    <p>Error analysis requires independent ground truth. Not available for user-uploaded documents.</p>
                    <p style="margin-top:0.5rem;font-size:0.8125rem;color:var(--text-subtle);">
                        To enable formal error analysis, provide independently annotated ground truth for this document.
                    </p>
                </div>
            `;
            return;
        }

        const fpTotal = eval_.total_fp || 0;
        const fnTotal = eval_.total_fn || 0;
        const fpByCat = eval_.fp_by_category || {};
        const fnByCat = eval_.fn_by_category || {};

        // Summary totals
        const summaryEl = document.createElement('div');
        summaryEl.className = 'error-summary';
        summaryEl.innerHTML = `
            <div class="error-total-box ${fpTotal > 0 ? 'error-has' : 'error-none'}">
                <span class="et-count">${fpTotal}</span>
                <span class="et-label">Total False Positives</span>
                <span class="et-def">Predicted but not in ground truth</span>
            </div>
            <div class="error-total-box ${fnTotal > 0 ? 'error-has' : 'error-none'}">
                <span class="et-count">${fnTotal}</span>
                <span class="et-label">Total False Negatives</span>
                <span class="et-def">In ground truth but not predicted</span>
            </div>
        `;
        container.appendChild(summaryEl);

        // Per-category breakdown
        const hasCatErrors = ALL_CATEGORIES.some(
            cat => (fpByCat[cat] || 0) > 0 || (fnByCat[cat] || 0) > 0
        );

        if (hasCatErrors) {
            const catGrid = document.createElement('div');
            catGrid.className = 'error-cat-grid';

            ALL_CATEGORIES.forEach(cat => {
                const fp = fpByCat[cat] || 0;
                const fn = fnByCat[cat] || 0;
                if (fp === 0 && fn === 0) return;

                const card = document.createElement('div');
                card.className = 'error-cat-card';
                card.innerHTML = `
                    <div class="error-cat-name">${fmtCat(cat)}</div>
                    <div class="error-cat-row"><span class="ec-label">FP</span><span class="ec-val ${fp > 0 ? 'ec-fp' : ''}">${fp}</span></div>
                    <div class="error-cat-row"><span class="ec-label">FN</span><span class="ec-val ${fn > 0 ? 'ec-fn' : ''}">${fn}</span></div>
                `;
                catGrid.appendChild(card);
            });

            container.appendChild(catGrid);
        } else {
            const perfect = document.createElement('div');
            perfect.className = 'perfect-score';
            perfect.innerHTML = `<span class="ps-icon">✓</span> No false positives or false negatives detected.`;
            container.appendChild(perfect);
        }
    }

    // ── Helpers ────────────────────────────────────────────────
    function setStatus(el, passed) {
        el.textContent = passed ? 'PASS' : 'FAIL';
        el.className = `metric-value metric-status ${passed ? '' : 'text-error'}`;
    }

    function fmtCat(name) {
        return name.replace(/_/g, ' ').toLowerCase().replace(/\b\w/g, l => l.toUpperCase());
    }

    function fmtPct(val) {
        if (val === null || val === undefined) return '<span class="na-val">N/A</span>';
        const pct = (val * 100).toFixed(1);
        const cls = val >= 0.8 ? 'val-good' : val >= 0.5 ? 'val-warn' : 'val-bad';
        return `<span class="${cls}">${pct}%</span>`;
    }

    function fmtErrorCell(count, type) {
        if (count === 0) return `<span class="ec-zero">0</span>`;
        const cls = type === 'fp' ? 'ec-fp' : 'ec-fn';
        return `<span class="${cls}">${count}</span>`;
    }

    function showError(title, message) {
        errorTitle.textContent = title;
        errorMessage.textContent = message;
        errorAlert.classList.remove('hidden');
    }

    function hideError() {
        errorAlert.classList.add('hidden');
    }

    function formatBytes(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
    }
});
