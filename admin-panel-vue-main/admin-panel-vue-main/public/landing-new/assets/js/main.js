(() => {
  const header = document.querySelector('.site-header');
  const toggle = document.querySelector('.site-header__burger');
  const menu = document.querySelector('#mobile-nav');

  if (!header || !toggle || !menu) return;

  const setMenuOpen = (open) => {
    toggle.setAttribute('aria-expanded', String(open));
    toggle.setAttribute('aria-label', open ? 'Закрыть меню' : 'Открыть меню');
    menu.hidden = !open;
    header.classList.toggle('site-header--menu-open', open);
  };

  toggle.addEventListener('click', () => {
    setMenuOpen(toggle.getAttribute('aria-expanded') !== 'true');
  });

  menu.addEventListener('click', (event) => {
    if (event.target.closest('a')) setMenuOpen(false);
  });

  document.addEventListener('click', (event) => {
    if (!header.contains(event.target)) setMenuOpen(false);
  });

  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape') {
      setMenuOpen(false);
      toggle.focus();
    }
  });

  const desktop = window.matchMedia('(min-width: 691px)');
  const closeOnDesktop = (event) => {
    if (event.matches) setMenuOpen(false);
  };

  if (desktop.addEventListener) desktop.addEventListener('change', closeOnDesktop);
  else desktop.addListener(closeOnDesktop);
})();
