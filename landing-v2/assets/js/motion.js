(function () {
  'use strict';

  var root = document.documentElement;
  var reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
  var editMode = window.location.hash.indexOf('edit') !== -1;

  if (reducedMotion.matches || editMode) {
    return;
  }

  function addRevealTargets() {
    var groups = [
      {
        selector: '.hero__title, .hero__lead, .hero__cta, .hero__chips, .hero__shot',
        step: 70
      },
      {
        selector: '.audience__grid',
        step: 0
      },
      {
        selector: '.pains .eyebrow, .pains .section-title, .pains .section-lead, .pains__grid',
        step: 65
      },
      {
        selector: '.how > .container > .eyebrow, .how__title, .how > .container > .section-lead, .how__grid',
        step: 65
      },
      {
        selector: '.features__head, .feature',
        step: 45
      },
      {
        selector: '.integrations__head, .integrations__rail',
        step: 80
      },
      {
        selector: '.pricing__head, .pricing__cards, .price-wl',
        step: 80
      },
      {
        selector: '.faq__head, .faq__body',
        step: 90
      },
      {
        selector: '.cta-band__title, .cta-band__lead, .cta-band__cta, .cta-band__note',
        step: 70
      },
      {
        selector: '.blog__head, .blog__grid',
        step: 90
      }
    ];

    var targets = [];

    groups.forEach(function (group) {
      document.querySelectorAll(group.selector).forEach(function (element, index) {
        if (targets.indexOf(element) !== -1) {
          return;
        }

        element.classList.add('reveal-target');
        element.style.setProperty('--reveal-delay', Math.min(index, 4) * group.step + 'ms');
        targets.push(element);
      });
    });

    return targets;
  }

  function initReveal() {
    var targets = addRevealTargets();
    root.classList.add('motion-ready');

    if (!('IntersectionObserver' in window)) {
      targets.forEach(function (element) {
        element.classList.add('is-visible');
      });
      return;
    }

    var observer = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (!entry.isIntersecting) {
          return;
        }

        entry.target.classList.add('is-visible');
        observer.unobserve(entry.target);
      });
    }, {
      rootMargin: '0px 0px -10% 0px',
      threshold: 0.08
    });

    targets.forEach(function (element) {
      observer.observe(element);
    });
  }

  function initParallax() {
    var finePointer = window.matchMedia('(hover: hover) and (pointer: fine)');

    if (!finePointer.matches) {
      return;
    }

    var config = [
      { selector: '.hero__card--tl', depth: 15 },
      { selector: '.hero__card--tr', depth: -12 },
      { selector: '.hero__card--r', depth: 18 },
      { selector: '.hero__card--l', depth: -15 },
      { selector: '.pains__decor--tl', depth: 8 },
      { selector: '.pains__decor--tr', depth: -9 },
      { selector: '.pains__decor--bl', depth: -7 },
      { selector: '.pains__decor--br', depth: 10 },
      { selector: '.cta-deco--send', depth: 8 },
      { selector: '.cta-deco--calendar', depth: -9 },
      { selector: '.cta-deco--cpc', depth: 12 },
      { selector: '.cta-deco--metrics', depth: -13 },
      { selector: '.cta-deco--pie', depth: 9 },
      { selector: '.cta-deco--bars', depth: -7 }
    ];

    var items = config.map(function (item) {
      return {
        element: document.querySelector(item.selector),
        depth: item.depth
      };
    }).filter(function (item) {
      return item.element;
    });

    if (!items.length) {
      return;
    }

    root.classList.add('motion-enhanced');

    var pointerX = 0;
    var pointerY = 0;
    var frame = 0;

    function render() {
      frame = 0;

      items.forEach(function (item) {
        item.element.style.setProperty('--parallax-x', (pointerX * item.depth).toFixed(2) + 'px');
        item.element.style.setProperty('--parallax-y', (pointerY * item.depth * 0.62).toFixed(2) + 'px');
      });
    }

    function schedule() {
      if (!frame) {
        frame = window.requestAnimationFrame(render);
      }
    }

    function onPointerMove(event) {
      pointerX = (event.clientX / window.innerWidth - 0.5) * 2;
      pointerY = (event.clientY / window.innerHeight - 0.5) * 2;
      schedule();
    }

    function reset() {
      pointerX = 0;
      pointerY = 0;
      schedule();
    }

    window.addEventListener('pointermove', onPointerMove, { passive: true });
    window.addEventListener('blur', reset);
    document.addEventListener('mouseleave', reset);
  }

  initReveal();
  initParallax();
}());
