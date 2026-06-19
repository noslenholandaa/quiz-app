const Theme = {
  STORAGE_KEY: 'quiz_theme',
  _initialized: false,

  init() {
    if (this._initialized) return;
    this._initialized = true;
    const saved = localStorage.getItem(this.STORAGE_KEY);
    if (saved === 'dark') {
      this.enableDark();
    } else if (saved === 'light') {
      this.enableLight();
    } else {
      this.matchSystem();
    }
    this.renderToggle();
    this._watchThemeToggle();
  },

  _watchThemeToggle() {
    const target = document.getElementById('theme-toggle');
    if (target && !target.dataset.themeBound) {
      target.dataset.themeBound = '1';
      target.addEventListener('click', (e) => {
        if (!e.target.closest('#theme-toggle')) return;
        this.toggle();
      });
    }
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
    const isDark = this.isDark();
    document.querySelectorAll('#theme-toggle').forEach(el => {
      el.innerHTML = isDark
        ? '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="5"/><path d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42"/></svg>'
        : '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/></svg>';
    });
    document.querySelectorAll('.theme-icon-sun, .theme-icon-moon').forEach(el => {
      el.style.display = isDark ? '' : '';
    });
    document.querySelectorAll('.theme-icon-sun').forEach(el => {
      el.style.display = isDark ? '' : 'none';
    });
    document.querySelectorAll('.theme-icon-moon').forEach(el => {
      el.style.display = isDark ? 'none' : '';
    });
  },
};

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => Theme.init());
} else {
  Theme.init();
}
