import { describe, it, expect, beforeEach, vi } from 'vitest'
import fs from 'fs'
import path from 'path'
import { fileURLToPath } from 'url'

const __dirname = path.dirname(fileURLToPath(import.meta.url))

describe('Toast', () => {
  beforeEach(() => {
    document.body.innerHTML = ''
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  function loadToast() {
    const code = fs.readFileSync(path.join(__dirname, '..', 'toast.js'), 'utf-8')
    const fn = new Function(code + '\nreturn Toast;')
    return fn()
  }

  it('should create toast container on first show', () => {
    const Toast = loadToast()
    Toast.show('teste', 'info', 0)
    expect(document.getElementById('toast-container')).toBeTruthy()
  })

  it('should display message text', () => {
    const Toast = loadToast()
    Toast.show('mensagem de teste', 'info', 0)
    const toast = document.querySelector('.toast')
    expect(toast.textContent).toContain('mensagem de teste')
  })

  it('should have role="alert" on toast', () => {
    const Toast = loadToast()
    Toast.show('teste', 'info', 0)
    const toast = document.querySelector('.toast')
    expect(toast.getAttribute('role')).toBe('alert')
  })

  it('should apply correct type class', () => {
    const Toast = loadToast()
    Toast.show('erro', 'error', 0)
    Toast.show('aviso', 'warning', 0)
    Toast.show('sucesso', 'success', 0)
    Toast.show('info', 'info', 0)
    const toasts = document.querySelectorAll('.toast')
    expect(toasts[0].classList.contains('toast-error')).toBe(true)
    expect(toasts[1].classList.contains('toast-warning')).toBe(true)
    expect(toasts[2].classList.contains('toast-success')).toBe(true)
    expect(toasts[3].classList.contains('toast-info')).toBe(true)
  })

  it('should auto-remove toast after duration', () => {
    const Toast = loadToast()
    Toast.show('auto', 'info', 1000)
    expect(document.querySelectorAll('.toast').length).toBe(1)
    vi.advanceTimersByTime(1300)
    expect(document.querySelectorAll('.toast').length).toBe(0)
  })

  it('should keep toast when duration is 0', () => {
    const Toast = loadToast()
    Toast.show('permanente', 'info', 0)
    vi.advanceTimersByTime(10000)
    expect(document.querySelectorAll('.toast').length).toBe(1)
  })

  it('should support shorthand methods', () => {
    const Toast = loadToast()
    Toast.success('ok')
    Toast.error('fail')
    Toast.warning('cuidado')
    Toast.info('info')
    expect(document.querySelectorAll('.toast-success').length).toBe(1)
    expect(document.querySelectorAll('.toast-error').length).toBe(1)
    expect(document.querySelectorAll('.toast-warning').length).toBe(1)
    expect(document.querySelectorAll('.toast-info').length).toBe(1)
  })
})
