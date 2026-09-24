// Public document navigation only: no auth, analytics or landing-only widgets.
(() => {
  const header = document.querySelector('.site-header')
  const button = header?.querySelector('.site-header__burger')
  const menu = header?.querySelector('#mobile-nav')
  if (!button || !menu) return
  const setOpen = (open) => {
    menu.hidden = !open
    button.setAttribute('aria-expanded', String(open))
    button.setAttribute('aria-label', open ? 'Закрыть меню' : 'Открыть меню')
  }
  button.addEventListener('click', () => setOpen(menu.hidden))
  menu.addEventListener('click', (event) => {
    if (event.target.closest('a')) setOpen(false)
  })
  document.addEventListener('click', (event) => {
    if (!header.contains(event.target)) setOpen(false)
  })
  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape' && !menu.hidden) {
      setOpen(false)
      button.focus()
    }
  })
  header.addEventListener('focusout', (event) => {
    if (!header.contains(event.relatedTarget)) setOpen(false)
  })
  window.matchMedia('(max-width: 1000px)').addEventListener('change', () => setOpen(false))
})()
