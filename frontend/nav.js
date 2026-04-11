(() => {
  const MOBILE_NAV_BREAKPOINT = 840;

  function closeNav(nav) {
    nav.classList.remove('nav-mobile-open');
    const toggle = nav.querySelector('[data-nav-toggle]');
    if (toggle) toggle.setAttribute('aria-expanded', 'false');
  }

  function toggleNav(nav) {
    const willOpen = !nav.classList.contains('nav-mobile-open');
    nav.classList.toggle('nav-mobile-open', willOpen);
    const toggle = nav.querySelector('[data-nav-toggle]');
    if (toggle) toggle.setAttribute('aria-expanded', willOpen ? 'true' : 'false');
  }

  function initNavMenus() {
    const navs = Array.from(document.querySelectorAll('.nav'));
    if (!navs.length) return;

    navs.forEach((nav) => {
      const toggle = nav.querySelector('[data-nav-toggle]');
      if (!toggle) return;

      toggle.addEventListener('click', (event) => {
        event.stopPropagation();
        toggleNav(nav);
      });

      nav.addEventListener('click', (event) => {
        if (event.target.closest('a') || event.target.closest('button.auth-link-btn')) {
          closeNav(nav);
        }
      });
    });

    document.addEventListener('click', (event) => {
      navs.forEach((nav) => {
        if (!nav.contains(event.target)) closeNav(nav);
      });
    });

    document.addEventListener('keydown', (event) => {
      if (event.key !== 'Escape') return;
      navs.forEach((nav) => closeNav(nav));
    });

    window.addEventListener('resize', () => {
      if (window.innerWidth > MOBILE_NAV_BREAKPOINT) {
        navs.forEach((nav) => closeNav(nav));
      }
    });
  }

  document.addEventListener('DOMContentLoaded', initNavMenus);
})();
