// ═══ AdMirra landing — минимальный интерактив ═══
// FAQ-аккордеон: если верстаешь на <details>/<summary> — JS вообще не нужен.
// Этот код нужен только для варианта с div-аккордеоном:
document.querySelectorAll('[data-accordion-toggle]').forEach((btn) => {
  btn.addEventListener('click', () => btn.closest('[data-accordion]')?.classList.toggle('open'))
})

// Бургер-меню на мобиле
document.querySelector('[data-burger]')?.addEventListener('click', () => {
  document.querySelector('[data-nav]')?.classList.toggle('open')
})
