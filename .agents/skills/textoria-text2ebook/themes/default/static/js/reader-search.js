/* Search the script-loaded book index without leaving the reading view. */
(() => {
  const input = document.getElementById('readerQuery');
  if (!input) return;
  const panel = document.getElementById('readerSearch');
  const results = document.getElementById('readerResults');
  const count = document.getElementById('readerResultCount');
  const list = document.getElementById('readerResultList');
  const more = document.getElementById('readerMoreResults');
  const button = document.getElementById('toggleReaderRight');
  const root = new URL(document.getElementById('readerSearchScript').dataset.siteRoot || './', location.href);
  const storageKey = 'textoria.readerQuery.' + root.href;
  const ready = Array.isArray(window.TEXTORIA_SEARCH_INDEX?.paragraphs);
  const data = ready ? window.TEXTORIA_SEARCH_INDEX.paragraphs : [];
  let rows = [], limit = 50;
  const close = (focus = false) => {
    panel.hidden = true;button.setAttribute('aria-expanded', 'false');
    if (focus) button.focus({preventScroll: true});
  };
  const show = () => {
    panel.hidden = false;panel.scrollTop = 0;button.setAttribute('aria-expanded', 'true');input.focus({preventScroll: true});
  };
  button.addEventListener('click', () => panel.hidden ? show() : close());
  document.addEventListener('click', event => {
    if (!panel.hidden && !panel.contains(event.target) && !button.contains(event.target)) close();
  });
  panel.addEventListener('keydown', event => {
    if (event.key === 'Escape') { event.preventDefault();close(true); }
  });
  list.addEventListener('click', event => {
    if (event.target.closest('a')) close();
  });
  const marked = (parent, text, query) => {
    let start = 0, position;
    while (query && (position = text.indexOf(query, start)) !== -1) {
      parent.append(document.createTextNode(text.slice(start, position)));
      const mark = document.createElement('mark');mark.textContent = query;parent.append(mark);
      start = position + query.length;
    }
    parent.append(document.createTextNode(text.slice(start)));
  };
  const highlight = query => {
    const content = document.getElementById('readerContent');
    content.querySelectorAll('mark[data-reader-match]').forEach(mark => mark.replaceWith(document.createTextNode(mark.textContent)));
    content.normalize();
    if (!query) return;
    content.querySelectorAll('p[data-paragraph-number]').forEach(paragraph => {
      const walker = document.createTreeWalker(paragraph, NodeFilter.SHOW_TEXT);
      const nodes = [];while (walker.nextNode()) nodes.push(walker.currentNode);
      nodes.forEach(node => {
        if (!node.textContent.includes(query)) return;
        const fragment = document.createDocumentFragment();marked(fragment, node.textContent, query);
        fragment.querySelectorAll('mark').forEach(mark => mark.dataset.readerMatch = 'true');
        node.replaceWith(fragment);
      });
    });
  };
  const render = () => {
    list.replaceChildren();
    rows.slice(0, limit).forEach(row => {
      const link = document.createElement('a');link.className = 'reader-result';
      // Index paths are relative to the book root, including on nested read pages.
      const target = new URL(row.href, root);
      if (target.origin !== root.origin || !target.pathname.startsWith(root.pathname)) return;
      target.searchParams.set('q', input.value.trim());link.href = target.href;
      const title = document.createElement('span');title.className = 'reader-result-title';
      title.textContent = (row.division_title || '') + ' · 第 ' + row.paragraph_index + ' 段';link.append(title);
      const text = String(row.text || ''), query = input.value.trim();
      const hit = text.indexOf(query), start = Math.max(0, hit - 28), end = Math.min(text.length, Math.max(hit + query.length, start + 110));
      marked(link, (start ? '…' : '') + text.slice(start, end) + (end < text.length ? '…' : ''), query);
      list.append(link);
    });
    more.hidden = rows.length <= limit;
  };
  function search() {
    const query = input.value.trim();
    try { sessionStorage.setItem(storageKey, query); } catch { /* Storage is optional. */ }
    try {
      const url = new URL(location.href);
      if (query) url.searchParams.set('q', query);else url.searchParams.delete('q');
      history.replaceState(null, '', url);
    } catch { /* Direct-file history can be unavailable. */ }
    results.hidden = !query;limit = 50;
    rows = query ? data.filter(row => row.text.includes(query)) : [];
    count.textContent = ready ? `共 ${rows.length} 筆` : '搜尋資料遺失，請重新取得完整網站資料夾。';
    render();highlight(query);
  }
  more.addEventListener('click', () => { limit += 50;render(); });
  input.addEventListener('input', search);
  const params = new URL(location.href).searchParams;
  let saved = '';try { saved = sessionStorage.getItem(storageKey) || ''; } catch { /* Storage is optional. */ }
  input.value = params.has('q') ? params.get('q') : saved;
  search();
  if (location.pathname.endsWith('/search.html') && !location.hash) show();
  const scrollTarget = () => {
    let target;try { target = document.getElementById(decodeURIComponent(location.hash.slice(1))); } catch { return; }
    if (target) requestAnimationFrame(() => requestAnimationFrame(() => target.scrollIntoView({block: 'start'})));
  };
  scrollTarget();window.addEventListener('hashchange', scrollTarget);
})();
