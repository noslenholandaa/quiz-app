import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import fs from 'fs'
import path from 'path'
import { fileURLToPath } from 'url'

const __dirname = path.dirname(fileURLToPath(import.meta.url))

describe('Theme', () => {
  let localStorageStore = {}

  beforeEach(() => {
    localStorageStore = {}
    vi.stubGlobal('localStorage', {
      getItem: vi.fn((key) => localStorageStore[key] ?? null),
      setItem: vi.fn((key, val) => { localStorageStore[key] = val }),
      removeItem: vi.fn((key) => { delete localStorageStore[key] }),
      clear: vi.fn(() => { localStorageStore = {} }),
    })
    document.documentElement.classList.remove('dark')
    document.body.innerHTML = '<button id="theme-toggle"></button>'
    delete globalThis.Theme
    vi.stubGlobal('matchMedia', () => ({ matches: false }))
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  function loadTheme() {
    const code = fs.readFileSync(path.join(__dirname, '..', 'theme.js'), 'utf-8')
    const fn = new Function(code + '\nreturn Theme;')
    return fn()
  }

  it('should start with light theme when no preference is saved', () => {
    vi.stubGlobal('matchMedia', () => ({ matches: false }))
    const Theme = loadTheme()
    Theme.init()
    expect(Theme.isDark()).toBe(false)
  })

  it('should start with dark theme when system prefers dark', () => {
    vi.stubGlobal('matchMedia', () => ({ matches: true }))
    const Theme = loadTheme()
    Theme.init()
    expect(Theme.isDark()).toBe(true)
  })

  it('should persist dark theme in localStorage', () => {
    const Theme = loadTheme()
    Theme.enableDark()
    expect(localStorageStore['quiz_theme']).toBe('dark')
    expect(document.documentElement.classList.contains('dark')).toBe(true)
  })

  it('should persist light theme in localStorage', () => {
    const Theme = loadTheme()
    Theme.enableDark()
    Theme.enableLight()
    expect(localStorageStore['quiz_theme']).toBe('light')
    expect(document.documentElement.classList.contains('dark')).toBe(false)
  })

  it('should toggle between dark and light', () => {
    const Theme = loadTheme()
    Theme.enableDark()
    expect(Theme.isDark()).toBe(true)
    Theme.toggle()
    expect(Theme.isDark()).toBe(false)
    Theme.toggle()
    expect(Theme.isDark()).toBe(true)
  })

  it('should restore saved dark theme on init', () => {
    localStorageStore['quiz_theme'] = 'dark'
    vi.stubGlobal('matchMedia', () => ({ matches: false }))
    const Theme = loadTheme()
    Theme.init()
    expect(Theme.isDark()).toBe(true)
  })

  it('should restore saved light theme on init', () => {
    localStorageStore['quiz_theme'] = 'light'
    vi.stubGlobal('matchMedia', () => ({ matches: true }))
    const Theme = loadTheme()
    Theme.init()
    expect(Theme.isDark()).toBe(false)
  })
})
