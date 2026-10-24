(() => {
  const path = location.pathname.replace(/\/$/, '') || '/';
  document.querySelectorAll('.site-header nav a').forEach(link => {
    const target = new URL(link.href, location.origin).pathname.replace(/\/$/, '') || '/';
    const active = target === '/' ? path === '/' : path === target || path.startsWith(target + '/');
    link.classList.toggle('is-active', active);
    if (active) link.setAttribute('aria-current', 'page');
  });

  const header = document.querySelector('.site-header');
  const nav = header?.querySelector('nav');
  if (header && nav) {
    const toggle = document.createElement('button');
    toggle.className = 'nav-toggle';
    toggle.type = 'button';
    toggle.setAttribute('aria-label', 'Mở điều hướng');
    toggle.setAttribute('aria-expanded', 'false');
    toggle.innerHTML = '<span></span><span></span>';
    header.insertBefore(toggle, nav);
    toggle.addEventListener('click', () => {
      const open = header.classList.toggle('nav-open');
      toggle.setAttribute('aria-expanded', String(open));
      toggle.setAttribute('aria-label', open ? 'Đóng điều hướng' : 'Mở điều hướng');
    });
  }

  document.querySelectorAll('a[target="_blank"]').forEach(link => link.rel = 'noopener noreferrer');
  document.querySelectorAll('form').forEach(form => form.addEventListener('submit', () => {
    const submit = form.querySelector('button[type="submit"], input[type="submit"]');
    if (submit && !submit.dataset.keepEnabled) {
      submit.setAttribute('aria-busy', 'true');
      setTimeout(() => submit.removeAttribute('aria-busy'), 8000);
    }
  }));
})();
