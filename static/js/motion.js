// Small touches that make the site feel alive: a ripple where you tap,
// and cards that slide in as you scroll. Nothing runs for people who
// asked their device for less motion.
(function () {
  var reduce = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  if (reduce) { return; }

  // ripple from the exact spot you tapped or clicked
  var RIPPLE = '.btn, .btn-message, .wechat-btn, .wechat-login, .chip, .icon-btn, .gallery-thumb, .seller-link, .gallery-expand';
  document.addEventListener('pointerdown', function (event) {
    var el = event.target.closest(RIPPLE);
    if (!el || el.disabled) { return; }
    var rect = el.getBoundingClientRect();
    var size = Math.max(rect.width, rect.height) * 2;
    var dot = document.createElement('span');
    dot.className = 'ripple';
    dot.style.width = size + 'px';
    dot.style.height = size + 'px';
    dot.style.left = (event.clientX - rect.left - size / 2) + 'px';
    dot.style.top = (event.clientY - rect.top - size / 2) + 'px';
    el.classList.add('has-ripple');
    el.appendChild(dot);
    // remove it when the animation ends (the timer is a backup for paused tabs)
    dot.addEventListener('animationend', function () { dot.remove(); });
    setTimeout(function () { dot.remove(); }, 800);
  });

  // cards slide in when they scroll into view, one after another
  if (!('IntersectionObserver' in window)) { return; }
  var items = document.querySelectorAll('.listing-card, .mini-card, .steps li, [data-reveal]');
  var observer = new IntersectionObserver(function (entries) {
    var shown = 0;
    entries.forEach(function (entry) {
      if (!entry.isIntersecting) { return; }
      var el = entry.target;
      observer.unobserve(el);
      var delay = shown++ * 70;
      el.style.transitionDelay = delay + 'ms';
      el.classList.add('is-revealed');
      // then hand the element back to its normal hover effects
      setTimeout(function () {
        el.classList.remove('will-reveal', 'is-revealed');
        el.style.transitionDelay = '';
      }, delay + 650);
    });
  }, { rootMargin: '0px 0px -40px 0px' });
  for (var i = 0; i < items.length; i++) {
    items[i].classList.add('will-reveal');
    observer.observe(items[i]);
  }
})();
