#!/usr/bin/env node
/* ==========================================================================
   «А всё ли ок у посетителя?» — проверка страниц так, как их открывает браузер

   tools/prerender.js пишет готовые страницы и заодно доказывает, что каждая из
   них отрисовывается. Но он же подставляет скрипту подсказки (localStorage с
   языком и трактатом, сервер на 127.0.0.1) — то есть проверяет сборку, а не
   то, что увидит человек.

   Этот скрипт открывает уже собранные страницы без подсказок: адрес как на
   GitHub Pages, пустое localStorage, данные берутся по относительным путям
   страницы. Проверяется два положения:

     1. обычное — страница должна отрисоваться сама;
     2. сбой — один файл данных отвечает 404. Напечатанный в HTML текст обязан
        остаться на месте: страница не имеет права превратиться в «Загрузка…».

   Запуск:  node tools/boot_check.js
   ========================================================================== */
"use strict";

const fs = require("fs");
const path = require("path");
const http = require("http");
const { JSDOM, VirtualConsole, ResourceLoader } = require("jsdom");

const ROOT = path.resolve(__dirname, "..");

const TYPES = {
  ".html": "text/html; charset=utf-8",
  ".js": "text/javascript; charset=utf-8",
  ".css": "text/css; charset=utf-8",
  ".json": "application/json; charset=utf-8",
  ".woff2": "font/woff2",
  ".txt": "text/plain; charset=utf-8"
};

/* Страницы, на которых проверяется каждое положение дел: оба корня (у них
   разная глубина, а значит и разная подстановка путей), страница позы, страница
   трактата и раздел. */
const ROUTES = [
  "/",
  "/en/",
  "/asana/pavanamuktasana/",
  "/en/asana/gomukhasana/",
  "/treatise/yoga-kaustubha/",
  "/en/treatise/hathapradipika/",
  "/en/treatise/yoga-kaustubha/introduction/"
];

/* Файл, который «пропадает» во второй половине проверки. Он не первый и не
   последний в списке, поэтому видно, что падение одного файла не рушит
   страницу целиком. */
const BREAK = /data\/manasollasa\.json$/;

class Loader extends ResourceLoader {
  /* Стили и шрифты странице для отрисовки не нужны — их не тянем, как и в
     сборке: иначе проверка ждала бы мегабайты впустую. */
  fetch(url, options) {
    if (/\.(css|woff2|woff|png|jpe?g|svg|ico)(\?|$)/.test(url)) return null;
    return super.fetch(url, options);
  }
}

const wait = (ms) => new Promise((r) => setTimeout(r, ms));

/* Необработанный отказ промиса в приложении убивает этот скрипт (в Node 22 так
   и задумано), и тогда вместо отчёта виден стек. Ловим его: у посетителя такой
   отказ выглядит как страница, застывшая на «Загрузка…», и это должно попасть
   в список проблем, а не оборвать проверку. */
const rejections = [];
process.on("unhandledRejection", (e) => {
  rejections.push((e && e.message) || String(e));
});

async function open(route, port, breakData, keep) {
  const file = route.endsWith("/") ? route + "index.html" : route;
  // Отметку «эта страница уже отрисована» снимаем: иначе готовый текст сойдёт
  // за доказательство работы скрипта, хотя скрипт мог и не загрузиться.
  const html = fs.readFileSync(path.join(ROOT, file), "utf8")
    .replace(/ data-rendered="[^"]*"/, "");

  const errors = [];
  const vc = new VirtualConsole();
  vc.on("jsdomError", (e) => errors.push(e.message));
  vc.on("error", (...a) => errors.push(a.join(" ")));

  const origin = "http://127.0.0.1:" + port + "/";
  const dom = new JSDOM(html, {
    url: origin + route.replace(/^\//, ""),
    runScripts: "dangerously",
    resources: new Loader(),
    pretendToBeVisual: true,
    virtualConsole: vc,
    beforeParse(window) {
      window.scrollTo = () => {};
      window.fetch = (u, o) => fetch(new URL(u, origin + route.replace(/^\//, "")).href, o);
    }
  });

  // Ждём того же, чего ждёт сборка: приложение отмечает документ маршрутом,
  // который только что нарисовало. В готовой странице эта отметка уже стоит,
  // поэтому дополнительно ждём, пока текст перестанет меняться.
  //
  // При сбое ждать «отметки» бессмысленно — её не будет. Ждём фиксированное
  // время: приложению нужно прочитать мегабайты данных, и только потом видно,
  // осталось ли на странице «Загрузка…».
  let last = "";
  const deadline = Date.now() + (breakData ? 6000 : 5000);
  while (Date.now() < deadline) {
    await wait(25);
    if (breakData) continue;
    const text = dom.window.document.querySelector("#view").textContent.trim();
    if (dom.window.document.documentElement.dataset.rendered &&
        text.length > 60 && text === last) break;
    last = text;
  }

  const doc = dom.window.document;
  const view = doc.querySelector("#view");
  const text = view.textContent.replace(/\s+/g, " ").trim();
  if (process.env.DEBUG) {
    console.log("   DEBUG", route, "| сбой:", breakData, "| rendered:",
      result0(dom), "| текст:", text.slice(0, 40), "| ошибки:", errors.slice(0, 2));
  }
  if (keep) return { route, dom, text, errors };

  const result = {
    route,
    rendered: doc.documentElement.dataset.rendered || "",
    title: doc.title,
    text,
    loading: /^(Загрузка…|Loading…)$/.test(text),
    errors
  };
  dom.window.close();
  return result;
}

/* ------------------------------------------------------------ поиск āсан

   Имена набраны с диакритикой («Вӣрāсана», «Vīrāsana»), а человек ищет
   обычными буквами — и по-русски, и по-английски, а то и в другом падеже.
   Таблица говорит, какой запрос какую позу обязан найти. */
const SEARCH_CASES = [
  ["/", "вирасана", "virasana"],
  ["/", "вирасану", "virasana"],
  ["/", "Вӣрāсана", "virasana"],
  ["/", "virasana", "virasana"],
  ["/", "Vīrāsana", "virasana"],
  ["/en/", "вирасану", "virasana"],
  ["/en/", "вирасана", "virasana"],
  ["/en/", "virasana", "virasana"],
  ["/en/", "уттана курмасана", "uttanakurmaka"],
  ["/en/", "uttanakurmaka", "uttanakurmaka"],
  ["/", "падмасана", "padmasana"],
  ["/en/", "padmāsana", "padmasana"]
];

async function searchOn(route, port) {
  const { dom } = await open(route, port, false, true);
  const doc = dom.window.document;
  const input = doc.querySelector("#filter");
  const found = (query) => {
    input.value = query;
    input.dispatchEvent(new dom.window.Event("input", { bubbles: true }));
    return [...doc.querySelectorAll("#pose-list li a")]
      .map((a) => a.getAttribute("href") || "");
  };
  return { found, close: () => dom.window.close() };
}

function result0(dom) {
  return dom.window.document.documentElement.dataset.rendered || "(нет)";
}

async function main() {
  const server = http.createServer((req, res) => {
    const url = decodeURIComponent(req.url.split("?")[0]);
    if (server.breakData && BREAK.test(url)) {
      if (process.env.DEBUG) console.log("   BREAK 404:", url);
      // Тело — не JSON: `404` само по себе число, и `r.json()` его разобрал бы,
      // сойдя за данные. Отдаём то, что действительно не читается.
      res.writeHead(404, { "Content-Type": "text/html; charset=utf-8" });
      return res.end("<html>404 Not Found</html>");
    }
    const file = path.join(ROOT, url);
    if (fs.existsSync(file) && fs.statSync(file).isDirectory()) {
      const index = path.join(file, "index.html");
      if (fs.existsSync(index)) {
        res.writeHead(200, { "Content-Type": TYPES[".html"] });
        return res.end(fs.readFileSync(index));
      }
      res.writeHead(404);
      return res.end("404");
    }
    if (!fs.existsSync(file)) {
      res.writeHead(404);
      return res.end("404");
    }
    res.writeHead(200, { "Content-Type": TYPES[path.extname(file)] || "application/octet-stream" });
    res.end(fs.readFileSync(file));
  });
  server.breakData = false;

  await new Promise((r) => server.listen(0, "127.0.0.1", r));
  const port = server.address().port;

  const problems = [];

  for (const route of ROUTES) {
    const page = await open(route, port, false);
    if (!page.rendered) {
      problems.push(`${route}: страница не отрисовалась` +
        (page.errors.length ? " — " + page.errors[0] : ""));
    } else if (page.loading) {
      problems.push(`${route}: на странице осталось «${page.text}»`);
    }
  }

  // Второе положение: данные отдаются с ошибкой. Напечатанный текст обязан
  // уцелеть, а слово «Загрузка…» — не появиться.
  server.breakData = true;
  for (const route of ROUTES) {
    const before = rejections.length;
    const page = await open(route, port, true);
    if (rejections.length > before) {
      problems.push(`${route}: при сбое данных приложение упало ` +
        `(${rejections[before]})`);
    }
    if (page.loading) {
      problems.push(`${route}: при сбое данных осталось «${page.text}»`);
    } else if (page.text.length < 200) {
      problems.push(`${route}: при сбое данных текст страницы пропал ` +
        `(${page.text.length} символов)`);
    }
  }

  // Третье положение: поиск по именам с диакритикой и без.
  for (const route of ["/", "/en/"]) {
    const page = await searchOn(route, port);
    for (const [where, query, key] of SEARCH_CASES) {
      if (where !== route) continue;
      const hits = page.found(query);
      if (!hits.some((href) => href.includes("/" + key + "/"))) {
        problems.push(`${route}: запрос «${query}» не нашёл ${key} ` +
          `(нашлось ${hits.length})`);
      }
    }
    page.close();
  }

  server.close();

  if (problems.length) {
    console.error("страницы у посетителя:\n  " + problems.join("\n  "));
    process.exit(1);
  }
  console.log(`страниц проверено: ${ROUTES.length} · ` +
    `запросов поиска: ${SEARCH_CASES.length} · ` +
    "обычное открытие, сбой данных и поиск без диакритики — всё сходится");
}

main();
