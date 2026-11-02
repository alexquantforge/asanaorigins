#!/usr/bin/env node
/* ==========================================================================
   Static pages for «Āсаны: истоки»

   GitHub Pages serves files, not routes: a visitor who asks for
   /asana/padmasana/ gets whatever lies at that path. This script writes those
   files, one per route, so that every pose and every treatise has its own URL,
   its own <title>, a canonical link and a full text in the HTML — the part
   search engines and AI crawlers read without running any JavaScript.

   The pages are produced by the site's own renderer: the script boots
   assets/app.js in jsdom, waits for the route to render, and writes the
   resulting DOM. There is no second renderer to fall out of step with the
   first — the markup of a static page is the markup the browser produces.

   Each page keeps the script, so the site stays interactive: verse tabs,
   themes, the pose filter and the keyboard paging all work as before, and
   internal links point at these same static addresses.

   Run:  npm install      (once; jsdom)
         node tools/prerender.js
   ========================================================================== */
"use strict";

const fs = require("fs");
const path = require("path");
const http = require("http");
const { JSDOM, VirtualConsole, ResourceLoader } = require("jsdom");

const ROOT = path.resolve(__dirname, "..");
/* The canonical address of the site. Change it here and everything follows:
   canonical links, hreflang, Open Graph, the sitemap. */
const SITE = "https://alexquantforge.github.io/asanaorigins";

const TYPES = {
  ".html": "text/html; charset=utf-8",
  ".js": "text/javascript; charset=utf-8",
  ".css": "text/css; charset=utf-8",
  ".json": "application/json; charset=utf-8",
  ".woff2": "font/woff2",
  ".png": "image/png",
  ".svg": "image/svg+xml",
  ".txt": "text/plain; charset=utf-8"
};

const SEO_BEGIN = "<!--seo:begin-->";
const SEO_END = "<!--seo:end-->";

/* ------------------------------------------------------------------ helpers */

const read = (p) => fs.readFileSync(path.join(ROOT, p), "utf8");
const readJSON = (p) => JSON.parse(read(p));
const esc = (s) => String(s == null ? "" : s)
  .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
  .replace(/"/g, "&quot;");

function write(file, text) {
  const full = path.join(ROOT, file);
  fs.mkdirSync(path.dirname(full), { recursive: true });
  fs.writeFileSync(full, text, "utf8");
}

/* A description of the page, built from the page itself: the heading and the
   line under it, cut at a word boundary. Nothing is invented — the words come
   from the text the page already shows. */
function describe(dom) {
  const doc = dom.window.document;
  const pick = (sel) => {
    const el = doc.querySelector(sel);
    return el ? el.textContent.replace(/\s+/g, " ").trim() : "";
  };
  const h1 = pick(".view-inner h1, .page-head h1, .pose-title");
  const gloss = pick(".pose-gloss");
  const meta = pick(".page-meta, .about-meta");
  const treatises = [];
  doc.querySelectorAll(".treatise-head h2").forEach((el) => {
    const name = el.textContent.replace(/\s+/g, " ").trim();
    if (name && !treatises.includes(name)) treatises.push(name);
  });
  let text = [h1, gloss || meta].filter(Boolean).join(" · ");
  if (treatises.length) text += " · " + treatises.join(", ");
  if (text.length > 158) {
    const cut = text.slice(0, 158);
    text = cut.slice(0, cut.lastIndexOf(" ")) + "…";
  }
  return text;
}

/* ------------------------------------------------------------------- routes */

function routesOf(treatises) {
  const pages = [];
  const push = (route, lang, treatiseId) => {
    const prefix = lang === "en" ? "en/" : "";
    let dir;
    if (route === "home") dir = prefix;
    else if (route.startsWith("pose/")) dir = prefix + "asana/" + route.split("/")[1] + "/";
    else {
      const id = route.split("/")[1];
      const section = route.split("/")[2] || "";
      dir = prefix + "treatise/" + id + "/" + (section ? section + "/" : "");
    }
    pages.push({
      route, lang, treatiseId, dir,
      depth: dir.split("/").filter(Boolean).length,
      file: path.join(dir, "index.html")
    });
  };

  for (const lang of ["ru", "en"]) {
    push("home", lang, null);
    const keys = new Map();          // поза -> первый трактат, где она названа
    treatises.forEach((tr) => tr.poses.forEach((p) => {
      if (!keys.has(p.key)) keys.set(p.key, tr.id);
    }));
    keys.forEach((treatiseId, key) => push("pose/" + key, lang, treatiseId));
    treatises.forEach((tr) => {
      push("treatise/" + tr.id, lang, tr.id);
      // Адрес раздела одинаков в обоих языках: различается только префикс /en/.
      const slug = { chapter: "introduction", appendix: "appendix", notes: "notes" };
      // «вступление» — это поле prologue: так раздел назван в данных
      const field = { chapter: "prologue", appendix: "appendix", notes: "notes" };
      for (const view of ["chapter", "appendix", "notes"]) {
        if ((tr[field[view]] && tr[field[view]][lang] || []).length) {
          push("treatise/" + tr.id + "/" + slug[view], lang, tr.id);
        }
      }
    });
  }
  return pages;
}

/* The same page in the other language: hreflang pairs must exist both ways.
   The address of a page does not depend on its language, so the only thing
   that changes is the /en/ prefix. */
function twin(page) {
  return { route: page.route, lang: page.lang === "ru" ? "en" : "ru" };
}

function dirOf(route, lang) {
  const prefix = lang === "en" ? "en/" : "";
  if (route === "home") return prefix;
  if (route.startsWith("pose/")) return prefix + "asana/" + route.split("/")[1] + "/";
  const parts = route.split("/");
  return prefix + "treatise/" + parts[1] + "/" + (parts[2] ? parts[2] + "/" : "");
}

/* ---------------------------------------------------------------- rendering */

class PageLoader extends ResourceLoader {
  /* Only the script and the data are needed to build a page; skipping the
     stylesheets and the fonts keeps a build of a hundred pages quick. */
  fetch(url, options) {
    if (/\.(css|woff2|woff|png|jpe?g|svg|ico)(\?|$)/.test(url)) return null;
    return super.fetch(url, options);
  }
}

const wait = (ms) => new Promise((r) => setTimeout(r, ms));

async function renderPage(page, shell, port) {
  const base = "../".repeat(page.depth);
  const html = shell
    .replace(/<base [^>]*>\n?/g, "")
    .replace(/<html lang="[a-z-]*"/, '<html lang="' + page.lang + '"')
    .replace(/<body[^>]*>/, '<body data-static="1" data-route="' + esc(page.route) +
      '" data-base="' + esc(base) + '" data-treatise="' + esc(page.treatiseId || "") + '">');

  const errors = [];
  const vc = new VirtualConsole();
  vc.on("jsdomError", (e) => errors.push(e.message));
  vc.on("error", (...a) => errors.push(a.join(" ")));

  const origin = "http://127.0.0.1:" + port + "/";
  const dom = new JSDOM(html, {
    url: origin + "index.html",
    runScripts: "dangerously",
    resources: new PageLoader(),
    pretendToBeVisual: true,
    virtualConsole: vc,
    beforeParse(window) {
      window.localStorage.setItem("ao.lang", page.lang);
      window.localStorage.setItem("ao.theme", "light");
      if (page.treatiseId) window.localStorage.setItem("ao.treatise", page.treatiseId);
      window.scrollTo = () => {};
      window.fetch = (u, o) => fetch(new URL(u, origin).href, o);
    }
  });

  const doc = dom.window.document;
  // The shell is the previous build's page, so «#view has text» proves nothing:
  // the page is ready when the app has put the requested route into it.
  //
  // app.js marks the document with the route it has just drawn (data-rendered),
  // so waiting is exact: nothing is written until the requested page is there.
  let ok = false;
  for (let i = 0; i < 400; i += 1) {
    await wait(25);
    if (doc.documentElement.dataset.rendered === page.route && doc.title &&
        doc.querySelector("#view").textContent.trim().length > 60) { ok = true; break; }
    if (errors.length) break;
  }
  if (!ok) {
    dom.window.close();
    throw new Error(page.route + " (" + page.lang + "): страница не отрисовалась — " +
      (errors[0] || "пусто"));
  }

  const description = describe(dom);
  const title = doc.title;
  const h1 = (doc.querySelector(".view-inner h1, .page-head h1, .pose-title") || {}).textContent || "";
  const serialized = dom.serialize();
  dom.window.close();
  return { html: serialized, title, description, h1: h1.replace(/\s+/g, " ").trim(), errors };
}

/* ---------------------------------------------------------------- the page */

function seoBlock(page, title, description, h1, site, treatiseTitle) {
  const url = SITE + "/" + page.dir;
  const alt = twin(page);
  const altUrl = alt ? SITE + "/" + dirOf(alt.route, alt.lang) : null;
  const crumbs = [{ name: site, url: SITE + "/" }];
  if (page.route.startsWith("pose/")) {
    crumbs.push({ name: h1 || title, url });
  } else if (page.route.startsWith("treatise/")) {
    crumbs.push({ name: treatiseTitle, url: SITE + "/" + dirOf("treatise/" + page.route.split("/")[1], page.lang) });
    if (page.route.split("/")[2]) crumbs.push({ name: h1 || title, url });
  }

  const graph = [
    {
      "@type": "WebSite",
      "@id": SITE + "/#website",
      url: SITE + "/",
      name: site,
      inLanguage: ["ru", "en"]
    },
    {
      "@type": "WebPage",
      "@id": url + "#webpage",
      url,
      name: title,
      description,
      inLanguage: page.lang,
      isPartOf: { "@id": SITE + "/#website" }
    },
    {
      "@type": "BreadcrumbList",
      itemListElement: crumbs.map((c, i) => ({
        "@type": "ListItem", position: i + 1, name: c.name, item: c.url
      }))
    }
  ];

  const lines = [
    SEO_BEGIN,
    '<link rel="canonical" href="' + esc(url) + '">',
    '<meta name="robots" content="index,follow">'
  ];
  for (const l of ["ru", "en"]) {
    const target = (l === page.lang) ? url : altUrl;
    if (target) lines.push('<link rel="alternate" hreflang="' + l + '" href="' + esc(target) + '">');
  }
  const ruUrl = SITE + "/" + dirOf(page.route, "ru");
  lines.push('<link rel="alternate" hreflang="x-default" href="' + esc(ruUrl) + '">');
  lines.push(
    '<meta property="og:type" content="website">',
    '<meta property="og:site_name" content="' + esc(site) + '">',
    '<meta property="og:title" content="' + esc(title) + '">',
    '<meta property="og:description" content="' + esc(description) + '">',
    '<meta property="og:url" content="' + esc(url) + '">',
    '<meta property="og:locale" content="' + (page.lang === "ru" ? "ru_RU" : "en_GB") + '">',
    '<meta name="twitter:card" content="summary">',
    '<script type="application/ld+json">' +
      JSON.stringify({ "@context": "https://schema.org", "@graph": graph }) +
      "</script>",
    SEO_END
  );
  return lines.join("\n");
}

function withBase(html, depth) {
  if (!depth) return html;
  const base = "../".repeat(depth);
  return html
    .replace(/(href|src)="assets\//g, '$1="' + base + 'assets/')
    .replace(/(href|src)="sources\//g, '$1="' + base + 'sources/')
    .replace(/(href|src)="data\//g, '$1="' + base + 'data/');
}

function applyHead(html, page, title, description, h1, site, treatiseTitle) {
  let out = withBase(html, page.depth);
  out = out.replace(/ data-rendered="[^"]*"/, "");
  // a rebuilt page must not keep the previous build's canonical block
  out = out.replace(new RegExp(SEO_BEGIN + "[\\s\\S]*?" + SEO_END + "\\n?"), "");
  out = out.replace(/<title>[\s\S]*?<\/title>/, "<title>" + esc(title) + "</title>");
  out = out.replace(/<meta name="description"[^>]*>/,
    '<meta name="description" content="' + esc(description) + '">');
  out = out.replace(/<\/head>/, seoBlock(page, title, description, h1, site, treatiseTitle) + "\n</head>");
  if (page.lang === "en") out = out.replace(/<html lang="ru"/, '<html lang="en"');
  return out;
}

/* -------------------------------------------------------------------- build */

async function main() {
  const argv = process.argv.slice(2);
  const checkOnly = argv.includes("--check");

  const index = readJSON("data/treatises.json");
  const treatises = index.treatises.map((meta) => {
    const data = readJSON(meta.file.replace(/^\.?\//, ""));
    return Object.assign({}, data, meta, {
      poses: data.poses || [],
      chapter: data.chapter || meta.chapter
    });
  });
  const site = (index.site && index.site.title && index.site.title.ru) || "Āсаны: истоки";
  const pages = routesOf(treatises);

  const shell = read("index.html");
  const server = http.createServer((req, res) => {
    const clean = decodeURIComponent(req.url.split("?")[0]);
    const file = path.join(ROOT, clean);
    fs.readFile(file, (err, buf) => {
      if (err) { res.writeHead(404); res.end("not found"); return; }
      res.writeHead(200, { "content-type": TYPES[path.extname(file)] || "application/octet-stream" });
      res.end(buf);
    });
  });
  await new Promise((r) => server.listen(0, "127.0.0.1", r));
  const port = server.address().port;

  const written = [];
  try {
    for (const page of pages) {
      const tr = treatises.find((t) => t.id === page.treatiseId);
      const treatiseTitle = tr ? tr.title[page.lang] || tr.title.ru : site;
      const built = await renderPage(page, shell, port);
      const html = applyHead(built.html, page, built.title, built.description,
                             built.h1, site, treatiseTitle);
      written.push({ page, title: built.title, description: built.description, html });
      if (!checkOnly) process.stdout.write("  " + page.lang + "  " + page.file + "\n");
    }
  } finally {
    server.close();
  }

  if (checkOnly) {
    let bad = 0;
    for (const { page, html } of written) {
      const onDisk = fs.existsSync(path.join(ROOT, page.file)) ? read(page.file) : "";
      if (onDisk !== html) { console.log("  устарело: " + page.file); bad += 1; }
    }
    console.log(bad ? "  страниц устарело: " + bad : "  все страницы совпадают с данными");
    return;
  }

  for (const { page, html } of written) write(page.file, html);

  /* the sitemap and robots.txt are written from the same list, so a page can
     never be missing from one and present in the other */
  const today = new Date().toISOString().slice(0, 10);
  const byRoute = new Map();
  for (const { page } of written) {
    const key = page.route;
    if (!byRoute.has(key)) byRoute.set(key, {});
    byRoute.get(key)[page.lang] = SITE + "/" + page.dir;
  }
  const urls = written.map(({ page }) => {
    const pair = byRoute.get(page.route) || {};
    const links = Object.entries(pair)
      .map(([lang, href]) => '    <xhtml:link rel="alternate" hreflang="' + lang +
        '" href="' + esc(href) + '"/>')
      .join("\n");
    return "  <url>\n    <loc>" + esc(SITE + "/" + page.dir) + "</loc>\n" +
      "    <lastmod>" + today + "</lastmod>\n" + links + "\n  </url>";
  }).join("\n");

  write("sitemap.xml",
    '<?xml version="1.0" encoding="UTF-8"?>\n' +
    '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"\n' +
    '        xmlns:xhtml="http://www.w3.org/1999/xhtml">\n' + urls + "\n</urlset>\n");

  write("robots.txt",
    "User-agent: *\nAllow: /\n\n" +
    "# поисковые системы и ИИ-краулеры читают те же страницы, что и люди\n" +
    "Sitemap: " + SITE + "/sitemap.xml\n");

  console.log("\n  страниц: " + written.length + " · sitemap.xml · robots.txt");
}

main().catch((e) => {
  console.error("\n  ошибка: " + e.message + "\n");
  process.exit(1);
});
