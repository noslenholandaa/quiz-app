let currentQuiz = null;
let allQuizzes = [];

async function loadQuizList() {
    const container = document.getElementById('quiz-list');
    try {
        allQuizzes = await apiGet('/quizzes');
        if (allQuizzes.length === 0) {
            container.innerHTML = '<div class="empty-state"><div class="empty-state-icon">📋</div><h3>Nenhum quiz disponível</h3><p>Ainda não há quizzes para responder. Volte mais tarde.</p></div>';
            return;
        }
        renderQuizzes(allQuizzes);
    } catch (err) {
        container.innerHTML = `<div class="alert alert-danger"><span class="alert-message">${handleApiError(err)}</span></div>`;
        Toast.error(handleApiError(err));
    }
}

function renderQuizzes(quizzes) {
    const container = document.getElementById('quiz-list');
    container.innerHTML = quizzes.map(q => `
        <div class="quiz-card" onclick="selectQuiz(${q.id})">
            <h3>${escapeHtml(q.title)}</h3>
            <p>${escapeHtml(q.description || 'Sem descrição')}</p>
            <div class="quiz-card-meta">
                <span class="badge badge-primary">${q.questions.length} perguntas</span>
                ${q.category ? `<span class="badge badge-success">${escapeHtml(q.category)}</span>` : ''}
                ${q.tags ? q.tags.map(t => `<span class="badge badge-warning">${escapeHtml(t)}</span>`).join('') : ''}
            </div>
        </div>
    `).join('');
}

function filterQuizzes(query) {
    if (!query.trim()) { renderQuizzes(allQuizzes); return; }
    const q = query.toLowerCase();
    const filtered = allQuizzes.filter(quiz =>
        quiz.title.toLowerCase().includes(q) ||
        (quiz.description && quiz.description.toLowerCase().includes(q)) ||
        (quiz.tags && quiz.tags.some(t => t.toLowerCase().includes(q)))
    );
    renderQuizzes(filtered);
}

async function selectQuiz(quizId) {
    try {
        currentQuiz = await apiGet(`/quizzes/${quizId}`);
        renderForm(currentQuiz);
    } catch (err) {
        Toast.error(handleApiError(err));
    }
}

function renderForm(quiz) {
    document.getElementById('quiz-list-section').classList.add('hidden');
    document.getElementById('form-container').classList.remove('hidden');
    document.getElementById('result-container').classList.add('hidden');

    document.getElementById('form-title').textContent = quiz.title;
    document.getElementById('form-desc').textContent = quiz.description;
    document.getElementById('form-title-progress').textContent = quiz.title;
    updateProgress();

    document.getElementById('quiz-questions').innerHTML = quiz.questions.map((q, i) => buildQuestionHtml(q, i)).join('');
}

function updateProgress() {
    const form = document.getElementById('quiz-form');
    if (!form) return;
    const total = form.querySelectorAll('[required]').length;
    const filled = form.querySelectorAll('[required]:valid').length;
    const pct = total > 0 ? Math.round((filled / total) * 100) : 0;
    document.getElementById('progress-fill').style.width = pct + '%';
    document.getElementById('progress-label').textContent = pct + '%';
}

function buildQuestionHtml(q, idx) {
    const required = q.required ? '<span class="required-mark" style="color:var(--color-danger);margin-left:4px">*</span>' : '';
    const header = `<div class="q-header"><span class="q-number">${idx + 1}</span><span class="question-text">${escapeHtml(q.text)}${required}</span></div>`;
    let inputHtml = '';

    switch (q.type) {
        case 'single_choice':
            inputHtml = `<div class="options-group">${q.options.map(o => `
                <label class="option-label">
                    <input type="radio" name="q_${q.id}" value="${o.id}" ${q.required ? 'required' : ''} onchange="updateProgress()">
                    <span class="option-text">${escapeHtml(o.text)}</span>
                </label>
            `).join('')}</div>`;
            break;
        case 'multiple_choice':
            inputHtml = `<div class="options-group">${q.options.map(o => `
                <label class="option-label">
                    <input type="checkbox" name="q_${q.id}" value="${o.id}" onchange="updateProgress()">
                    <span class="option-text">${escapeHtml(o.text)}</span>
                </label>
            `).join('')}</div>`;
            break;
        case 'rating':
            inputHtml = `<div class="rating-group" data-question="${q.id}" data-required="${q.required}">
                ${q.options.map(o => `
                    <button type="button" class="rating-btn" data-value="${o.id}" onclick="selectRating(this, ${q.id})">${escapeHtml(o.text)}</button>
                `).join('')}
                <input type="hidden" name="q_${q.id}" id="rating_${q.id}" ${q.required ? 'required' : ''}>
            </div>`;
            break;
        case 'text':
            inputHtml = `<textarea class="form-input" name="q_${q.id}" placeholder="Digite sua resposta..." ${q.required ? 'required' : ''} oninput="updateProgress()" style="min-height:90px"></textarea>`;
            break;
    }
    return `<div class="question-block" style="animation-delay: ${idx * 0.06}s">${header}${inputHtml}</div>`;
}

function selectRating(btn, questionId) {
    const group = btn.closest('.rating-group');
    group.querySelectorAll('.rating-btn').forEach(b => b.classList.remove('selected'));
    btn.classList.add('selected');
    document.getElementById(`rating_${questionId}`).value = btn.dataset.value;
    updateProgress();
}

function backToList() {
    document.getElementById('quiz-list-section').classList.remove('hidden');
    document.getElementById('form-container').classList.add('hidden');
    document.getElementById('result-container').classList.add('hidden');
    currentQuiz = null;
}

async function submitForm(event) {
    event.preventDefault();
    if (!currentQuiz) return;
    const form = document.getElementById('quiz-form');
    const formData = new FormData(form);
    const answers = [];
    for (const question of currentQuiz.questions) {
        const fieldName = `q_${question.id}`;
        switch (question.type) {
            case 'single_choice':
            case 'rating':
            case 'text': {
                const val = formData.get(fieldName);
                if (val) answers.push({ question_id: question.id, value: val });
                break;
            }
            case 'multiple_choice': {
                const vals = formData.getAll(fieldName);
                answers.push({ question_id: question.id, value: vals });
                break;
            }
        }
    }
    const btn = document.querySelector('.btn-primary');
    btn.disabled = true;
    btn.textContent = 'Enviando...';
    try {
        const result = await apiPost(`/quizzes/${currentQuiz.id}/submit`, { answers });
        showResult(result);
    } catch (err) {
        Toast.error(handleApiError(err));
    } finally {
        btn.disabled = false;
        btn.textContent = 'Enviar respostas';
    }
}

function showResult(result) {
    document.getElementById('form-container').classList.add('hidden');
    document.getElementById('result-container').classList.remove('hidden');

    console.debug('[Result Debug] Full API response:', JSON.parse(JSON.stringify(result)));
    result.answers.forEach((a, i) => {
        console.debug('[Result Debug] Answer %d: question="%s" correct=%s (type=%s) answer_text="%s" raw=%s',
            i, a.question_text, a.correct, typeof a.correct, a.answer_text, JSON.stringify(a.answer));
    });

    const correctCount = result.answers.filter(a => a.correct).length;
    const incorrectCount = result.answers.length - correctCount;
    const perc = result.percentage || Math.round((result.score / result.max_score) * 100) || 0;
    const badge = getGradeLabel(perc);

    document.getElementById('result-title').textContent = result.quiz_title;
    document.getElementById('result-badge').className = `badge ${getGradeClass(perc)}`;
    document.getElementById('result-badge').textContent = `${perc}%`;

    document.getElementById('result-summary').innerHTML = `
        <div class="h-summary-item h-summary-correct">
            <span class="h-summary-icon">&#10003;</span>
            <span><strong>${correctCount}</strong> corretas</span>
        </div>
        <div class="h-summary-item h-summary-incorrect">
            <span class="h-summary-icon">&#10007;</span>
            <span><strong>${incorrectCount}</strong> incorretas</span>
        </div>
        <div class="h-summary-item h-summary-total">
            <span class="h-summary-icon">&#9733;</span>
            <span><strong>${perc}%</strong> de aproveitamento</span>
        </div>
        <span class="h-badge-performance">${badge.icon} ${badge.label}</span>
    `;

    document.getElementById('result-answers').innerHTML = result.answers.map(a => {
        const isCorrect = a.correct === true;
        const icon = isCorrect
            ? '<span class="h-answer-icon h-correct" title="Correta">&#10003;</span>'
            : '<span class="h-answer-icon h-incorrect" title="Incorreta">&#10007;</span>';
        const rowClass = isCorrect ? 'h-answer-correct' : 'h-answer-incorrect';
        const displayAnswer = a.answer_text || String(a.answer);
        return `<div class="h-answer-row ${rowClass}">
            <div class="h-answer-content">
                <div class="h-answer-question">${escapeHtml(a.question_text)}</div>
                <div class="h-answer-value">${escapeHtml(displayAnswer)}</div>
            </div>
            ${icon}
        </div>`;
    }).join('');

    document.getElementById('result-date').textContent = '';
    if (result.created_at) {
        const dateEl = document.getElementById('result-date');
        dateEl.innerHTML = `
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="4" width="18" height="18" rx="2" ry="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg>
            ${formatDate(result.created_at)}
        `;
    }
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

redirectIfNotAuth();
if (typeof initLayout === 'function') initLayout('Explorar');
loadQuizList();
