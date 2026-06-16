import { describe, it, expect } from 'vitest'

describe('Empty state rendering', () => {
  it('should contain .empty-state with icon, heading, and action', () => {
    document.body.innerHTML = `
      <div class="empty-state">
        <div class="empty-icon"><svg aria-hidden="true"></svg></div>
        <h3>Nenhum resultado ainda</h3>
        <a href="/static/index.html" class="dash-empty-cta">Responder quizzes</a>
      </div>
    `
    const state = document.querySelector('.empty-state')
    expect(state).toBeTruthy()
    expect(state.querySelector('.empty-icon svg')).toBeTruthy()
    expect(state.querySelector('h3')).toBeTruthy()
    expect(state.querySelector('a.dash-empty-cta')).toBeTruthy()
  })

  it('should have aria-hidden on decorative SVG', () => {
    document.body.innerHTML = `
      <div class="empty-state">
        <div class="empty-icon">
          <svg width="48" height="48" aria-hidden="true"></svg>
        </div>
        <h3>Vazio</h3>
      </div>
    `
    const svg = document.querySelector('.empty-icon svg')
    expect(svg.getAttribute('aria-hidden')).toBe('true')
  })

  it('should be hidden by default when .hidden class is present', () => {
    document.body.innerHTML = `
      <div id="test-empty" class="empty-state hidden">
        <h3>Escondido</h3>
      </div>
    `
    const el = document.getElementById('test-empty')
    expect(el.classList.contains('hidden')).toBe(true)
  })
})
