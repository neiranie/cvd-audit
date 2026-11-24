() => {
  const canvas = document.createElement('canvas');
  canvas.width = canvas.height = 1;
  const ctx = canvas.getContext('2d', { willReadFrequently: true });

  // Returns [r, g, b, a] with r,g,b in 0..255 and a in 0..1.
  function parse(c) {
    const m = c.match(/^rgba?\(([^)]+)\)$/);
    if (m) {
      const p = m[1].split(/[,\s\/]+/).filter(Boolean)
        .map(t => t.endsWith('%') ? parseFloat(t) / 100 : Number(t));
      return [p[0], p[1], p[2], p.length > 3 ? p[3] : 1];
    }
    // Fallback for color(), oklch(), etc.: let the browser convert to sRGB.
    ctx.clearRect(0, 0, 1, 1);
    ctx.fillStyle = '#000';
    ctx.fillStyle = c;
    ctx.fillRect(0, 0, 1, 1);
    const d = ctx.getImageData(0, 0, 1, 1).data;
    return [d[0], d[1], d[2], d[3] / 255];
  }

  // Background we cannot measure from computed styles: media or background images
  // behind the text, and ::before/::after backgrounds. Such elements are flagged
  // `unknown` and excluded from pass/fail statistics.
  const pseudoCache = new Map();
  function pseudoBg(e) {
    if (pseudoCache.has(e)) return pseudoCache.get(e);
    let r = false;
    for (const p of ['::before', '::after']) {
      const cs = getComputedStyle(e, p);
      if (cs.content && cs.content !== 'none' && cs.content !== 'normal') {
        if ((cs.backgroundImage && cs.backgroundImage !== 'none') || parse(cs.backgroundColor)[3] > 0) r = true;
      }
    }
    pseudoCache.set(e, r);
    return r;
  }

  const MEDIA = new Set(['IMG', 'SVG', 'VIDEO', 'CANVAS', 'PICTURE']);
  function mediaBehind(el) {
    let r = el.getBoundingClientRect();
    let x = r.left + r.width / 2, y = r.top + r.height / 2;
    if (x < 0 || y < 0 || x > innerWidth || y > innerHeight) {
      el.scrollIntoView({ block: 'center', inline: 'center' }); // restored at the end
      r = el.getBoundingClientRect();
      x = r.left + r.width / 2; y = r.top + r.height / 2;
      if (x < 0 || y < 0 || x > innerWidth || y > innerHeight) return true; // cannot test
    }
    for (const e of document.elementsFromPoint(x, y)) {
      if (e === el || el.contains(e) || e.contains(el)) continue;
      if (MEDIA.has(e.tagName.toUpperCase())) return true;
      const cs = getComputedStyle(e);
      if (cs.backgroundImage && cs.backgroundImage !== 'none') return true;
      if (parse(cs.backgroundColor)[3] > 0 && !e.contains(el)) return true; // another painted box behind/over
    }
    return false;
  }

  function effectiveBg(el) {
    const chain = [];
    for (let e = el; e; e = e.parentElement) chain.push(e);
    let out = [255, 255, 255];
    let unknown = false, opacity = 1;
    for (let i = chain.length - 1; i >= 0; i--) {
      const cs = getComputedStyle(chain[i]);
      if (cs.backgroundImage && cs.backgroundImage !== 'none') unknown = true;
      if (pseudoBg(chain[i])) unknown = true;
      opacity *= parseFloat(cs.opacity);
      const [r, g, b, a] = parse(cs.backgroundColor);
      // A translucent layer that is absolutely/fixed positioned is an overlay on something we cannot see
      // from computed styles (typically a photo): the backdrop is unknown, not the page canvas.
      if (a > 0 && a < 0.99 && (cs.position === 'absolute' || cs.position === 'fixed')) unknown = true;
      if (a > 0) out = [r * a + out[0] * (1 - a), g * a + out[1] * (1 - a), b * a + out[2] * (1 - a)];
    }
    if (!unknown && mediaBehind(el)) unknown = true;
    return { rgb: out, unknown, opacity };
  }

  function blend(fg, bg) {
    const [r, g, b, a] = fg;
    return [r * a + bg[0] * (1 - a), g * a + bg[1] * (1 - a), b * a + bg[2] * (1 - a)];
  }

  function visible(el) {
    const cs = getComputedStyle(el);
    if (cs.display === 'none' || cs.visibility !== 'visible') return false;
    const r = el.getBoundingClientRect();
    return r.width > 0 && r.height > 0;
  }

  function isBlockLike(el) {
    const d = getComputedStyle(el).display;
    return d !== 'inline' && d !== 'contents';
  }

  const scrollX0 = scrollX, scrollY0 = scrollY;
  const SKIP = new Set(['SCRIPT', 'STYLE', 'NOSCRIPT', 'TEMPLATE', 'SVG', 'CANVAS']);
  const texts = [], links = [];
  const seen = new Set();

  const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  let node;
  while ((node = walker.nextNode()) && texts.length < 6000) {
    const el = node.parentElement;
    if (!el || SKIP.has(el.tagName.toUpperCase()) || seen.has(el)) continue;
    const len = node.textContent.trim().length;
    if (!len || !visible(el)) continue;
    seen.add(el);
    const cs = getComputedStyle(el);
    const bg = effectiveBg(el);
    if (bg.opacity < 0.05) continue; // invisible
    const fg = blend(parse(cs.color), bg.rgb);
    texts.push({
      tag: el.tagName.toLowerCase(),
      cls: (el.className && el.className.toString ? el.className.toString() : '').slice(0, 60),
      textLen: len,
      sample: node.textContent.trim().slice(0, 30),
      fg, bg: bg.rgb, bgUnknown: bg.unknown, opacity: bg.opacity,
      fontSize: parseFloat(cs.fontSize), fontWeight: parseInt(cs.fontWeight) || 400,
      inLink: !!el.closest('a'),
    });
  }

  for (const a of document.querySelectorAll('a[href]')) {
    if (links.length >= 3000) break;
    if (!visible(a)) continue;
    let block = a.parentElement;
    while (block && !isBlockLike(block)) block = block.parentElement;
    if (!block) continue;
    // Only links inside running text count: the link itself must be inline and unstyled as a button,
    // and the block must hold its own sentence text (not text of nested blocks, not other links).
    const acs = getComputedStyle(a);
    if (acs.display !== 'inline') continue;
    if (a.getAttribute('role') === 'button') continue;
    if (parse(acs.backgroundColor)[3] !== undefined && parse(acs.backgroundColor)[3] > 0.05) continue;
    if (acs.backgroundImage !== 'none') continue;
    if ((parseFloat(acs.borderTopWidth) || 0) > 0 && acs.borderTopStyle !== 'none') continue;
    let around = 0;
    const w = document.createTreeWalker(block, NodeFilter.SHOW_TEXT);
    let n;
    while ((n = w.nextNode())) {
      let e = n.parentElement, ok = true;
      while (e && e !== block) {
        if (e.tagName === 'A' || isBlockLike(e)) { ok = false; break; }
        e = e.parentElement;
      }
      if (ok) around += n.textContent.trim().length;
    }
    if (around < 10) continue; // link is not embedded in running text
    const cs = getComputedStyle(a), bs = getComputedStyle(block);
    const bg = effectiveBg(a);
    links.push({
      linkText: a.textContent.trim().slice(0, 30),
      fg: blend(parse(cs.color), bg.rgb),
      blockFg: blend(parse(bs.color), bg.rgb),
      bg: bg.rgb, bgUnknown: bg.unknown, opacity: bg.opacity,
      decoration: cs.textDecorationLine, blockDecoration: bs.textDecorationLine,
      borderBottomWidth: parseFloat(cs.borderBottomWidth) || 0,
      borderBottomStyle: cs.borderBottomStyle,
      fontWeight: parseInt(cs.fontWeight) || 400, blockFontWeight: parseInt(bs.fontWeight) || 400,
      fontStyle: cs.fontStyle, blockFontStyle: bs.fontStyle,
      surroundingChars: around,
    });
  }
  window.scrollTo(scrollX0, scrollY0);
  return { version: 3, title: document.title, url: location.href, texts, links };
}