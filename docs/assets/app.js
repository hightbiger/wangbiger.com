(function () {
  'use strict';

  // Theme toggle -------------------------------------------------------------
  var root = document.documentElement;
  var themeBtn = document.querySelector('[data-theme-toggle]');
  function paintTheme(theme) {
    if (!themeBtn) return;
    themeBtn.setAttribute('aria-label', theme === 'dark' ? '切换到浅色模式' : '切换到深色模式');
    themeBtn.innerHTML = theme === 'dark'
      ? '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true"><circle cx="12" cy="12" r="4.2"/><path d="M12 2.5v2M12 19.5v2M2.5 12h2M19.5 12h2M5 5l1.4 1.4M17.6 17.6L19 19M19 5l-1.4 1.4M6.4 17.6L5 19"/></svg>'
      : '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true"><path d="M20.5 15.2A8.6 8.6 0 0 1 8.8 3.5 8.6 8.6 0 1 0 20.5 15.2Z"/></svg>';
  }
  function setTheme(theme) {
    root.setAttribute('data-theme', theme);
    try { localStorage.setItem('theme', theme); } catch (e) {}
    paintTheme(theme);
  }
  if (themeBtn) {
    paintTheme(root.getAttribute('data-theme') === 'dark' ? 'dark' : 'light');
    themeBtn.addEventListener('click', function () {
      setTheme(root.getAttribute('data-theme') === 'dark' ? 'light' : 'dark');
    });
  }

  // Mobile nav ---------------------------------------------------------------
  var navToggle = document.querySelector('[data-nav-toggle]');
  var nav = document.getElementById('site-nav');
  if (navToggle && nav) {
    navToggle.addEventListener('click', function () {
      var open = nav.classList.toggle('open');
      navToggle.setAttribute('aria-expanded', open ? 'true' : 'false');
    });
  }

  // Search -------------------------------------------------------------------
  var searchPage = document.querySelector('[data-search]');
  if (searchPage) {
    var input = searchPage.querySelector('input[type="search"]');
    var results = searchPage.querySelector('[data-results]');
    var index = null;
    var loading = false;

    function esc(s) {
      return String(s).replace(/[&<>"']/g, function (c) {
        return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
      });
    }
    function highlight(text, q) {
      if (!q) return esc(text);
      var i = text.toLowerCase().indexOf(q.toLowerCase());
      if (i < 0) return esc(text);
      return esc(text.slice(0, i)) + '<mark>' + esc(text.slice(i, i + q.length)) + '</mark>' + esc(text.slice(i + q.length));
    }
    function render(q) {
      q = (q || '').trim();
      if (!q) {
        results.innerHTML = '<p class="hint">输入关键词开始搜索，例如「比特币」「钱包安全」「返佣」。</p>';
        return;
      }
      if (!index) return;
      var ql = q.toLowerCase();
      var hits = [];
      index.forEach(function (item) {
        var score = 0;
        if (item.title.toLowerCase().indexOf(ql) >= 0) score += 6;
        if ((item.tags || []).join(' ').toLowerCase().indexOf(ql) >= 0) score += 3;
        if ((item.category || '').toLowerCase().indexOf(ql) >= 0) score += 2;
        if ((item.summary || '').toLowerCase().indexOf(ql) >= 0) score += 1;
        if (score > 0) { item._score = score; hits.push(item); }
      });
      hits.sort(function (a, b) { return b._score - a._score || (a.date < b.date ? 1 : -1); });
      if (!hits.length) {
        results.innerHTML = '<p class="hint">没有找到与「' + esc(q) + '」相关的文章。</p>';
        return;
      }
      results.innerHTML = '<p class="hint">找到 ' + hits.length + ' 篇相关文章</p>' + hits.map(function (item) {
        return '<article class="search-hit"><h2><a href="' + item.url + '">' + highlight(item.title, q) + '</a></h2>' +
          '<p>' + highlight(item.summary || '', q) + '</p>' +
          '<p class="card-meta"><span>' + esc(item.date) + '</span><span>' + esc(item.category || '') + '</span></p></article>';
      }).join('');
    }
    function load() {
      if (loading || index) return;
      loading = true;
      fetch('/search-index.json').then(function (r) { return r.json(); }).then(function (data) {
        index = data;
        var q = new URLSearchParams(location.search).get('q') || '';
        if (input.value !== q) input.value = q;
        render(input.value);
      }).catch(function () {
        results.innerHTML = '<p class="hint">搜索索引加载失败，请稍后重试。</p>';
      });
    }
    input.addEventListener('input', function () {
      render(input.value);
      var url = new URL(location.href);
      if (input.value.trim()) url.searchParams.set('q', input.value.trim());
      else url.searchParams.delete('q');
      history.replaceState(null, '', url);
    });
    load();
    var initial = new URLSearchParams(location.search).get('q');
    if (initial) input.value = initial;
  }
})();
