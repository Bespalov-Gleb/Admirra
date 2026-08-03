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


  document.documentElement.classList.add('motion-scroll');

  const easeOut = 'cubic-bezier(0.22, 0.61, 0.36, 1)';
  const easeSoft = 'cubic-bezier(0.16, 1, 0.3, 1)';
  const runningAnimations = new Set();
  let motionAllowed = true;


  const shift = (x, y, scale = 1) => {
    const parts = [];
    if (x) parts.push(`translate3d(${x}px, 0, 0)`);
    else if (y) parts.push(`translate3d(0, ${y}px, 0)`);
    if (scale !== 1) parts.push(`scale(${scale})`);
    const transform = parts.join(' ');
    return transform ? { from: { transform }, to: { transform: 'translate3d(0, 0, 0) scale(1)' } } : { from: {}, to: {} };
  };


  const presets = {
    rise:      { duration: 700, easing: easeOut,  frames: () => shift(0, 13) },
    lead:      { duration: 720, easing: easeOut,  frames: () => shift(0, 11) },
    card:      { duration: 760, easing: easeSoft, frames: () => shift(0, 18, 0.988) },
    left:      { duration: 780, easing: easeSoft, frames: () => shift(-24, 0) },
    right:     { duration: 780, easing: easeSoft, frames: () => shift(24, 0) },
    image:     { duration: 980, easing: easeSoft, frames: () => shift(0, 22, 0.99), clip: true },
    fade:      { duration: 720, easing: easeOut,  frames: () => shift(0, 0) },
    heroTitle: { duration: 940, easing: easeSoft, frames: () => shift(0, 24), clip: true },

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
  ];

  revealGroups.forEach((group) => {
    document.querySelectorAll(group.selector).forEach((element, index) => {
      arm(element, group.preset, (index % group.batch) * group.stagger);
    });
  });


  document.querySelectorAll('.feature').forEach((element, index) => {
    const presetName = desktopRail.matches ? (index % 2 ? 'right' : 'left') : 'card';
    arm(element, presetName, 0);
  });


  document.querySelectorAll('.cta-band__cta, .cta-band__note').forEach((element, index) => {
    const presetName = desktopRail.matches ? 'riseCenter' : 'rise';
    arm(element, presetName, index * 70);
  });


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


(() => {
  const items = document.querySelectorAll('.faq-item');
  if (!items.length) return;

  const reduce = window.matchMedia('(prefers-reduced-motion: reduce)');
  const easeOpen = 'cubic-bezier(0.16, 1, 0.3, 1)';   // мягкий, глубокий ease-out
  const easeClose = 'cubic-bezier(0.4, 0, 0.2, 1)';   // ровный ease-in-out без рывка в конце

  items.forEach((item) => {
    const summary = item.querySelector('.faq-item__q');
    const answer = item.querySelector('.faq-item__a');
    if (!summary || !answer) return;

    let anim = null;

    const reset = () => {
      answer.style.height = '';
      answer.style.paddingTop = '';
      answer.style.paddingBottom = '';
      answer.style.opacity = '';
      answer.style.overflow = '';
    };


    const animateTo = (opening) => {
      if (anim) { anim.cancel(); anim = null; }
      if (opening) item.open = true;                // рендерим ответ для измерения

      answer.style.overflow = 'hidden';
      const cs = getComputedStyle(answer);
      const full = {
        height: `${answer.scrollHeight}px`,         // полная высота контента + паддинги
        paddingTop: cs.paddingTop,
        paddingBottom: cs.paddingBottom,
        opacity: 1,
      };
      const none = { height: '0px', paddingTop: '0px', paddingBottom: '0px', opacity: 0 };

      const current = answer.animate(
        opening ? [none, full] : [full, none],
        { duration: opening ? 380 : 320, easing: opening ? easeOpen : easeClose, fill: 'both' },
      );
      anim = current;

      current.finished.then(() => {
        if (anim !== current) return;               // успел стартовать новый тоггл
        if (!opening) item.open = false;            // скрываем нативно ДО отката стилей
        anim.cancel();                              // отпускаем удержание fill
        anim = null;
        reset();
      }).catch(() => {});
    };

    summary.addEventListener('click', (event) => {
      if (reduce.matches || !answer.animate) return;   // штатное поведение
      event.preventDefault();
      animateTo(!item.open);
    });
  });
})();
