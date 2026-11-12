const readerIcons = {
  leftExpand: '<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="M4 6a2 2 0 0 1 2-2h12a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6"/><path d="M9 4v16"/><path d="m14 10 2 2-2 2"/></svg>',
  leftCollapse: '<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="M4 6a2 2 0 0 1 2-2h12a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6"/><path d="M9 4v16"/><path d="m15 10-2 2 2 2"/></svg>',
  right: '<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"><circle cx="10.5" cy="10.5" r="6.5"/><path d="m16 16 4.5 4.5"/></svg>' 
};

function initReaderChrome() {
  const layout = document.querySelector('.layout');
  const left = document.getElementById('toggleReaderLeft');
  const right = document.getElementById('toggleReaderRight');
  const mobile = window.matchMedia('(max-width: 910px)');
  const bookRoot = new URL('../../', document.querySelector('script[src*="js/reader.js"]').src).href;
  const storageKey = 'textoria.readerSidebar.' + bookRoot;
  let desktopOpen = false;
  try { desktopOpen = sessionStorage.getItem(storageKey) === 'open'; } catch { /* Storage is optional. */ }

  if (left) {
    const sync = () => {
      left.setAttribute("aria-expanded", String(Boolean(layout && !layout.classList.contains("reader-left-collapsed"))));
      left.innerHTML = layout && layout.classList.contains('reader-left-collapsed')
        ? readerIcons.leftExpand
        : readerIcons.leftCollapse;
    };
    if (layout) layout.classList.toggle('reader-left-collapsed', mobile.matches || !desktopOpen);
    sync();
    left.addEventListener('click', () => {
      if (!layout) return;
      layout.classList.toggle('reader-left-collapsed');
      if (!mobile.matches) {
        desktopOpen = !layout.classList.contains('reader-left-collapsed');
        try { sessionStorage.setItem(storageKey, desktopOpen ? 'open' : 'closed'); } catch { /* Keep the current page usable. */ }
      }
      sync();
    });
    document.getElementById('readerSidebar')?.addEventListener('click', event => {
      if (mobile.matches && event.target.closest('.toc-link, .toc-doc')) {
        layout?.classList.add('reader-left-collapsed');
        sync();
      }
    });
    mobile.addEventListener('change', () => {
      if (layout) layout.classList.toggle('reader-left-collapsed', mobile.matches || !desktopOpen);
      sync();
    });
  }
  if (right) right.innerHTML = readerIcons.right;

}

function initTocTree() {
  const links = [...document.querySelectorAll('.toc-link')];
  if (!links.length) return;
  const bookRoot = new URL('../../', document.querySelector('script[src*="js/reader.js"]').src).href;
  const storageKey = 'textoria.readerBranches.' + bookRoot;
  let expanded = new Set();
  try {
    const saved = JSON.parse(sessionStorage.getItem(storageKey) || '[]');
    if (Array.isArray(saved)) expanded = new Set(saved);
  } catch { /* Navigation works without storage. */ }
  const save = () => {
    try { sessionStorage.setItem(storageKey, JSON.stringify([...expanded])); } catch { /* Keep in-page state. */ }
  };
  const branches = new Map();
  document.querySelectorAll('.toc-toggle').forEach(button => {
    const item = button.closest('.toc-item');
    const children = item?.querySelector(':scope > .toc-children');
    if (!children) return;
    const id = button.dataset.tocToggle;
    const title = (button.getAttribute('aria-label') || '').replace(/^(展開|收合) /, '');
    const setExpanded = open => {
      button.setAttribute('aria-expanded', String(open));
      button.setAttribute('aria-label', `${open ? '收合' : '展開'} ${title}`);
      button.textContent = open ? '▾' : '▸';
      children.hidden = !open;
      if (open) expanded.add(id);else expanded.delete(id);
    };
    branches.set(item, setExpanded);
    setExpanded(expanded.has(id));
    button.addEventListener('click', () => {
      setExpanded(button.getAttribute('aria-expanded') !== 'true');
      save();select(currentLink);
    });
  });
  const sections = [...document.querySelectorAll('#readerContent .reader-section')];
  const linkById = new Map();
  links.forEach(link => {
    const url = new URL(link.href);
    if (url.hash) {
      try {
        const id = decodeURIComponent(url.hash.slice(1));
        if (sections.some(section => section.id === id)) linkById.set(id, link);
      } catch {
        /* Ignore malformed anchors. */
      }
    }
  });
  const pageLink = links.find(link => link.classList.contains('active'));
  if (sections[0] && pageLink) linkById.set(sections[0].id, pageLink);
  let currentLink = null;
  const select = (link, reveal = false) => {
    if (!link) return;
    const changed = link !== currentLink;
    currentLink = link;
    if (reveal || changed) {
      let parent = link.closest('.toc-item')?.parentElement?.closest('.toc-item');
      while (parent) {
        branches.get(parent)?.(true);
        parent = parent.parentElement?.closest('.toc-item');
      }
      save();
    }
    let visibleLink = link;
    let item = link.closest('.toc-item');
    while (item) {
      const children = item.parentElement;
      if (children?.classList.contains('toc-children') && children.hidden) {
        visibleLink = children.parentElement.querySelector(':scope > .toc-link') || visibleLink;
      }
      item = children?.closest('.toc-item');
    }
    links.forEach(entry => {
      entry.classList.toggle('active', entry === visibleLink);
      if (entry === visibleLink) entry.setAttribute('aria-current', 'location');
      else entry.removeAttribute('aria-current');
    });
    link = visibleLink;
    const side = link.closest('.side');
    if (side && link.getClientRects().length) {
      const bounds = side.getBoundingClientRect();
      const rect = link.getBoundingClientRect();
      if (rect.top < bounds.top) side.scrollTop += rect.top - bounds.top;
      else if (rect.bottom > bounds.bottom) side.scrollTop += rect.bottom - bounds.bottom;
    }
  };
  const showCurrent = () => {
    let target = null;
    try {
      target = document.getElementById(decodeURIComponent(location.hash.slice(1)));
    } catch {
      /* Fall back to the current top-level division for malformed anchors. */
    }
    const section = target?.closest('.reader-section');
    select(linkById.get(section?.id) || pageLink, true);
  };
  showCurrent();
  window.addEventListener('hashchange', showCurrent);
  document.getElementById('toggleReaderLeft')?.addEventListener('click', () => {
    if (!document.querySelector('.layout')?.classList.contains('reader-left-collapsed')) select(currentLink, true);
  });
  links.forEach(link => link.addEventListener('click', () => {
    const url = new URL(link.href);
    if (url.pathname === location.pathname && url.hash === location.hash) showCurrent();
  }));
  let pending = false;
  window.addEventListener('scroll', () => {
    if (pending) return;
    pending = true;
    window.requestAnimationFrame(() => {
      pending = false;
      const threshold = (document.querySelector('header')?.getBoundingClientRect().bottom || 0) + 24;
      let section = sections[0];
      for (const candidate of sections) {
        if (candidate.getBoundingClientRect().top > threshold) break;
        section = candidate;
      }
      select(linkById.get(section?.id));
    });
  }, { passive: true });
}

function initReaderPageEnter() {
  const content = document.getElementById('readerContent');
  const layout = document.querySelector('.layout');
  if (!content) return;
  window.requestAnimationFrame(() => {
    window.requestAnimationFrame(() => {
      if (layout) layout.classList.remove('reader-entering');
      content.classList.add('reader-slide-active');
    });
  });
}

initReaderChrome();
initTocTree();
initReaderPageEnter();
