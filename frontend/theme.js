const Theme = {
  STORAGE_KEY: 'quiz_theme',

  init() {
    const saved = localStorage.getItem(this.STORAGE_KEY);
    if (saved === 'dark') {
      this.enableDark();
    } else if (saved === 'light') {
      this.enableLight();
    } else {
      this.matchSystem();
    }
    this.renderToggle();
  },

  matchSystem() {
    if (window.matchMedia('(prefers-color-scheme: dark)').matches) {
      this.enableDark();
    } else {
      this.enableLight();
    }
  },

  enableDark() {
    document.documentElement.classList.add('dark');
    localStorage.setItem(this.STORAGE_KEY, 'dark');
    this.renderToggle();
  },

  enableLight() {
    document.documentElement.classList.remove('dark');
    localStorage.setItem(this.STORAGE_KEY, 'light');
    this.renderToggle();
  },

  toggle() {
    if (document.documentElement.classList.contains('dark')) {
      this.enableLight();
    } else {
      this.enableDark();
    }
  },

  isDark() {
    return document.documentElement.classList.contains('dark');
  },

  renderToggle() {
    const existing = document.getElementById('theme-toggle');
    if (existing) {
      existing.innerHTML = this.isDark()
        ? '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="5"/><line x1="12" y1="1" x2="12" y2="3"/><line x1="12" y1="21" x2="12" y2="23"/><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/><line x1="1" y1="12" x2="3" y2="12"/><line x1="21" y1="12" x2="23" y2="12"/><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/></svg>'
        : '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/></svg>';
    }
  },
};

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => Theme.init());
} else {
  Theme.init();
}
