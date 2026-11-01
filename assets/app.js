/* ==========================================================================
   Āsana: Origins
   Static reader for asana passages. All textual content comes from
   data/*.json, which is generated verbatim from the source PDFs.
   ========================================================================== */

(function () {
  "use strict";

  const I18N = {
    ru: {
      skip: "К содержанию",
      treatise: "Трактат",
      asanas: "Āсаны",
      chapter: "Глава XXXI",
      sections: "Разделы главы",
      filter: "Найти āсану",
      asana: "Āсана",
      verse: "стих",
      about: "О трактате",
      chapterLink: "Вступление и перечень āсан",
      appendix: "Приложение",
      notes: "Примечания к чтениям",
      copied: "Текст скопирован",
      copy: "Копировать",
      prev: "Предыдущая",
      next: "Следующая",
      notFound: "Такой āсаны нет в этом трактате.",
      loading: "Загрузка…",
      error: "Не удалось загрузить данные. Откройте сайт через локальный сервер.",
      source: "Источник",
      pdf: "PDF источника",
      translation: "Перевод",
      edition: "Издание",
      chapters: "Разделы главы",
      treatiseAbout: "О трактате",
      toAbout: "О трактате",
      noMatch: "Ничего не найдено",
      countOf: "из",
      datingTitle: "Датировка текста",
      datingOpen: "Читать датировку полностью",
      datingClose: "Свернуть",
      datingSource: "Источник датировки",
      build: "версия"
    },
    en: {
      skip: "Skip to content",
      treatise: "Treatise",
      asanas: "Āsanas",
      chapter: "Chapter XXXI",
      sections: "Chapter sections",
      filter: "Find a pose",
      asana: "Āsana",
      verse: "verse",
      about: "About the treatise",
      chapterLink: "Opening and List of Āsanas",
      appendix: "Appendix",
      notes: "Notes on Readings",
      copied: "Text copied",
      copy: "Copy",
      prev: "Previous",
      next: "Next",
      notFound: "This pose is not in this treatise.",
      loading: "Loading…",
      error: "Could not load the data. Serve the site from a local web server.",
      source: "Source",
      pdf: "Source PDF",
      translation: "Translation",
      edition: "Edition",
      chapters: "Sections of the chapter",
      treatiseAbout: "About the treatise",
      toAbout: "About",
      noMatch: "Nothing found",
      countOf: "of",
      datingTitle: "Dating of the text",
      datingOpen: "Read the full dating",
      datingClose: "Collapse",
      datingSource: "Source of the dating",
      build: "build"
    }
  };

  const BUILD = "2026-11-01.9";
  const V = "?v=" + BUILD;

  const state = {
    lang: localStorage.getItem("ao.lang") === "en" ? "en" : "ru",
    theme: localStorage.getItem("ao.theme") || "light",
    treatiseId: localStorage.getItem("ao.treatise") || null,
    filter: ""
  };

  let site = null;
  let treatises = [];
  let activeTreatise = null;
  let lastPoseKey = null;

  const $ = (sel, root) => (root || document).querySelector(sel);
  const $$ = (sel, root) => Array.from((root || document).querySelectorAll(sel));
  const t = (key) => I18N[state.lang][key] || key;
  const tx = (obj) =>
    typeof obj === "string" ? obj : (obj && (obj[state.lang] || obj.ru)) || "";

  function esc(s) {
    return String(s == null ? "" : s)
      .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }


  /* ------------------------------------------------------- combining marks

     Cyrillic transliteration needs marks that most display fonts do not have
     (м̣, р̣, н̇, н̃, ш́). The browser would then take the whole letter from a
     fallback font — it looked heavier than its neighbours — and letter-spacing
     pushed the mark sideways. The mark is therefore drawn by CSS, while the
     real combining character stays in the text at zero size, so copying,
     searching and screen readers still get the true letter.
  */

  const MARK_CLASS = {
    "\u0323": "m-b",   // dot below
    "\u0307": "m-a",   // dot above
    "\u0301": "m-ac",  // acute
    "\u0303": "m-t",   // tilde
    "\u0304": "m-mac"  // macron
  };

  function marksInText(text) {
    let out = "";
    let i = 0;
    while (i < text.length) {
      const base = text[i];
      const marks = [];
      let j = i + 1;
      while (j < text.length && MARK_CLASS[text[j]]) {
        marks.push(text[j]);
        j += 1;
      }
      if (marks.length) {
        out += '<span class="mk ' + marks.map((m) => MARK_CLASS[m]).join(" ") + '">' +
          base + '<span class="cmb">' + marks.join("") + "</span></span>";
        i = j;
      } else {
        out += base;
        i += 1;
      }
    }
    return out;
  }

  function applyMarks(html) {
    return String(html)
      .split(/(<[^>]*>)/)
      .map((part) => (!part || part[0] === "<" ? part : marksInText(part)))
      .join("");
  }

  /* ------------------------------------------------------------------ load */

  async function boot() {
    document.documentElement.setAttribute("data-theme", state.theme);
    applyStaticText();
    $("#view").innerHTML = '<p class="empty">' + esc(t("loading")) + "</p>";

    let index;
    try {
      index = await fetch("data/treatises.json" + V).then((r) => {
        if (!r.ok) throw new Error(r.status);
        return r.json();
      });
    } catch (e) {
      $("#view").innerHTML = '<p class="empty">' + esc(t("error")) + "</p>";
      return;
    }

    site = index.site || null;
    const loaded = await Promise.all(
      index.treatises.map(async (meta) => {
        const data = await fetch(meta.file + V).then((r) => r.json());
        // registry metadata (short title, edition, PDF) wins over the document's
        // own long title; the long title stays available as docTitle
        return Object.assign({}, data, meta, {
          chapter: data.chapter || meta.chapter,
          poses: data.poses || [],
          about: data.about || { ru: [], en: [] },
          prologue: data.prologue || { ru: [], en: [] },
          appendix: data.appendix || { ru: [], en: [] },
          notes: data.notes || { ru: [], en: [] },
          asanasTitle: data.asanasTitle || null,
          docTitle: data.title || null
        });
      })
    );
    treatises = loaded;

    if (!state.treatiseId || !treatises.some((x) => x.id === state.treatiseId)) {
      state.treatiseId = treatises[0] ? treatises[0].id : null;
    }
    activeTreatise = treatises.find((x) => x.id === state.treatiseId) || null;

    if (site) {
      if (site.title && site.title[state.lang]) {
        $("[data-site-title]").textContent = tx(site.title);
      }
      if (site.tagline) {
        $("[data-site-tagline]").textContent = tx(site.tagline);
      }
    }

    updateBrand();
    buildTreatiseSelect();
    buildChapterNav();
    buildPoseList();
    wireEvents();

    if (!location.hash) {
      const first = activeTreatise && activeTreatise.poses[0];
      location.replace(first ? "#/pose/" + first.key : "#/about");
    } else {
      render();
    }
  }

  /* ----------------------------------------------------------- static text */

  function applyStaticText() {
    document.documentElement.lang = state.lang;
    $$("[data-i18n]").forEach((el) => {
      el.textContent = t(el.getAttribute("data-i18n"));
    });
    $$("[data-i18n-placeholder]").forEach((el) => {
      el.setAttribute("placeholder", t(el.getAttribute("data-i18n-placeholder")));
    });
    $$(".lang-switch button").forEach((b) => {
      const on = b.dataset.lang === state.lang;
      b.classList.toggle("is-active", on);
      b.setAttribute("aria-pressed", on ? "true" : "false");
    });
    const menu = $("#menu-btn");
    if (menu) menu.setAttribute("aria-label", state.lang === "ru" ? "Меню" : "Menu");
    updateThemeLabel();
  }

  function updateThemeLabel() {
    const btn = $("#theme-btn");
    if (!btn) return;
    const label = state.theme === "dark"
      ? (state.lang === "ru" ? "Светлая тема" : "Light theme")
      : (state.lang === "ru" ? "Тёмная тема" : "Dark theme");
    btn.setAttribute("aria-label", label);
    btn.setAttribute("title", label);
  }

  /* -------------------------------------------------------------- sidebar */

  function buildTreatiseSelect() {
    const sel = $("#treatise-select");
    sel.innerHTML = treatises
      .map((tr) => '<option value="' + esc(tr.id) + '">' + esc(tx(tr.title)) + "</option>")
      .join("");
    sel.value = state.treatiseId || "";
    updateTreatiseNote();
  }

  function updateBrand() {
    const first = activeTreatise && activeTreatise.poses[0];
    const brand = $(".brand");
    if (brand) brand.setAttribute("href", first ? "#/pose/" + first.key : "#/about");
  }

  function updateTreatiseNote() {
    const note = $("#treatise-note");
    if (!activeTreatise) {
      note.textContent = "";
      return;
    }
    const parts = [tx(activeTreatise.subtitle), tx(activeTreatise.tradition)];
    note.innerHTML = applyMarks(esc(parts.filter(Boolean).join(" · ")));

    const foot = $("#side-source");
    foot.innerHTML = applyMarks(
      esc(tx(activeTreatise.edition)) +
        (activeTreatise.pdf
          ? ' · <a href="' + esc(encodeURI(activeTreatise.pdf[state.lang] || activeTreatise.pdf.ru)) +
            '" target="_blank" rel="noopener">' + esc(t("pdf")) + "</a>"
          : ""));
  }

  function chapterTitle() {
    if (!activeTreatise) return t("chapterLink");
    const own = tx(activeTreatise.asanasTitle);
    if (own) return own;
    const prologue = activeTreatise.prologue[state.lang] || [];
    const lead = prologue.find((s) => s.type === "subhead");
    return (lead && lead.label) || t("chapterLink");
  }

  function chapterNavLabel() {
    const prologue = (activeTreatise && activeTreatise.prologue[state.lang]) || [];
    const lead = prologue.find((s) => s.type === "subhead");
    return (lead && lead.label) || t("chapterLink");
  }

  function buildChapterNav() {
    if (!activeTreatise) return;
    const appendix = activeTreatise.appendix[state.lang] || [];
    const notes = activeTreatise.notes[state.lang] || [];
    const appendixLabel =
      (appendix.find((s) => s.type === "subhead") || {}).label || t("appendix");
    const notesTitle = (activeTreatise.notesTitle && activeTreatise.notesTitle[state.lang]) || t("notes");

    // a treatise without a chapter page of its own gets no link to one
    const prologue = activeTreatise.prologue[state.lang] || [];
    const items = prologue.length ? [["#/chapter", chapterNavLabel()]] : [];
    if (appendix.length) items.push(["#/appendix", appendixLabel.split(".")[0]]);
    if (notes.length) items.push(["#/notes", notesTitle]);
    items.push(["#/about", t("treatiseAbout")]);
    $("#chapter-nav").innerHTML = applyMarks(
      items
        .map(([href, label]) => '<li><a href="' + href + '"><span>' + esc(label) +
          "</span></a></li>")
        .join(""));
  }

  function poseGroups() {
    const map = new Map();
    treatises.forEach((tr) => {
      (tr.poses || []).forEach((pose) => {
        if (!map.has(pose.key)) map.set(pose.key, []);
        map.get(pose.key).push({ treatise: tr, pose });
      });
    });
    return map;
  }

  function poseListData() {
    const map = poseGroups();
    const order = [];
    const push = (list) =>
      (list || []).forEach((p) => {
        if (order.indexOf(p.key) < 0) order.push(p.key);
      });
    push(activeTreatise && activeTreatise.poses);
    treatises.forEach((tr) => push(tr.poses));
    return order.map((key) => {
      const group = map.get(key) || [];
      const pick = group.find((g) => g.treatise === activeTreatise) || group[0] || {};
      const pose = pick.pose || {};
      return {
        key: key,
        number: pose.number,
        name: tx(pose.name),
        gloss: tx(pose.gloss),
        iast: pose.iast,
        inTreatise: group.some((g) => g.treatise === activeTreatise)
      };
    });
  }

  function buildPoseList() {
    const list = $("#pose-list");
    const data = poseListData();
    const q = state.filter.trim().toLowerCase();
    const shown = q
      ? data.filter(
          (p) =>
            p.name.toLowerCase().includes(q) ||
            (p.gloss || "").toLowerCase().includes(q) ||
            (p.iast || "").toLowerCase().includes(q) ||
            String(p.number) === q
        )
      : data;

    list.innerHTML = applyMarks(shown.length
      ? shown
          .map((p) => {
            const active = isCurrent("#/pose/" + p.key);
            return (
              '<li' + (p.inTreatise === false ? ' class="is-other"' : "") +
              '><a href="#/pose/' + p.key + '"' +
              (active ? ' aria-current="page"' : "") + ">" +
              '<span class="pose-num">' + String(p.number).padStart(2, "0") + "</span>" +
              '<span class="pose-name"><span class="ru">' + esc(p.name) + "</span>" +
              (p.iast ? '<span class="iast">' + esc(p.iast) + "</span>" : "") +
              "</span></a></li>"
            );
          })
          .join("")
      : '<li><p class="side-note">' + esc(t("noMatch")) + "</p></li>");

    const count = $("#pose-count");
    if (count) count.textContent = shown.length + " / " + data.length;
  }

  function isCurrent(href) {
    return location.hash === href;
  }

  function markCurrent() {
    $$(".pose-list a, #chapter-nav a").forEach((a) => {
      if (a.getAttribute("href") === location.hash) a.setAttribute("aria-current", "page");
      else a.removeAttribute("aria-current");
    });
  }

  /* --------------------------------------------------------------- routing */

  function parseRoute() {
    const hash = location.hash || "#/";
    const parts = hash.replace(/^#\/?/, "").split("/");
    if (parts[0] === "pose" && parts[1]) return { view: "pose", key: parts[1] };
    if (["chapter", "appendix", "notes", "about"].includes(parts[0])) {
      return { view: parts[0] };
    }
    return { view: "pose", key: activeTreatise && activeTreatise.poses[0] ? activeTreatise.poses[0].key : null };
  }

  function render() {
    const route = parseRoute();
    const view = $("#view");
    view.innerHTML = "";

    if (!activeTreatise) {
      view.innerHTML = '<p class="empty">' + esc(t("error")) + "</p>";
      return;
    }

    if (route.view === "chapter" && !(activeTreatise.prologue[state.lang] || []).length) {
      route.view = "about";
    }
    if (route.view === "appendix" && !(activeTreatise.appendix[state.lang] || []).length) {
      route.view = "about";
    }
    if (route.view === "notes" && !(activeTreatise.notes[state.lang] || []).length) {
      route.view = "about";
    }

    let html = "";
    if (route.view === "pose") html = renderPose(route.key);
    else if (route.view === "chapter") html = renderChapter();
    else if (route.view === "appendix") html = renderAppendix();
    else if (route.view === "notes") html = renderNotes();
    else if (route.view === "about") html = renderAbout();

    view.innerHTML = applyMarks(html);
    view.style.animation = "none";
    void view.offsetWidth;
    view.style.animation = "";

    markCurrent();
    wireDating(view);
    wireVerseTabs(view);
    document.title = pageTitle(route);
    window.scrollTo({ top: 0, behavior: "auto" });
  }

  function pageTitle(route) {
    const base = site && site.title ? tx(site.title) : "Āsana: Origins";
    if (route.view === "pose") {
      const found = activeTreatise.poses.find((p) => p.key === route.key);
      return found ? tx(found.name) + " — " + base : base;
    }
    if (route.view === "about") return t("about") + " — " + base;
    if (route.view === "chapter") return t("chapterLink") + " — " + base;
    if (route.view === "appendix") return t("appendix") + " — " + base;
    if (route.view === "notes") return t("notes") + " — " + base;
    return base;
  }

  /* ------------------------------------------------------------ rendering */

  function renderPose(key) {
    const occurrences = [];
    treatises.forEach((tr) => {
      const pose = tr.poses.find((p) => p.key === key);
      if (pose) occurrences.push({ treatise: tr, pose });
    });
    // the treatise chosen in the sidebar is read first
    occurrences.sort((a, b) => (a.treatise === activeTreatise ? -1 : 0) -
      (b.treatise === activeTreatise ? -1 : 0));

    if (!occurrences.length) {
      return '<p class="empty">' + esc(t("notFound")) + "</p>";
    }

    const own = occurrences.find((o) => o.treatise === activeTreatise);
    const primaryOcc = own || occurrences[0];
    const primary = primaryOcc.pose;
    const multi = occurrences.length > 1;
    lastPoseKey = key;
    const index = activeTreatise.poses.findIndex((p) => p.key === key);

    let html = "";
    html +=
      '<article class="view-inner">' +
      '<header class="pose-head">' +
      '<p class="eyebrow"><span class="num">' + esc(t("asana")) + " " +
      String(primary.number).padStart(2, "0") + "</span>" +
      '<span class="dot"></span><span>' + esc(tx(primary.verses)) + "</span></p>" +
      '<h1 class="pose-title">' + esc(tx(primary.name)) + "</h1>" +
      '<p class="pose-gloss">' + esc(tx(primary.gloss)) + "</p>" +
      '<p class="pose-iast">' + esc(primary.iast || "") + "</p>" +
      '<div class="pose-rule"></div>' +
      "</header>";

    // Every treatise reads as one continuous sheet: the source's name and
    // reference come first, then its dating, then the text itself.
    occurrences.forEach((occ) => {
      const tr = occ.treatise;
      const pose = occ.pose;
      html += '<section class="treatise-block">';
      html += '<div class="treatise-head">';
      html += "<h2>" + esc(tx(tr.title)) + "</h2>";
      html += '<span class="ref">' +
        esc(tx(tr.chapterWord) || (state.lang === "ru" ? "глава" : "chapter")) +
        (tr.chapter ? " " + esc(tr.chapter) : "") + "</span>";
      if (multi) {
        html += '<a class="link" href="#/about">' + esc(t("toAbout")) + "</a>";
      }
      html += "</div>";
      html += renderDating(tr);
      html += renderSections(pose.text[state.lang] || pose.text.ru);
      html += "</section>";
    });

    html += "</article>";
    html += renderPager(index);
    html += renderColophon((own || occurrences[0]).treatise);
    return html;
  }


  /* ------------------------------------------- rich blocks (about, dating) */

  function blockBody(b) {
    if (b.html != null) return b.html;
    return esc(b.text || "");
  }

  function renderTable(b) {
    const rows = b.rows || [];
    if (!rows.length) return "";
    let html = '<div class="doc-table-wrap"><table class="doc-table">';
    let body = rows;
    if (rows.length > 1) {
      html += "<thead><tr>" +
        rows[0].map((c) => "<th>" + esc(c) + "</th>").join("") + "</tr></thead>";
      body = rows.slice(1);
    }
    // On a phone the table becomes a stack of cards; each cell carries the
    // name of its column in data-label, so nothing has to be guessed.
    const heads = rows.length > 1 ? rows[0] : [];
    html += "<tbody>" +
      body.map((r) => "<tr>" + r.map((c, i) =>
        "<td" + (heads[i] ? ' data-label="' + esc(heads[i]) + '"' : "") + ">" +
        esc(c) + "</td>").join("") + "</tr>").join("") +
      "</tbody></table></div>";
    return html;
  }

  function renderList(b) {
    const items = b.items || [];
    const cls = items.some((it) => it && typeof it === "object") ? "doc-list" : "source-list";
    const tag = b.ordered ? "ol" : "ul";
    const start = b.ordered && b.start && b.start > 1 ? ' start="' + esc(b.start) + '"' : "";
    return "<" + tag + ' class="' + cls + '"' + start + ">" +
      (b.items || []).map((item) => {
        if (item && typeof item === "object") {
          const level = item.level > 1 ? " lvl" + item.level : "";
          const code = item.code
            ? '<pre class="doc-code"><code>' + esc(item.code) + "</code></pre>"
            : "";
          return '<li class="list-item' + level + '">' + blockBody(item) + code + "</li>";
        }
        return "<li>" + esc(item) + "</li>";
      }).join("") + "</" + tag + ">";
  }

  function renderQuote(b) {
    return '<blockquote class="doc-quote">' +
      (b.paragraphs || []).map((p) => "<p>" + p + "</p>").join("") + "</blockquote>";
  }

  function renderBlocks(blocks) {
    return (blocks || []).map((b) => {
      switch (b.type) {
        case "title":
          return '<h1 class="about-title">' + blockBody(b) + "</h1>";
        case "byline":
          return '<p class="about-byline">' + blockBody(b) + "</p>";
        case "h2":
          return '<h2 class="about-h2">' + blockBody(b) + "</h2>";
        case "h3":
          return '<h3 class="about-h3">' + blockBody(b) + "</h3>";
        case "h4":
          return '<h4 class="about-h4">' + blockBody(b) + "</h4>";
        case "subhead":
          return '<h2 class="subhead">' + esc(b.label) + "</h2>";
        case "list":
          return renderList(b);
        case "quote":
          return renderQuote(b);
        case "table":
          return renderTable(b);
        case "deva":
          return '<p class="about-deva" lang="sa">' +
            (b.lines || []).map((line) => "<span>" + esc(line) + "</span>").join("") + "</p>";
        case "code":
          return '<pre class="doc-code"><code>' + esc(b.text || "") + "</code></pre>";
        case "p":
          return '<p class="about-p">' + blockBody(b) + "</p>";
        default:
          return '<p class="about-p">' + blockBody(b) + "</p>";
      }
    }).join("");
  }

  function renderDating(tr) {
    const summary = tr.datingSummary;
    const full = tr.dating && tr.dating[state.lang];
    if (!summary && !(full && full.blocks && full.blocks.length)) return "";

    let html = '<section class="dating" aria-label="' + esc(t("datingTitle")) + '">';
    html += '<p class="dating-kicker"><span>' + esc(t("datingTitle")) + "</span></p>";

    if (summary) {
      if (summary.note) {
        html += '<p class="dating-note">' + esc(tx(summary.note)) + "</p>";
      }
      html += '<ul class="dating-rows">';
      (summary.items || []).forEach((item) => {
        html += "<li>";
        html += '<span class="dating-who">' + esc(tx(item.who)) + "</span>";
        html += '<span class="dating-when">' + esc(tx(item.when));
        if (item.whenNote) {
          html += '<span class="dating-when-note">' + esc(tx(item.whenNote)) + "</span>";
        }
        html += "</span>";
        const workLabel = summary.label ? tx(summary.label) : t("datingSource");
        html += '<span class="dating-work"><span class="dating-work-label">' +
          esc(workLabel) + "</span>" + esc(tx(item.work)) + "</span>";
        html += "</li>";
      });
      html += "</ul>";
    }

    if (full && full.blocks && full.blocks.length) {
      html += '<details class="dating-more">';
      html += '<summary><span class="dating-toggle-label">' + esc(t("datingOpen")) +
        "</span></summary>";
      html += '<div class="dating-full">';
      html += '<h3 class="dating-full-title">' + esc(full.title) + "</h3>";
      html += renderBlocks(full.blocks);
      html += '<p class="dating-full-link"><a href="#/about">' +
        esc(t("treatiseAbout")) + " →</a></p>";
      html += "</div></details>";
    }

    html += "</section>";
    return html;
  }

  function renderSections(sections) {
    let html = "";
    let i = 0;
    while (i < sections.length) {
      const sec = sections[i];
      if (sec.type === "verse_card") {
        html += '<div class="verse-card">';
        if (sec.verses) {
          html += '<p class="verse-card-num"><span>' + esc(sec.verses) + "</span></p>";
        }
        html += renderVerses(sec.sections || []) + "</div>";
        i += 1;
        continue;
      }
      if (sec.type === "verse") {
        const run = [];
        while (i < sections.length && sections[i].type === "verse") {
          run.push(sections[i]);
          i += 1;
        }
        html += renderVerses(run);
        continue;
      }
      if (sec.type === "words") {
        html += '<section class="section">';
        if (sec.label) html += '<h3 class="section-label"><span>' + esc(sec.label) + "</span></h3>";
        const groups = sec.groups || (sec.pairs ? [sec.pairs] : []);
        if (!groups.length) {
          (sec.paragraphs || []).forEach((p) => {
            html += '<p class="about-p">' + esc(p) + "</p>";
          });
        }
        groups.forEach((pairs) => {
          html += '<dl class="words">';
          pairs.forEach((pair) => {
            const term = pair[0] || "";
            const gloss = pair[1] || "";
            if (!term) {
              html += '<dd class="wide">' + esc(gloss) + "</dd>";
            } else {
              html += "<dt>" + esc(term) + "</dt><dd>" + esc(gloss) + "</dd>";
            }
          });
          html += "</dl>";
        });
        html += "</section>";
        i += 1;
        continue;
      }
      if (sec.type === "note") {
        html += '<aside class="note">';
        (sec.paragraphs || []).forEach((p) => {
          html += "<p>" + esc(p) + "</p>";
        });
        html += "</aside>";
        i += 1;
        continue;
      }
      if (sec.type === "prose") {
        html += '<section class="section prose-' + esc(sec.key || "") + '">';
        if (sec.label) html += '<h3 class="section-label"><span>' + esc(sec.label) + "</span></h3>";
        (sec.paragraphs || []).forEach((p) => {
          html += "<p>" + esc(p) + "</p>";
        });
        html += "</section>";
        i += 1;
        continue;
      }
      if (sec.type === "subhead") {
        html += '<h2 class="subhead">' + esc(sec.label) + "</h2>";
        i += 1;
        continue;
      }
      if (sec.type === "quote") {
        html += renderQuote(sec);
        i += 1;
        continue;
      }
      if (sec.html != null) {
        // a block of the reference (§8 code sample, a Devanāgarī quotation)
        html += renderBlocks([sec]);
        i += 1;
        continue;
      }
      // plain paragraphs
      (sec.paragraphs || []).forEach((p) => {
        html += '<p class="about-p">' + esc(p) + "</p>";
      });
      i += 1;
    }
    return html;
  }

  function renderVerses(run) {
    let tabs = "";
    let panels = "";
    run.forEach((sec, idx) => {
      const id = "verse-" + Math.random().toString(36).slice(2, 8) + "-" + idx;
      const selected = idx === 0;
      tabs +=
        '<button type="button" role="tab" id="tab-' + id + '" aria-controls="' + id +
        '" aria-selected="' + (selected ? "true" : "false") + '" data-tab="' + id + '">' +
        esc(sec.label) + "</button>";
      panels +=
        '<div class="verse-body" id="' + id + '" role="tabpanel" aria-labelledby="tab-' + id + '"' +
        (selected ? "" : " hidden") + ">" +
        '<p class="verse-lines ' + esc(sec.key) + '" lang="' +
        (sec.key === "deva" ? "sa" : sec.key === "cyr" ? "ru" : "sa-Latn") + '">' +
        sec.lines.map((line) => "<span>" + esc(line) + "</span>").join("") +
        "</p></div>";
    });

    return (
      '<div class="verses" data-verses>' +
      '<div class="verse-tabs">' +
      '<div class="verse-tablist" role="tablist">' + tabs + "</div>" +
      '<button type="button" class="verse-copy" data-copy>' +
      '<svg viewBox="0 0 24 24" aria-hidden="true"><rect x="9" y="9" width="11" height="11" rx="2"/>' +
      '<path d="M15 6.5V5a2 2 0 0 0-2-2H5a2 2 0 0 0-2 2v8a2 2 0 0 0 2 2h1.5"/></svg>' +
      esc(t("copy")) + "</button></div>" +
      panels +
      "</div>"
    );
  }

  function renderPager(index) {
    const poses = poseListData();
    if (!poses.length) return "";
    const here = index >= 0 ? index : poses.findIndex((p) => p.key === (lastPoseKey || ""));
    const prev = poses[here - 1];
    const next = poses[here + 1];
    let html = '<nav class="pager" aria-label="' + esc(t("asanas")) + '">';
    html += prev
      ? '<a class="prev" href="#/pose/' + prev.key + '"><span class="dir">' +
        esc(t("prev")) + '</span><span class="to">' + esc(prev.name) + "</span></a>"
      : "<span></span>";
    html += next
      ? '<a class="next" href="#/pose/' + next.key + '"><span class="dir">' +
        esc(t("next")) + '</span><span class="to">' + esc(next.name) + "</span></a>"
      : "";
    html += "</nav>";
    return html;
  }

  function renderColophon(tr) {
    const pdfHref = tr.pdf ? encodeURI(tr.pdf[state.lang] || tr.pdf.ru) : null;
    let html = '<footer class="colophon">';
    html += "<p><strong>" + esc(tx(tr.title)) + "</strong>" +
      (tr.chapter ? " · " + esc(tx(tr.chapterWord) || (state.lang === "ru" ? "глава" : "chapter")) +
        " " + esc(tr.chapter) : "") + "</p>";
    if (tr.edition) html += "<p>" + esc(t("edition")) + ": " + esc(tx(tr.edition)) + "</p>";
    if (tr.translator) html += "<p>" + esc(tx(tr.translator)) + "</p>";
    if (pdfHref) {
      html += '<p><a href="' + esc(pdfHref) + '" target="_blank" rel="noopener">' +
        esc(t("pdf")) + " ↗</a></p>";
    }
    html += '<p class="colophon-build">' + esc(t("build")) + " " + esc(BUILD) + "</p>";
    html += "</footer>";
    return html;
  }

  /* ------------------------------------------------------- chapter & notes */

  function pageHead(title, meta) {
    let html = '<header class="page-head"><h1>' + esc(title) + "</h1>";
    if (meta) html += '<p class="page-meta">' + meta + "</p>";
    html += "</header>";
    return html;
  }

  function renderChapter() {
    const all = activeTreatise.prologue[state.lang] || [];
    const title = chapterTitle();
    const sections = all;
    let html = pageHead(title, esc(tx(activeTreatise.title)) + " · " + esc(tx(activeTreatise.subtitle)));
    html += renderSections(sections);
    html += renderColophon(activeTreatise);
    return '<article class="view-inner">' + html + "</article>";
  }

  function renderAppendix() {
    const all = activeTreatise.appendix[state.lang] || [];
    const lead = all.find((s) => s.type === "subhead");
    const title = (lead && lead.label) || t("appendix");
    const sections = lead ? all.filter((s) => s !== lead) : all;
    let html = pageHead(title, esc(tx(activeTreatise.title)));
    html += renderSections(sections);
    html += renderColophon(activeTreatise);
    return '<article class="view-inner">' + html + "</article>";
  }

  function renderNotes() {
    const sections = activeTreatise.notes[state.lang] || [];
    const title = (activeTreatise.notesTitle && activeTreatise.notesTitle[state.lang]) || t("notes");
    let html = pageHead(title, esc(tx(activeTreatise.title)));
    html += '<div class="notes-stack">';
    sections.forEach((sec) => {
      html += '<div class="note">';
      (sec.paragraphs || []).forEach((p) => {
        html += "<p>" + esc(p) + "</p>";
      });
      html += "</div>";
    });
    html += "</div>";
    const closing = activeTreatise.closing && activeTreatise.closing[state.lang];
    if (closing && closing.length) {
      html += '<p class="about-p">' + esc(closing.join(" ")) + "</p>";
    }
    html += renderColophon(activeTreatise);
    return '<article class="view-inner">' + html + "</article>";
  }

  function renderAbout() {
    const blocks = activeTreatise.about[state.lang] || [];
    const bits = [];
    if (activeTreatise.tradition) bits.push(esc(tx(activeTreatise.tradition)));
    if (activeTreatise.edition) bits.push(esc(tx(activeTreatise.edition)));
    const meta = bits.join(" · ");

    let html = "";
    let metaPlaced = false;
    blocks.forEach((b) => {
      if (b.type === "title") {
        html += renderBlocks([b]);
        if (meta) {
          html += '<p class="about-meta">' + meta + "</p>";
          metaPlaced = true;
        }
        return;
      }
      html += renderBlocks([b]);
    });

    if (!metaPlaced && meta) {
      html = '<p class="about-meta">' + meta + "</p>" + html;
    }

    const pdfHref = activeTreatise.pdf
      ? encodeURI(activeTreatise.pdf[state.lang] || activeTreatise.pdf.ru)
      : null;
    if (pdfHref) {
      html += '<p class="about-p"><a class="back-link" href="' + esc(pdfHref) +
        '" target="_blank" rel="noopener">' + esc(t("pdf")) + " ↗</a></p>";
    }
    if (activeTreatise.chapter) {
      html += '<p class="about-p"><a class="back-link" href="#/chapter">' +
        esc(chapterTitle()) + " →</a></p>";
    }
    return '<article class="view-inner">' + html + "</article>";
  }

  /* ------------------------------------------------------------------- UI */

  function wireDating(root) {
    $$(".dating-more", root).forEach((box) => {
      const label = $(".dating-toggle-label", box);
      if (!label) return;
      box.addEventListener("toggle", () => {
        label.textContent = box.open ? t("datingClose") : t("datingOpen");
      });
    });
  }

  function wireVerseTabs(root) {
    $$("[data-verses]", root).forEach((card) => {
      const tabs = $$('[role="tab"]', card);
      const panels = $$('[role="tabpanel"]', card);
      tabs.forEach((tab, idx) => {
        tab.addEventListener("click", () => selectTab(tabs, panels, idx));
        tab.addEventListener("keydown", (e) => {
          if (e.key !== "ArrowRight" && e.key !== "ArrowLeft") return;
          e.preventDefault();
          const dir = e.key === "ArrowRight" ? 1 : -1;
          const nextIdx = (idx + dir + tabs.length) % tabs.length;
          selectTab(tabs, panels, nextIdx);
          tabs[nextIdx].focus();
        });
      });

      const copy = $("[data-copy]", card);
      if (copy) {
        copy.addEventListener("click", () => {
          const active = panels.find((p) => !p.hasAttribute("hidden")) || panels[0];
          const text = $$(".verse-lines > span", active).map((s) => s.textContent).join("\n");
          copyText(text);
        });
      }
    });
  }

  function selectTab(tabs, panels, idx) {
    tabs.forEach((tab, i) => {
      const on = i === idx;
      tab.setAttribute("aria-selected", on ? "true" : "false");
      tab.tabIndex = on ? 0 : -1;
      panels[i].toggleAttribute("hidden", !on);
    });
  }

  function copyText(text) {
    const done = () => showToast(t("copied"));
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(text).then(done, fallback);
    } else {
      fallback();
    }
    function fallback() {
      const ta = document.createElement("textarea");
      ta.value = text;
      ta.setAttribute("readonly", "");
      ta.style.position = "fixed";
      ta.style.opacity = "0";
      document.body.appendChild(ta);
      ta.select();
      try { document.execCommand("copy"); done(); } catch (e) { /* ignore */ }
      document.body.removeChild(ta);
    }
  }

  let toastTimer = null;
  function showToast(msg) {
    const el = $("#toast");
    el.textContent = msg;
    el.classList.add("show");
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => el.classList.remove("show"), 1900);
  }

  function closeDrawer() {
    $("#sidebar").classList.remove("is-open");
    $("#backdrop").hidden = true;
    $("#menu-btn").setAttribute("aria-expanded", "false");
  }

  function openDrawer() {
    $("#sidebar").classList.add("is-open");
    $("#backdrop").hidden = false;
    $("#menu-btn").setAttribute("aria-expanded", "true");
  }

  function wireEvents() {
    window.addEventListener("hashchange", () => {
      render();
      closeDrawer();
    });

    $("#treatise-select").addEventListener("change", (e) => {
      state.treatiseId = e.target.value;
      localStorage.setItem("ao.treatise", state.treatiseId);
      activeTreatise = treatises.find((x) => x.id === state.treatiseId) || treatises[0];
      buildPoseList();
      buildChapterNav();
      updateBrand();
      updateTreatiseNote();
      if (site) {
        if (site.title) $("[data-site-title]").textContent = tx(site.title);
        if (site.tagline) $("[data-site-tagline]").textContent = tx(site.tagline);
      }
      const route = parseRoute();
      const exists = activeTreatise.poses.some((p) => p.key === (route.key || ""));
      if (route.view === "pose" && !exists) {
        const first = activeTreatise.poses[0];
        location.hash = first ? "#/pose/" + first.key : "#/about";
      } else {
        render();
      }
    });

    $("#filter").addEventListener("input", (e) => {
      state.filter = e.target.value;
      buildPoseList();
    });

    $$(".lang-switch button").forEach((btn) => {
      btn.addEventListener("click", () => {
        state.lang = btn.dataset.lang;
        localStorage.setItem("ao.lang", state.lang);
        applyStaticText();
        buildTreatiseSelect();
        buildChapterNav();
        buildPoseList();
        updateTreatiseNote();
        if (site) {
          if (site.title) $("[data-site-title]").textContent = tx(site.title);
          if (site.tagline) $("[data-site-tagline]").textContent = tx(site.tagline);
        }
        render();
      });
    });

    $("#theme-btn").addEventListener("click", () => {
      state.theme = state.theme === "dark" ? "light" : "dark";
      localStorage.setItem("ao.theme", state.theme);
      document.documentElement.setAttribute("data-theme", state.theme);
      updateThemeLabel();
    });

    $("#menu-btn").addEventListener("click", () => {
      const open = $("#sidebar").classList.contains("is-open");
      if (open) closeDrawer();
      else openDrawer();
    });
    $("#backdrop").addEventListener("click", closeDrawer);

    document.addEventListener("keydown", (e) => {
      const tag = (e.target.tagName || "").toLowerCase();
      if (tag === "input" || tag === "textarea" || tag === "select" || e.metaKey || e.ctrlKey || e.altKey) return;
      if (e.key === "Escape") closeDrawer();
      if (e.key !== "j" && e.key !== "k" && e.key !== "ArrowDown" && e.key !== "ArrowUp") return;
      if (e.key === "ArrowDown" || e.key === "ArrowUp") {
        if (document.activeElement && document.activeElement.tagName === "BUTTON") return;
      }
      const route = parseRoute();
      if (route.view !== "pose") return;
      const poses = activeTreatise.poses;
      const idx = poses.findIndex((p) => p.key === route.key);
      if (idx < 0) return;
      const nextIdx = (e.key === "j" || e.key === "ArrowDown") ? idx + 1 : idx - 1;
      if (nextIdx < 0 || nextIdx >= poses.length) return;
      e.preventDefault();
      location.hash = "#/pose/" + poses[nextIdx].key;
    });

    window.addEventListener("resize", () => {
      if (window.innerWidth > 920) closeDrawer();
    });
  }

  boot();
})();
