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
      chapter: "Глава 31",
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
      verseOwn: "здесь названа эта асана",
      treatises: "Трактаты",
      allAsanas: "Все āсаны",
      verseDeva: "Деванагари",
      verseIast: "IAST",
      verseCyr: "Кириллическая транслитерация",
      hpRefLead: "Этот стих напечатан в критическом издании так; ниже — перевод и все рукописи, названные в его аппарате, чтобы ни за чем не приходилось идти в другой раздел.",
      hpRefVerse: "стих",
      hpRefVerses: "стихи",
      hpRefHere: "здесь же",
      hpRefApparatus: "Рукописи и чтения",
      hpRefAlias: "Ссылка выше дана по нумерации старых изданий ({old}); в критическом издании этот стих — {new}. Стих напечатан здесь в нумерации критического издания.",
      chapterAdded: "Сверх главы 1 в собрание добавлена глава 3 — четыре стиха о Випарӣта-каран̣ӣ (3.73–3.77) и ещё один перед ними; они взяты из того же электронного критического издания, потому что других āсан в главе 3 нет. Страница позы: ",
      hpRefEditionTr: "Перевод издания",
      hpRefOwnTr: "Наш подстрочник",
      hpRefMetre: "Метр",
      abbrHead: "Сокращения в этом разделе",
      build: "версия"
    },
    en: {
      skip: "Skip to content",
      treatise: "Treatise",
      asanas: "Āsanas",
      chapter: "Chapter 31",
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
      verseOwn: "this pose is named here",
      treatises: "Treatises",
      allAsanas: "All āsanas",
      verseDeva: "Devanagari",
      verseIast: "IAST",
      verseCyr: "Cyrillic transliteration",
      hpRefLead: "This is how the verse is printed in the critical edition; below are the translation and every manuscript named in its apparatus, so that nothing has to be looked up in another section.",
      hpRefVerse: "verse",
      hpRefVerses: "verses",
      hpRefHere: "right here",
      hpRefApparatus: "Manuscripts and readings",
      hpRefAlias: "The reference above uses the numbering of the older editions ({old}); in the critical edition this verse is {new}. The verse is printed here in the critical edition’s numbering.",
      chapterAdded: "Besides chapter 1, chapter 3 has been added to the collection: the verses on Viparītakaraṇī (3.73–3.77) together with the one before them, taken from the same electronic critical edition, because chapter 3 contains no other āsanas. The pose page: ",
      hpRefEditionTr: "Edition translation",
      hpRefOwnTr: "Our rendering",
      hpRefMetre: "Metre",
      abbrHead: "Abbreviations in this section",
      build: "build"
    }
  };

  const BUILD = "2026-11-06.01";
  const V = "?v=" + BUILD;

  const state = {
    lang: localStorage.getItem("ao.lang") === "en" ? "en" : "ru",
    theme: localStorage.getItem("ao.theme") || "light",
    treatiseId: localStorage.getItem("ao.treatise") || null,
    filter: ""
  };

  /* ---------------------------------------------------------- page addresses

     Every route is a real file on GitHub Pages: /asana/padmasana/,
     /treatise/manasollasa/, and the same under /en/. tools/prerender.js writes
     those files and marks each page with data-static, data-route, data-base and
     data-treatise; the same script still answers old hash links (#/pose/…),
     which keep working wherever they were already shared.
  */
  const STATIC = document.body.dataset.static === "1";
  const BASE = document.body.dataset.base || "";        // prefix back to the site root
  const DECLARED = document.body.dataset.route || "";   // the route this file is

  // На статической странице язык задан самой страницей (<html lang>), а не
  // памятью прошлой сессии: иначе английская страница открылась бы по-русски,
  // пока посетитель не переключит язык вручную.
  if (STATIC) {
    state.lang = document.documentElement.lang === "en" ? "en" : "ru";
  }

  // Разделы названы по-английски в обоих языках: адрес трактата одинаков
  // в русской и английской версии и различается только префиксом /en/.
  const SECTION_SLUGS = {
    chapter: "introduction",
    appendix: "appendix",
    notes: "notes"
  };
  // Старые написания раздела (в том числе хеш-адреса из первых версий сайта)
  // читаются по-прежнему, чтобы уже разосланные ссылки не ломались.
  const SUB_VIEWS = {
    introduction: "chapter", vstuplenie: "chapter", intro: "chapter",
    appendix: "appendix", prilozhenie: "appendix",
    notes: "notes", primechaniya: "notes"
  };

  let site = null;
  let treatises = [];
  let activeTreatise = null;
  let lastPoseKey = null;
  let abbrList = [];      // сокращения, раскрытые в data/abbreviations.json
  let hpIndex = null;     // стихи «Хат̣хапрадӣпики» по номерам: 1.30 → карточка
  let hpAlias = {};       // старая нумерация → критическое издание: 3.79 → 3.74

  /* ------------------------------------------------ addresses of the routes */

  function pagePath(view, key, lang, treatiseId) {
    const prefix = lang === "en" ? "en/" : "";
    if (view === "home") return prefix;
    if (view === "pose") return prefix + "asana/" + key + "/";
    const id = treatiseId || (activeTreatise && activeTreatise.id) || "";
    if (view === "about") return prefix + "treatise/" + id + "/";
    const slug = SECTION_SLUGS[view];
    return prefix + "treatise/" + id + "/" + (slug ? slug + "/" : "");
  }

  // Where a link to that page points from the page we are on: a real relative
  // address on the prerendered site, a hash in the old single-page mode.
  function url(view, key, lang, treatiseId) {
    const lng = lang || state.lang;
    if (!STATIC) {
      if (view === "home") return "#/";
      if (view === "pose") return "#/pose/" + key;
      return "#/" + view;
    }
    return BASE + pagePath(view, key, lng, treatiseId);
  }

  // Маршрут словами — тот же, что лежит в data-route статической страницы.
  // Сборщик страниц ждёт, пока он появится: так видно, что отрисована именно
  // эта страница, а не та, что осталась в шаблоне от прошлой сборки.
  function routeString(route) {
    if (route.view === "home") return "home";
    if (route.view === "pose") return "pose/" + route.key;
    const id = route.treatise || (activeTreatise && activeTreatise.id) || "";
    const slug = SECTION_SLUGS[route.view];
    return "treatise/" + id + (slug ? "/" + slug : "");
  }

  // The page we are on, written the way url() writes it.
  function herePath() {
    const route = parseRoute();
    return pagePath(route.view, route.key, state.lang,
                    route.treatise || (activeTreatise && activeTreatise.id));
  }

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
     (м̣, р̣, н̇, н̃, ш́). The browser would take the letter from one web font
     and the mark from another (or from a fallback), and letter-spacing pushed
     the mark sideways; the marks are therefore drawn by CSS, and the real
     combining character stays in the text at zero size, so copying, searching
     and screen readers still get the true letter.

     The mark is placed from the baseline (see .mk in style.css), not from the
     line box: a line box grows with line-height, so a mark measured from its
     bottom edge slid down onto the letter in running text (line-height 1.7)
     and crossed it out. A capital keeps its mark above the cap height.
  */

  const MARK_CLASS = {
    "\u0323": "m-b",   // dot below
    "\u0307": "m-a",   // dot above
    "\u0301": "m-ac",  // acute
    "\u0303": "m-t",   // tilde
    "\u0304": "m-mac"  // macron
  };

  // У «р» хвост идёт вниз ровно под точкой: точку приходится опускать под него.
  // У «д» ножки уходят вниз по краям, а под точкой в середине буквы пусто —
  // поэтому её точка стоит на одной высоте с остальными (см. .mk.m-b).
  // Прописная «Д» — единственная, где ножки идут вниз по всей ширине.
  const DESCENDER = { "р": "d-deep", "Д": "d-tail" };

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
        const cls = marks.map((m) => MARK_CLASS[m]);
        if (base !== base.toLowerCase()) cls.push("is-cap");
        if (DESCENDER[base]) cls.push(DESCENDER[base]);
        out += '<span class="mk ' + cls.join(" ") + '">' +
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

  // Файлы (данные, PDF источника) лежат в корне сайта, а страница может стоять
  // на три уровня глубже — тогда к адресу приписывается data-base.
  function asset(href) {
    return href && STATIC && !/^(https?:|data:|\/|#)/.test(href) ? BASE + href : href;
  }

  async function boot() {
    document.documentElement.setAttribute("data-theme", state.theme);
    applyStaticText();
    $("#view").innerHTML = '<p class="empty">' + esc(t("loading")) + "</p>";

    let index;
    try {
      index = await fetch(asset("data/treatises.json") + V).then((r) => {
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
        const data = await fetch(asset(meta.file) + V).then((r) => r.json());
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

    // Справочник сокращений — отдельный файл: он не про трактат, а про то,
    // как читать аппарат любого из них.
    try {
      const abbr = await fetch(asset("data/abbreviations.json") + V).then((r) =>
        (r.ok ? r.json() : null));
      abbrList = (abbr && abbr.entries) || [];
    } catch (e) {
      abbrList = [];
    }
    // Глава 3 «Хат̣хапрадӣпики» лежит отдельным файлом: в двух PDF её не было,
    // а позу Випарӣта-каран̣ӣ трактат описывает именно там. Стихи встают
    // в тот же трактат, чтобы у позы был его собственный раздел, а не сноска.
    const hp = treatises.find((x) => x.id === "hathapradipika");
    try {
      const ch3 = await fetch(asset("data/hathapradipika-ch3.json") + V).then((r) =>
        (r.ok ? r.json() : null));
      if (hp && ch3 && ch3.poses) {
        ch3.poses.forEach((pose) => {
          pose.chapter = 3;
          pose.addedLater = ch3;
          hp.poses.push(pose);
        });
        hpAlias = (ch3.vulgate && ch3.vulgate.map) || {};
      }
    } catch (e) {
      hpAlias = {};
    }
    hpIndex = hp ? buildHpIndex(hp) : null;

    // a prerendered treatise page says which treatise it is; that wins over the
    // one the visitor last looked at
    if (DECLARED.startsWith("treatise/")) {
      state.treatiseId = DECLARED.split("/")[1];
      localStorage.setItem("ao.treatise", state.treatiseId);
    }
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

    render();
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
    if (brand) brand.setAttribute("href", url("home"));
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
    const items = prologue.length ? [[url("chapter"), chapterNavLabel()]] : [];
    if (appendix.length) items.push([url("appendix"), appendixLabel.split(".")[0]]);
    if (notes.length) items.push([url("notes"), notesTitle]);
    items.push([url("about"), t("treatiseAbout")]);
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
            const active = isCurrent(url("pose", p.key));
            return (
              '<li' + (p.inTreatise === false ? ' class="is-other"' : "") +
              '><a href="' + url("pose", p.key) + '"' +
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
    return STATIC ? href === BASE + herePath() : location.hash === href;
  }

  function markCurrent() {
    $$(".pose-list a, #chapter-nav a").forEach((a) => {
      if (isCurrent(a.getAttribute("href"))) a.setAttribute("aria-current", "page");
      else a.removeAttribute("aria-current");
    });
  }

  /* --------------------------------------------------------------- routing */

  function declaredRoute() {
    const parts = DECLARED.split("/").filter(Boolean);
    if (parts[0] === "pose" && parts[1]) return { view: "pose", key: parts[1] };
    if (parts[0] === "treatise" && parts[1]) {
      return { view: SUB_VIEWS[parts[2]] || "about", treatise: parts[1] };
    }
    return { view: "home" };
  }

  function parseRoute() {
    const hash = location.hash || "";
    if (hash && hash !== "#/") {
      const parts = hash.replace(/^#\/?/, "").split("/");
      if (parts[0] === "pose" && parts[1]) return { view: "pose", key: parts[1] };
      if (["chapter", "appendix", "notes", "about"].includes(parts[0])) {
        return { view: parts[0] };
      }
    }
    return declaredRoute();
  }

  function render() {
    const route = parseRoute();
    const view = $("#view");
    verseSeq = 0;
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
    if (route.view === "home") html = renderHome();
    else if (route.view === "pose") html = renderPose(route.key);
    else if (route.view === "chapter") html = renderChapter();
    else if (route.view === "appendix") html = renderAppendix();
    else if (route.view === "notes") html = renderNotes();
    else if (route.view === "about") html = renderAbout();

    view.innerHTML = applyMarks(html);
    view.style.animation = "none";
    void view.offsetWidth;
    view.style.animation = "";

    document.documentElement.dataset.rendered = routeString(route);
    markCurrent();
    wireDating(view);
    wireVerseTabs(view);
    wireAbbrNotes(view);
    wireHpRefs(view);
    document.title = pageTitle(route);
    window.scrollTo({ top: 0, behavior: "auto" });
  }

  function pageTitle(route) {
    const base = site && site.title ? tx(site.title) : "Āsana: Origins";
    if (route.view === "home") return base + " — " + (site && site.tagline ? tx(site.tagline) : base);
    if (route.view === "pose") {
      const found = activeTreatise.poses.find((p) => p.key === route.key);
      return found ? tx(found.name) + " — " + base : base;
    }
    const tr = activeTreatise ? tx(activeTreatise.title) : "";
    const titled = (label) => [label, tr, base].filter(Boolean).join(" — ");
    if (route.view === "about") return titled(t("about"));
    if (route.view === "chapter") return titled(chapterTitle());
    if (route.view === "appendix") return titled(t("appendix"));
    if (route.view === "notes") return titled(t("notes"));
    return base;
  }

  /* ------------------------------------------------------------ rendering */

  function renderHome() {
    const base = site && site.title ? tx(site.title) : "Āsana: Origins";
    const all = [];
    treatises.forEach((tr) => (tr.poses || []).forEach((p) => all.push(p)));

    let html = '<article class="view-inner">';
    html += '<header class="page-head home-head"><h1>' + esc(base) + "</h1>";
    if (site && site.tagline) {
      html += '<p class="page-meta">' + esc(tx(site.tagline)) + "</p>";
    }
    html += '</header>';

    html += '<section class="home-block">';
    html += '<h2 class="about-h2">' + esc(t("treatises")) + "</h2>";
    treatises.forEach((tr) => {
      const bits = [];
      if (tr.tradition) bits.push(esc(tx(tr.tradition)));
      if (tr.edition) bits.push(esc(tx(tr.edition)));
      html += '<section class="home-treatise">';
      html += '<h3 class="about-h3"><a href="' + url("about", null, null, tr.id) + '">' +
        esc(tx(tr.title)) + "</a></h3>";
      if (bits.length) html += '<p class="about-meta">' + bits.join(" · ") + "</p>";
      html += '<ul class="home-poses">';
      (tr.poses || []).forEach((pose) => {
        html += '<li><a href="' + url("pose", pose.key) + '">' + esc(tx(pose.name)) +
          "</a><span>" + esc(tx(pose.verses)) + "</span></li>";
      });
      html += "</ul></section>";
    });
    html += "</section>";

    const unique = [];
    all.forEach((p) => { if (!unique.includes(p.key)) unique.push(p.key); });
    html += '<p class="home-total">' + esc(t("allAsanas")) + " — " + unique.length + "</p>";
    html += "</article>";
    return html;
  }

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
      (tx(primary.gloss) ? '<p class="pose-gloss">' + esc(tx(primary.gloss)) + "</p>" : "") +
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
      const chap = pose.chapter || tr.chapter;
      html += '<span class="ref">' +
        esc(tx(tr.chapterWord) || (state.lang === "ru" ? "глава" : "chapter")) +
        (chap ? " " + esc(chap) : "") + "</span>";
      if (multi) {
        html += '<a class="link" href="' + url("about", null, null, tr.id) + '">' +
          esc(t("toAbout")) + "</a>";
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

  // Ячейка таблицы — строка текста или {html}: во второй можно поставить
  // ссылку (данные свои, из data/*.json).
  function cellHtml(cell) {
    if (cell && typeof cell === "object") return cell.html != null ? cell.html : esc(cell.text || "");
    return esc(cell == null ? "" : cell);
  }

  function cellText(cell) {
    if (cell && typeof cell === "object") return (cell.text || "").replace(/<[^>]*>/g, "");
    return cell == null ? "" : String(cell);
  }

  // Пословный разбор приходит в двух формах: список групп, где группа — это
  // список пар «слово → значение» (так у большинства трактатов), и просто
  // список пар (так записан Ш́āрн̇гадхара-паддхати). Раньше вторая форма
  // принималась за список групп, и разбор рассыпа́лся на отдельные буквы:
  // «uttānau» превращалось в d t → u, d d → t и так далее.
  function wordGroups(sec) {
    const raw = sec.groups || (sec.pairs ? [sec.pairs] : []);
    if (!raw.length) return [];
    const flat = raw.every((g) => Array.isArray(g) && typeof g[0] === "string");
    return flat ? [raw] : raw;
  }

  // Разбор по словам. Один и тот же код для страницы асаны и для статьи о
  // датировке: раньше статья о датировке шла через renderBlocks(), где этого
  // типа не было, и разбор с литературным переводом молча выпадали, оставляя
  // пустые абзацы.
  function renderWordsBlock(sec) {
    let html = '<section class="section">';
    if (sec.label) html += '<h3 class="section-label"><span>' + esc(sec.label) + "</span></h3>";
    const groups = wordGroups(sec);
    if (!groups.length) {
      (sec.paragraphs || []).forEach((p) => {
        html += '<p class="about-p">' + esc(p) + "</p>";
      });
    }
    const titles = sec.titles || [];
    groups.forEach((pairs, gi) => {
      // a passage quoted in full keeps the verses apart in the analysis too
      if (titles[gi]) {
        html += '<p class="words-verse">' + esc(titles[gi]) + "</p>";
      }
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
    return html + "</section>";
  }

  function renderNoteBlock(sec) {
    return '<aside class="note">' +
      (sec.paragraphs || []).map((p) => "<p>" + esc(p) + "</p>").join("") +
      "</aside>";
  }

  function renderProseBlock(sec) {
    let html = '<section class="section prose-' + esc(sec.key || "") + '">';
    if (sec.label) html += '<h3 class="section-label"><span>' + esc(sec.label) + "</span></h3>";
    return html + (sec.paragraphs || []).map((p) => "<p>" + esc(p) + "</p>").join("") +
      "</section>";
  }

  function renderTable(b) {
    const rows = b.rows || [];
    if (!rows.length) return "";
    let html = '<div class="doc-table-wrap"><table class="doc-table">';
    let body = rows;
    if (rows.length > 1) {
      html += "<thead><tr>" +
        rows[0].map((c) => "<th>" + cellHtml(c) + "</th>").join("") + "</tr></thead>";
      body = rows.slice(1);
    }
    // On a phone the table becomes a stack of cards; each cell carries the
    // name of its column in data-label, so nothing has to be guessed.
    const heads = rows.length > 1 ? rows[0] : [];
    html += "<tbody>" +
      body.map((r) => "<tr>" + r.map((c, i) =>
        "<td" + (heads[i] ? ' data-label="' + esc(cellText(heads[i])) + '"' : "") + ">" +
        cellHtml(c) + "</td>").join("") + "</tr>").join("") +
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
        case "words":
          return renderWordsBlock(b);
        case "note":
          return renderNoteBlock(b);
        case "prose":
          return renderProseBlock(b);
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
      // The short block lists every date the article has, in the camps the
      // article itself puts them in: showing one camp alone read as if five
      // scholars were the whole literature. A treatise that still carries a
      // single flat list (items, no groups) renders exactly as before.
      const groups = summary.groups && summary.groups.length
        ? summary.groups
        : [{ items: summary.items || [], label: summary.label }];
      if (summary.note) {
        html += '<p class="dating-note dating-lead">' + esc(tx(summary.note)) + "</p>";
      }
      groups.forEach((group) => {
        const items = (group && group.items) || [];
        if (!items.length) return;
        html += '<div class="dating-group">';
        if (group.title) {
          html += '<p class="dating-group-title"><span>' + esc(tx(group.title)) + "</span></p>";
        }
        if (group.intro) {
          html += '<p class="dating-group-intro">' + esc(tx(group.intro)) + "</p>";
        }
        html += '<ul class="dating-rows">';
        items.forEach((item) => {
          html += "<li>";
          html += '<span class="dating-who">' + esc(tx(item.who)) + "</span>";
          html += '<span class="dating-when">' + esc(tx(item.when));
          if (item.whenNote) {
            html += '<span class="dating-when-note">' + esc(tx(item.whenNote)) + "</span>";
          }
          html += "</span>";
          if (item.work) {
            const label = group.label || summary.label;
            const workLabel = label ? tx(label) : t("datingSource");
            html += '<span class="dating-work"><span class="dating-work-label">' +
              esc(workLabel) + "</span>" + esc(tx(item.work)) + "</span>";
          }
          html += "</li>";
        });
        html += "</ul></div>";
      });
      if (summary.note2) {
        html += '<p class="dating-note dating-bound">' + esc(tx(summary.note2)) + "</p>";
      }
    }

    if (full && full.blocks && full.blocks.length) {
      html += '<details class="dating-more">';
      html += '<summary><span class="dating-toggle-label">' + esc(t("datingOpen")) +
        "</span></summary>";
      html += '<div class="dating-full">';
      html += '<h3 class="dating-full-title">' + esc(full.title) + "</h3>";
      html += renderBlocks(full.blocks);
      html += '<p class="dating-full-link"><a href="' + url("about", null, null, tr.id) + '">' +
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
        html += '<div class="verse-card' + (sec.own ? " is-own" : "") + '">';
        if (sec.verses) {
          html += '<p class="verse-card-num"><span>' + esc(sec.verses) + "</span>" +
            (sec.own ? '<em class="verse-card-own">' + esc(t("verseOwn")) + "</em>" : "") +
            "</p>";
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
        html += renderWordsBlock(sec);
        i += 1;
        continue;
      }
      if (sec.type === "note") {
        html += renderNoteBlock(sec);
        i += 1;
        continue;
      }
      if (sec.type === "prose") {
        html += renderProseBlock(sec);
        i += 1;
        continue;
      }
      if (sec.type === "label") {
        html += '<h3 class="section-label"><span>' + esc(sec.label) + "</span></h3>";
        i += 1;
        continue;
      }
      if (sec.type === "list" || sec.type === "table") {
        html += '<section class="section">' +
          (sec.label ? '<h3 class="section-label"><span>' + esc(sec.label) + "</span></h3>" : "") +
          renderBlocks([sec]) + "</section>";
        i += 1;
        continue;
      }
      if (sec.type === "subhead") {
        html += '<h2 class="subhead">' + esc(sec.label) + "</h2>";
        i += 1;
        continue;
      }
      if (sec.type === "deva") {
        // a Devanāgarī quotation inside a pose page (e.g. §6.3 of the
        // Mānasollāsa), rendered exactly as on the treatise page
        html += renderBlocks([sec]);
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
      if ((sec.type === "p" || sec.type === "h3" || sec.type === "h4") &&
          (sec.text != null || sec.html != null)) {
        // заголовок или абзац внутри раздела: классы те же, что у «О трактате»
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

  // Идентификаторы вкладок считаются, а не берутся случайными: иначе две
  // сборки одной и той же страницы различались бы, и `node tools/prerender.js
  // --check` не мог бы сказать, изменилось ли что-нибудь на самом деле.
  let verseSeq = 0;

  function renderVerses(run) {
    let tabs = "";
    let panels = "";
    run.forEach((sec, idx) => {
      verseSeq += 1;
      const id = "verse-" + (sec.key || "v") + "-" + verseSeq + "-" + idx;
      const selected = idx === 0;
      tabs +=
        '<button type="button" role="tab" id="tab-' + id + '" aria-controls="' + id +
        '" aria-selected="' + (selected ? "true" : "false") + '" data-tab="' + id + '">' +
        esc(sec.label || t("verse" + (sec.key || "").charAt(0).toUpperCase() +
          (sec.key || "").slice(1))) + "</button>";
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
      ? '<a class="prev" href="' + url("pose", prev.key) + '"><span class="dir">' +
        esc(t("prev")) + '</span><span class="to">' + esc(prev.name) + "</span></a>"
      : "<span></span>";
    html += next
      ? '<a class="next" href="' + url("pose", next.key) + '"><span class="dir">' +
        esc(t("next")) + '</span><span class="to">' + esc(next.name) + "</span></a>"
      : "";
    html += "</nav>";
    return html;
  }

  function renderColophon(tr) {
    const pdfHref = tr.pdf ? asset(encodeURI(tr.pdf[state.lang] || tr.pdf.ru)) : null;
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
    // первый подзаголовок служит и названием страницы — второй раз не печатаем
    const lead = all[0] && all[0].type === "subhead" ? all[0] : null;
    const sections = lead && lead.label === title ? all.slice(1) : all;
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
      // раздел с типом — заголовок, список, таблица или цитата; так же, как в
      // остальных разделах трактата. Без типа — прежнее примечание абзацами.
      if (sec && sec.type) {
        html += renderSections([sec]);
        return;
      }
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
    // подпись издания идёт после шапки: титул, строка главы, подзаголовок
    let head = 0;
    while (head < blocks.length && (blocks[head].type === "title" || blocks[head].type === "byline")) {
      head += 1;
    }
    blocks.forEach((b, i) => {
      html += renderBlocks([b]);
      if (meta && !metaPlaced && i === head - 1) {
        html += '<p class="about-meta">' + meta + "</p>";
        metaPlaced = true;
      }
    });

    if (!metaPlaced && meta) {
      html = '<p class="about-meta">' + meta + "</p>" + html;
    }

    // Глава, добавленная в собрание сверх PDF (глава 3 «Хат̣хапрадӣпики»),
    // называется здесь же: в оглавлении самого издания её нет.
    const added = activeTreatise.poses.find((p) => p.addedLater);
    if (added) {
      html += '<p class="about-p about-added">' + esc(t("chapterAdded")) +
        '<a class="back-link" href="' + url("pose", added.key) + '">' +
        esc(tx(added.name)) + " →</a></p>";
    }

    const pdfHref = activeTreatise.pdf
      ? asset(encodeURI(activeTreatise.pdf[state.lang] || activeTreatise.pdf.ru))
      : null;
    if (pdfHref) {
      html += '<p class="about-p"><a class="back-link" href="' + esc(pdfHref) +
        '" target="_blank" rel="noopener">' + esc(t("pdf")) + " ↗</a></p>";
    }
    // ссылка на вступление — только если оно есть: у «Ма̄насолла̄сы» его нет
    if (activeTreatise.chapter && (activeTreatise.prologue[state.lang] || []).length) {
      html += '<p class="about-p"><a class="back-link" href="' + url("chapter") + '">' +
        esc(chapterTitle()) + " →</a></p>";
    }
    return '<article class="view-inner">' + html + "</article>";
  }

  /* ------------------------------------------------------------------- UI */

  /* --------------------------- «Хат̣хапрадӣпикā»: справка прямо на месте

     Другой трактат может сослаться на «Хат̣хапрадӣпику» («ср. HP 1.30»,
     «HP 1.45–47», «HP 3.79–82»). Читатель не должен ни листать страницу,
     ни переключать трактат, ни догадываться, о каком стихе речь: рядом
     с упоминанием встаёт сам стих — деванагари, IAST, кириллица, перевод
     и весь аппарат с полными названиями рукописей.

     Стихи берутся из данных «Хат̣хапрадӣпики», то есть из того же издания,
     что и её собственная страница; ничего не переписывается руками.
  */

  const HP_REF = /(?:\bHP\b|\bХП\b|Haṭhapradīpik\w*)\s*[.:]?\s*(?:гл\.?\s*[1-4]\s*[.,]?\s*)?([1-4])\s*[.,]\s*(\d{1,3})(?:\s*[–—-]\s*(\d{1,3}))?/g;

  // Какой блок данных относится к стиху: заголовок «Стих 1.45–46» открывает
  // карточку, а всё до следующего заголовка принадлежит ей.
  function buildHpIndex(doc) {
    const index = {};
    const scan = (blocks) => {
      let entry = null;
      (blocks || []).forEach((b) => {
        if (b.type === "h4" && b.text) {
          const m = /(\d)\s*[.]\s*(\d{1,3})(?:\s*[–—-]\s*(\d{1,3}))?/.exec(b.text);
          entry = null;
          if (m) {
            const chapter = m[1];
            const from = parseInt(m[2], 10);
            const to = m[3] ? parseInt(m[3], 10) : from;
            entry = {
              chapter: chapter, range: "", sections: null, edition: null,
              own: null, metre: null, apparatus: [], verses: []
            };
            for (let n = from; n <= to; n += 1) {
              index[chapter + "." + n] = entry;
              entry.verses.push(chapter + "." + n);
            }
            entry.range = to > from
              ? m[2] + "–" + m[3] : m[2];
          }
          return;
        }
        if (!entry) return;
        if (b.type === "verse_card") entry.sections = b.sections;
        else if (b.type === "prose" && b.key === "edition") entry.edition = b.paragraphs;
        else if (b.type === "prose" && b.key === "own") entry.own = b.paragraphs;
        else if (b.type === "prose" && b.key === "metre") entry.metre = b.paragraphs;
        else if (b.type === "list" && b.items && b.items.length &&
                 /(Разночтени|Readings)/i.test(String(b.label || ""))) {
          entry.apparatus = b.items;
        }
      });
    };
    (doc.poses || []).forEach((p) => scan(p.text[state.lang] || p.text.ru));
    scan(doc.prologue[state.lang] || doc.prologue.ru);
    return index;
  }

  function cardLines(sec) {
    const lines = (sec && sec.lines) || [];
    return lines.map((l) => '<span>' + esc(l) + "</span>").join("");
  }

  function renderHpCard(entry) {
    const many = String(entry.range).indexOf("–") >= 0;
    const label = entry.chapter + "." + entry.range;
    let html = '<aside class="hp-ref">';
    html += '<p class="hp-ref-head"><span class="hp-ref-name">' +
      esc(state.lang === "en" ? "Haṭhapradīpikā" : "Хат̣хапрадӣпикā") + "</span>" +
      '<span class="hp-ref-where">' + esc(many ? t("hpRefVerses") : t("hpRefVerse")) +
      " " + esc(label) + " · " + esc(t("hpRefHere")) + "</span></p>";
    html += '<p class="hp-ref-lead">' + esc(t("hpRefLead")) + "</p>";
    if (entry.printedAs) {
      html += '<p class="hp-ref-lead hp-ref-alias">' + esc(
        t("hpRefAlias").replace("{old}", entry.printedAs).replace("{new}", label)
      ) + "</p>";
    }

    if (entry.sections) {
      entry.sections.forEach((sec) => {
        html += '<p class="hp-ref-line ' + esc(sec.key || "") + '">' +
          cardLines(sec) + "</p>";
      });
    }
    if (entry.edition && entry.edition.length) {
      html += '<p class="hp-ref-tr"><span class="hp-ref-tr-label">' +
        esc(t("hpRefEditionTr")) + "</span> " +
        entry.edition.map(esc).join(" ") + "</p>";
    }
    if (entry.own && entry.own.length) {
      html += '<p class="hp-ref-tr"><span class="hp-ref-tr-label">' +
        esc(t("hpRefOwnTr")) + "</span> " +
        entry.own.map(esc).join(" ") + "</p>";
    }
    if (entry.metre && entry.metre.length) {
      html += '<p class="hp-ref-tr"><span class="hp-ref-tr-label">' +
        esc(t("hpRefMetre")) + "</span> " + entry.metre.map(esc).join(" ") + "</p>";
    }
    if (entry.apparatus && entry.apparatus.length) {
      html += '<div class="hp-ref-app"><p class="hp-ref-app-head">' +
        esc(t("hpRefApparatus")) + "</p><ul>";
      entry.apparatus.forEach((it) => {
        const body = it && it.html != null ? it.html : esc(it);
        html += "<li>" + body + "</li>";
      });
      html += "</ul></div>";
    }
    html += "</aside>";
    return html;
  }

  function wireHpRefs(root) {
    if (!hpIndex) return;
    const shown = {};
    const hits = [];
    const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, null);
    let node = walker.nextNode();
    while (node) {
      const text = node.nodeValue || "";
      if (/(HP|ХП|Haṭhapradīpik)/.test(text)) {
        const re = new RegExp(HP_REF.source, "g");
        let m = re.exec(text);
        while (m) {
          const from = parseInt(m[2], 10);
          const to = m[3] ? parseInt(m[3], 10) : from;
          const entries = [];
          for (let n = from; n <= to; n += 1) {
            const key = m[1] + "." + n;
            const direct = hpIndex[key];
            const e = direct || hpIndex[hpAlias[key]];
            if (e && entries.indexOf(e) < 0) {
              if (!direct && hpAlias[key]) e.printedAs = key;
              entries.push(e);
            }
          }
          if (entries.length) hits.push({ node: node, entries: entries });
          m = re.exec(text);
        }
      }
      node = walker.nextNode();
    }

    hits.forEach((hit) => {
      const fresh = hit.entries.filter((e) => !shown[e.range]);
      if (!fresh.length) return;
      fresh.forEach((e) => { shown[e.range] = true; });
      const host = hit.node.parentElement &&
        hit.node.parentElement.closest("p, li, blockquote, td, dd, figcaption") ||
        hit.node.parentElement;
      if (!host || !host.parentElement) return;
      const holder = document.createElement("div");
      holder.className = "hp-refs";
      holder.innerHTML = fresh.map(renderHpCard).join("");
      host.parentElement.insertBefore(holder, host.nextSibling);
    });
  }

  /* ------------------------------- сокращения: расшифровка в каждом разделе

     Аппарат цитируется дословно, поэтому сокращение внутри цитаты остаётся
     как в источнике. Расшифровка ставится в начале раздела — до того места,
     где сокращение встретится, — и перечисляет только те сокращения, которые
     в этом разделе действительно есть.
  */
  function wireAbbrNotes(root) {
    if (!abbrList.length) return;
    $$(".treatise-block", root).forEach((block) => {
      const text = block.textContent || "";
      const used = abbrList.filter((a) => {
        // границы слова — по свойствам Unicode, без перечисления алфавитов:
        // иначе в самом коде страницы оказалось бы слово из двух письменностей
        const re = new RegExp("(^|[^\\p{L}\\p{N}])" +
          a.code.replace(/[.*+?^${}()|[\]\\]/g, "\\$&") +
          "($|[^\\p{L}\\p{N}])", "u");
        return re.test(text);
      });
      if (!used.length) return;
      const head = $(".treatise-head", block);
      const box = document.createElement("div");
      box.className = "abbr-note";
      box.innerHTML = '<p class="abbr-note-head">' + esc(t("abbrHead")) + "</p>" +
        '<ul class="abbr-list">' + used.map((a) =>
          '<li><b>' + esc(a.code) + "</b> — " +
          esc(state.lang === "en" ? a.en : a.ru) + "</li>").join("") + "</ul>";
      if (head && head.parentElement === block) {
        block.insertBefore(box, head.nextSibling);
      } else {
        block.insertBefore(box, block.firstChild);
      }
    });
  }

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
      if (STATIC) {
        // one treatise is one set of pages, so choosing another one is a
        // normal page load, not a repaint
        location.href = url("about", null, null, state.treatiseId);
        return;
      }
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
        if (STATIC && btn.dataset.lang !== state.lang) {
          const route = parseRoute();
          location.href = url(route.view, route.key, btn.dataset.lang,
                              route.treatise || (activeTreatise && activeTreatise.id));
          return;
        }
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
      location.href = url("pose", poses[nextIdx].key);
    });

    window.addEventListener("resize", () => {
      if (window.innerWidth > 920) closeDrawer();
    });
  }

  boot();
})();
