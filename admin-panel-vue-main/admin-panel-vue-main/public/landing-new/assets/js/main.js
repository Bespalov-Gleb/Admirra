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

(() => {
  const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
  const desktopRail = window.matchMedia('(min-width: 691px)');

  if (reducedMotion.matches || !Element.prototype.animate) return;

  /* Класс и скрытое состояние ставит один и тот же скрипт: если он не выполнится,
     ничего не прячется и весь контент виден — «осиротевшего» invisible-контента нет. */
  document.documentElement.classList.add('motion-scroll');

  const easeOut = 'cubic-bezier(0.22, 0.61, 0.36, 1)';
  const easeSoft = 'cubic-bezier(0.16, 1, 0.3, 1)';
  const runningAnimations = new Set();
  let motionAllowed = true;

  /* translate/scale собираем строкой, чтобы движение шло на композиторе. */
  const shift = (x, y, scale = 1) => {
    const parts = [];
    if (x) parts.push(`translate3d(${x}px, 0, 0)`);
    else if (y) parts.push(`translate3d(0, ${y}px, 0)`);
    if (scale !== 1) parts.push(`scale(${scale})`);
    const transform = parts.join(' ');
    return transform ? { from: { transform }, to: { transform: 'translate3d(0, 0, 0) scale(1)' } } : { from: {}, to: {} };
  };

  /* Небольшой словарь «характеров» появления. Роль блока определяет движение,
     поэтому лендинг не выглядит однообразным, но каждый эффект короткий и лёгкий. */
  const presets = {
    rise:      { duration: 700, easing: easeOut,  frames: () => shift(0, 13) },
    lead:      { duration: 720, easing: easeOut,  frames: () => shift(0, 11) },
    card:      { duration: 760, easing: easeSoft, frames: () => shift(0, 18, 0.988) },
    left:      { duration: 780, easing: easeSoft, frames: () => shift(-24, 0) },
    right:     { duration: 780, easing: easeSoft, frames: () => shift(24, 0) },
    image:     { duration: 980, easing: easeSoft, frames: () => shift(0, 22, 0.99), clip: true },
    fade:      { duration: 720, easing: easeOut,  frames: () => shift(0, 0) },
    heroTitle: { duration: 940, easing: easeSoft, frames: () => shift(0, 24), clip: true },
    /* Для элементов, центрируемых через translateX(-50%): сохраняем -50% в
       кадрах, иначе reveal-transform сбивает центровку и элемент уезжает вправо. */
    riseCenter:{ duration: 720, easing: easeOut,  frames: () => ({ from: { transform: 'translate(-50%, 14px)' }, to: { transform: 'translate(-50%, 0)' } }) },
  };

  const play = (element, presetName, delay = 0) => {
    if (!element || element.dataset.motionRevealed === 'true' || !motionAllowed) return;

    const preset = presets[presetName] || presets.rise;
    element.dataset.motionRevealed = 'true';
    element.classList.add('is-revealed');

    const { from, to } = preset.frames();
    const start = { opacity: 0, ...from };
    const end = { opacity: 1, ...to };

    if (preset.clip) {
      start.clipPath = 'inset(0 0 18% 0 round 3px)';
      end.clipPath = 'inset(0 0 0 0 round 3px)';
    }

    const animation = element.animate([start, end], {
      duration: preset.duration,
      delay,
      easing: preset.easing,
      fill: 'backwards',
    });

    runningAnimations.add(animation);
    animation.finished
      .catch(() => {})
      .finally(() => runningAnimations.delete(animation));
  };

  /* Помечаем цель data-reveal сразу — CSS прячет её до попадания в вид,
     поэтому нет вспышки «видно → спрятали → проявили». */
  const arm = (element, presetName, delay = 0) => {
    element.setAttribute('data-reveal', '');
    element.dataset.motionPreset = presetName;
    element.dataset.motionDelay = String(delay);
    revealObserver.observe(element);
  };

  const revealObserver = new IntersectionObserver((entries, observer) => {
    entries.forEach((entry) => {
      if (!entry.isIntersecting) return;
      const element = entry.target;
      observer.unobserve(element);
      play(element, element.dataset.motionPreset, Number(element.dataset.motionDelay || 0));
    });
  }, {
    threshold: 0.12,
    rootMargin: '0px 0px -8% 0px',
  });

  /* Первый экран: короткий каскад «смысл → действие → продукт». Прячем
     hero сразу и проявляем на следующем кадре, чтобы не было мигания. */
  const heroSequence = [
    ['.hero__title', 'heroTitle', 0],
    ['.hero__lead', 'lead', 110],
    ['.hero__cta', 'rise', 210],
    ['.hero__chips', 'rise', 290],
  ];

  heroSequence.forEach(([selector]) => {
    const el = document.querySelector(selector);
    if (el) el.setAttribute('data-reveal', '');
  });

  requestAnimationFrame(() => {
    heroSequence.forEach(([selector, presetName, delay]) => {
      play(document.querySelector(selector), presetName, delay);
    });
  });

  /* LCP-дашборд НЕ прячем через opacity — иначе откладывается Largest Contentful
     Paint и всплывают плавающие карты. Картинка видна с первого кадра (opacity
     остаётся 1), даём только лёгкое смещение по transform. */
  const heroShot = document.querySelector('.hero__shot');
  if (heroShot) {
    requestAnimationFrame(() => {
      const animation = heroShot.animate([
        { transform: 'translate3d(0, 16px, 0) scale(0.992)' },
        { transform: 'translate3d(0, 0, 0) scale(1)' },
      ], {
        duration: 900,
        delay: 240,
        easing: easeSoft,
        fill: 'backwards',
      });
      runningAnimations.add(animation);
      animation.finished.catch(() => {}).finally(() => runningAnimations.delete(animation));
    });
  }

  /* Группы скролл-появления. batch — сколько элементов подряд получают
     нарастающую задержку, затем волна начинается заново, чтобы каскад не тянулся. */
  const revealGroups = [
    { selector: '.aud-card', preset: 'card', stagger: 70, batch: 3 },
    { selector: '.pains .eyebrow, .pains .section-title, .pains .section-lead', preset: 'rise', stagger: 60, batch: 3 },
    { selector: '.pain-card', preset: 'card', stagger: 70, batch: 2 },
    { selector: '.how .eyebrow, .how .section-title, .how .section-lead', preset: 'rise', stagger: 60, batch: 3 },
    { selector: '.how-card', preset: 'card', stagger: 75, batch: 3 },
    { selector: '.features__head', preset: 'rise', stagger: 0, batch: 1 },
    { selector: '.integrations__eyebrow, .integrations__title', preset: 'rise', stagger: 70, batch: 2 },
    { selector: '.integrations__rail', preset: 'fade', stagger: 0, batch: 1 },
    { selector: '.pricing__eyebrow, .pricing__title, .pricing__lead', preset: 'rise', stagger: 60, batch: 3 },
    { selector: '.price-card', preset: 'card', stagger: 75, batch: 3 },
    { selector: '.price-wl', preset: 'rise', stagger: 0, batch: 1 },
    { selector: '.faq__head', preset: 'rise', stagger: 0, batch: 1 },
    { selector: '.faq__visual', preset: 'image', stagger: 0, batch: 1 },
    { selector: '.faq__list', preset: 'rise', stagger: 0, batch: 1 },
    { selector: '.cta-band__title, .cta-band__lead', preset: 'rise', stagger: 65, batch: 2 },
    { selector: '.blog__head', preset: 'rise', stagger: 0, batch: 1 },
    { selector: '.blog-card', preset: 'card', stagger: 70, batch: 3 },
  ];

  revealGroups.forEach((group) => {
    document.querySelectorAll(group.selector).forEach((element, index) => {
      arm(element, group.preset, (index % group.batch) * group.stagger);
    });
  });

  /* Фича-ряды получают лёгкий боковой заход, поочерёдно слева и справа —
     только на десктопе, чтобы узкий экран не ловил горизонтальный сдвиг. */
  document.querySelectorAll('.feature').forEach((element, index) => {
    const presetName = desktopRail.matches ? (index % 2 ? 'right' : 'left') : 'card';
    arm(element, presetName, 0);
  });

  /* CTA-кнопка и капсула на десктопе центрируются через translateX(-50%),
     поэтому им нужен пресет, сохраняющий -50%. На мобиле у них обычное
     потоковое позиционирование (transform: none) — там достаточно 'rise'. */
  document.querySelectorAll('.cta-band__cta, .cta-band__note').forEach((element, index) => {
    const presetName = desktopRail.matches ? 'riseCenter' : 'rise';
    arm(element, presetName, index * 70);
  });

  /* Вертикальный скролл мягко прокатывает ленту интеграций по горизонтали.
     На touch-экранах остаётся нативный горизонтальный swipe без автосмещения. */
  const integrations = document.querySelector('.integrations');
  const rail = integrations?.querySelector('.integrations__rail');
  let railActive = false;
  let railFrame = 0;
  let railCurrent = 0;
  let railTarget = 0;

  const renderRail = () => {
    railFrame = 0;
    if (!rail || !motionAllowed || !desktopRail.matches) return;

    railCurrent += (railTarget - railCurrent) * 0.14;
    rail.style.transform = `translate3d(${railCurrent.toFixed(2)}px, 0, 0)`;

    if (Math.abs(railTarget - railCurrent) > 0.08) {
      railFrame = requestAnimationFrame(renderRail);
    }
  };

  const updateRailTarget = () => {
    if (!rail || !integrations || !railActive || !motionAllowed || !desktopRail.matches) return;

    const rect = integrations.getBoundingClientRect();
    const viewport = window.innerHeight || document.documentElement.clientHeight;
    const progress = Math.min(1, Math.max(0, (viewport - rect.top) / (viewport + rect.height)));
    const travel = Math.min(window.innerWidth * 0.115, 220);
    railTarget = (0.5 - progress) * travel * 2;

    if (!railFrame) railFrame = requestAnimationFrame(renderRail);
  };

  const resetRail = () => {
    if (!rail) return;
    railTarget = 0;
    railCurrent = 0;
    rail.style.removeProperty('transform');
  };

  if (integrations && rail) {
    const railObserver = new IntersectionObserver(([entry]) => {
      railActive = entry.isIntersecting;
      if (railActive) updateRailTarget();
    }, { rootMargin: '45% 0px 45% 0px' });

    railObserver.observe(integrations);
    window.addEventListener('scroll', updateRailTarget, { passive: true });
    window.addEventListener('resize', () => {
      if (!desktopRail.matches) resetRail();
      else updateRailTarget();
    }, { passive: true });

    const onDesktopChange = (event) => {
      if (!event.matches) resetRail();
      else updateRailTarget();
    };

    if (desktopRail.addEventListener) desktopRail.addEventListener('change', onDesktopChange);
    else desktopRail.addListener(onDesktopChange);
  }

  const disableMotion = (event) => {
    if (!event.matches) return;
    motionAllowed = false;
    document.documentElement.classList.remove('motion-scroll');
    runningAnimations.forEach((animation) => animation.cancel());
    runningAnimations.clear();
    revealObserver.disconnect();
    if (railFrame) cancelAnimationFrame(railFrame);
    resetRail();
  };

  if (reducedMotion.addEventListener) reducedMotion.addEventListener('change', disableMotion);
  else reducedMotion.addListener(disableMotion);
})();

/* Плавное раскрытие FAQ. Нативные <details> открываются мгновенно; здесь
   перехватываем клик и анимируем высоту ответа. Прогрессивное улучшение:
   без JS или при reduce-motion остаётся штатное поведение <details>. */
(() => {
  const items = document.querySelectorAll('.faq-item');
  if (!items.length) return;

  const reduce = window.matchMedia('(prefers-reduced-motion: reduce)');
  const easing = 'cubic-bezier(0.22, 0.61, 0.36, 1)';

  items.forEach((item) => {
    const summary = item.querySelector('.faq-item__q');
    const answer = item.querySelector('.faq-item__a');
    if (!summary || !answer) return;

    let anim = null;

    const clear = () => {
      answer.style.height = '';
      answer.style.opacity = '';
      answer.style.overflow = '';
      anim = null;
    };

    const run = (from, to, duration, onfinish) => {
      if (anim) anim.cancel();
      answer.style.overflow = 'hidden';
      anim = answer.animate([from, to], { duration, easing });
      anim.onfinish = () => { onfinish?.(); clear(); };
      anim.oncancel = clear;
    };

    const expand = () => {
      item.open = true;                 // рендерим ответ, чтобы измерить высоту
      const h = answer.offsetHeight;    // border-box глобально → == height
      run({ height: '0px', opacity: 0 }, { height: `${h}px`, opacity: 1 }, 320);
    };

    const collapse = () => {
      const h = answer.offsetHeight;
      run({ height: `${h}px`, opacity: 1 }, { height: '0px', opacity: 0 }, 260, () => {
        item.open = false;
      });
    };

    summary.addEventListener('click', (event) => {
      if (reduce.matches || !answer.animate) return;   // штатное поведение
      event.preventDefault();
      if (item.open) collapse();
      else expand();
    });
  });
})();
