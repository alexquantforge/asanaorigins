const fs = require('fs'), path = require('path');
const { JSDOM } = require('jsdom');

// 1) собрать селекторы, у которых display: flex/grid
const css = fs.readFileSync('assets/style.css', 'utf8').replace(/\/\*[\s\S]*?\*\//g, '');
const flexSel = [];
for (const m of css.matchAll(/([^{}]+)\{([^{}]*)\}/g)) {
  const body = m[2];
  if (/display:\s*(inline-)?(flex|grid)/.test(body)) {
    for (const part of m[1].split(',')) {
      const s = part.trim().replace(/::?[a-z-]+(\([^)]*\))?/g, '').trim();
      if (!s || /[\[\]:>+~]/.test(s.replace(/^[.#\w-]+$/,''))) continue;
      flexSel.push(s);
    }
  }
}
const uniq = [...new Set(flexSel)];
console.log('flex/grid селекторов:', uniq.length);

function pages(dir, out = []) {
  for (const e of fs.readdirSync(dir, { withFileTypes: true })) {
    if (e.name === 'node_modules' || e.name.startsWith('.')) continue;
    const p = path.join(dir, e.name);
    if (e.isDirectory()) pages(p, out); else if (e.name === 'index.html') out.push(p);
  }
  return out;
}
const hits = {};
for (const file of pages('.')) {
  const doc = new JSDOM(fs.readFileSync(file, 'utf8')).window.document;
  for (const sel of uniq) {
    let els = [];
    try { els = [...doc.querySelectorAll(sel)]; } catch (e) { continue; }
    for (const el of els) {
      const kids = [...el.childNodes].filter(n => n.nodeType === 1 || (n.nodeType === 3 && n.textContent.trim()));
      const mkKids = kids.filter(n => n.nodeType === 1 && n.classList.contains('mk'));
      const textKids = kids.filter(n => n.nodeType === 3);
      if (!mkKids.length && !(textKids.length > 3)) continue;
      const key = sel + (mkKids.length ? ' | с .mk детьми' : ' | много текстовых детей');
      hits[key] = (hits[key] || 0) + 1;
      if (hits[key] === 1) console.log('×', key, '|', file, '|', el.textContent.replace(/\s+/g,' ').trim().slice(0,60));
    }
  }
}
console.log('\nитог:');
for (const [k, n] of Object.entries(hits)) console.log('  ', n, k);
