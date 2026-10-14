(function () {
  var header = document.querySelector('.site-header');
  var toggle = document.querySelector('.nav-toggle');
  if (toggle && header) {
    toggle.addEventListener('click', function () {
      header.classList.toggle('is-open');
      toggle.setAttribute(
        'aria-expanded',
        header.classList.contains('is-open') ? 'true' : 'false'
      );
    });
  }

  var path = window.location.pathname.split('/').pop() || '';
  document.querySelectorAll('.site-nav a[data-nav]').forEach(function (link) {
    if (link.getAttribute('data-nav') === path) {
      link.classList.add('is-active');
    }
  });

  var tocDetails = document.querySelector('.toc-details');
  if (tocDetails) {
    var desktopToc = window.matchMedia('(min-width: 901px)');
    var syncToc = function () {
      tocDetails.open = desktopToc.matches;
    };
    if (typeof desktopToc.addEventListener === 'function') {
      desktopToc.addEventListener('change', syncToc);
    } else if (typeof desktopToc.addListener === 'function') {
      desktopToc.addListener(syncToc);
    }
    syncToc();
  }
})();
