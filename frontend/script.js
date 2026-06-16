let currentQuiz = null;
let currentUser = null;

async function loadUser() {
    try {
        currentUser = await fetchMe();
        document.getElementById('user-name').textContent = currentUser.name;
        document.getElementById('user-area').classList.remove('hidden');
        if (currentUser.role !== 'admin') {
            const manageLink = document.getElementById('manage-link');
            if (manageLink) manageLink.style.display = 'none';
        }
    } catch (err) {
        if (err.status === 401) { logout(); }
        else { Toast.error(handleApiError(err)); logout(); }
    }
}

async function loadQuizList() {
    const container = document.getElementById('quiz-list');
    container.innerHTML = Array(4).fill(`
        <div class="quiz-card" style="pointer-events:none">
            <div class="skeleton" style="height:20px;width:60%;margin-bottom:8px"></div>
            <div class="skeleton" style="height:14px;width:90%;margin-bottom:4px"></div>
            <div class="skeleton" style="height:14px;width:40%"></div>
            <div class="skeleton" style="height:22px;width:90px;margin-top:10px;border-radius:20px"></div>
        </div>
    `).join('');
    try {
        const quizzes = await apiGet('/quizzes');
        container.innerHTML = quizzes.map(q => `
            <div class="quiz-card" onclick="selectQuiz(${q.id})">
                <h3>${escapeHtml(q.title)}</h3>
                <p>${escapeHtml(q.description)}</p>
                <span class="badge">${q.questions.length} perguntas</span>
            </div>
        `).join('');
    } catch (err) {
        document.getElementById('quiz-list').innerHTML =
            `<div class="error">${handleApiError(err)}</div>`;
        Toast.error(handleApiError(err));
    }
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
    document.getElementById('form-container').classList.add('active');
    document.getElementById('result-container').classList.remove('active');

    document.getElementById('form-title').textContent = quiz.title;
    document.getElementById('form-desc').textContent = quiz.description;

    document.getElementById('quiz-questions').innerHTML = quiz.questions.map((q, i) => buildQuestionHtml(q, i)).join('');
}

function buildQuestionHtml(q, idx) {
    const required = q.required ? '<span class="required-mark">*</span>' : '';
    const header = `<div class="q-header"><span class="q-number">${idx + 1}</span><span class="question-text">${escapeHtml(q.text)}${required}</span></div>`;
    let inputHtml = '';

    switch (q.type) {
        case 'single_choice':
            inputHtml = `
                <div class="options-group">
                    ${q.options.map(o => `
                        <label class="option-label">
                            <input type="radio" name="q_${q.id}" value="${o.id}" ${q.required ? 'required' : ''}>
                            <span class="option-text">${escapeHtml(o.text)}</span>
                        </label>
                    `).join('')}
                </div>`;
            break;

        case 'multiple_choice':
            inputHtml = `
                <div class="options-group">
                    ${q.options.map(o => `
                        <label class="option-label">
                            <input type="checkbox" name="q_${q.id}" value="${o.id}">
                            <span class="option-text">${escapeHtml(o.text)}</span>
                        </label>
                    `).join('')}
                </div>`;
            break;

        case 'rating':
            inputHtml = `
                <div class="rating-group" data-question="${q.id}" data-required="${q.required}">
                    ${q.options.map(o => `
                        <button type="button" class="rating-btn" data-value="${o.id}" onclick="selectRating(this, ${q.id})">
                            ${escapeHtml(o.text)}
                        </button>
                    `).join('')}
                    <input type="hidden" name="q_${q.id}" id="rating_${q.id}" ${q.required ? 'required' : ''}>
                </div>`;
            break;

        case 'text':
            inputHtml = `
                <textarea class="text-input" name="q_${q.id}" placeholder="Digite sua resposta..." ${q.required ? 'required' : ''}></textarea>`;
            break;
    }

    return `
        <div class="question-block" style="animation-delay: ${idx * 0.06}s">
            ${header}
            ${inputHtml}
        </div>`;
}

function selectRating(btn, questionId) {
    const group = btn.closest('.rating-group');
    group.querySelectorAll('.rating-btn').forEach(b => b.classList.remove('selected'));
    btn.classList.add('selected');
    document.getElementById(`rating_${questionId}`).value = btn.dataset.value;
}

function backToList() {
    document.getElementById('quiz-list-section').classList.remove('hidden');
    document.getElementById('form-container').classList.remove('active');
    document.getElementById('result-container').classList.remove('active');
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
                if (val) {
                    answers.push({ question_id: question.id, value: val });
                }
                break;
            }
            case 'multiple_choice': {
                const vals = formData.getAll(fieldName);
                answers.push({ question_id: question.id, value: vals });
                break;
            }
        }
    }

    const btn = document.querySelector('.submit-btn');
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
    document.getElementById('form-container').classList.remove('active');
    document.getElementById('result-container').classList.add('active');

    document.getElementById('result-title').textContent = result.quiz_title;
    document.getElementById('submission-id').textContent = `Protocolo #${result.id}`;

    const list = document.getElementById('result-answers');
    list.innerHTML = result.answers.map(a => `
        <div class="result-answer">
            <div class="raq-question">${escapeHtml(a.question_text)}</div>
            <div class="raq-answer">${formatAnswer(a.answer)}</div>
        </div>
    `).join('');
}

function formatAnswer(answer) {
    if (Array.isArray(answer)) {
        return answer.join(', ');
    }
    return String(answer);
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

redirectIfNotAuth();
loadUser();
loadQuizList();
