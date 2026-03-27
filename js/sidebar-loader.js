/**
 * Sidebar Loader - Dynamically populate meeting navigation from meetings.json
 */
(function() {
  'use strict';

  function getCurrentPageFilename() {
    var p = window.location.pathname;
    return p.substring(p.lastIndexOf('/') + 1) || '';
  }

  function getMeetingsJsonPath() {
    var parts = window.location.pathname.split('/').filter(Boolean);
    if (parts.length > 0) {
      parts.pop();
      parts.push('data', 'meetings.json');
      return '/' + parts.join('/');
    }
    return 'data/meetings.json';
  }

  function initializeSidebar() {
    var container = document.getElementById('meeting-nav');
    if (!container) return;

    fetch(getMeetingsJsonPath())
      .then(function(r) { return r.json(); })
      .then(function(meetings) {
        var cur = getCurrentPageFilename();
        container.innerHTML = meetings.map(function(m) {
          var cls = m.file === cur ? 'nav-link active' : 'nav-link';
          return '<a class="' + cls + '" href="' + m.file + '">' +
            m.title + ' <span style="opacity:.6;font-size:.75rem;">' + m.date + '</span></a>';
        }).join('\n  ');
      })
      .catch(function() {});
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initializeSidebar);
  } else {
    initializeSidebar();
  }
})();
