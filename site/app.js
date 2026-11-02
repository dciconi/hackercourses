(() => {
  "use strict";

  const DATA = window.HACKER_COURSES || { topics: [], courses: [], comments: [] };
  const PAGE = 60;
  const ALL = "";
  const STANCE = ["Criticizes", "Mentions", "Recommends", "Strongly recommends"];
  const BADGE = { classic: ["Classic", "classic"], evergreen: ["Evergreen", "evergreen"],
                  rising: ["Rising", "rising"], "hidden gem": ["Hidden gem", "gem"] };
  const VIEWS = [
    { id: "best", label: "Best", sort: "score" },
    { id: "trending", label: "Trending", sort: "trend" },
    { id: "gems", label: "Hidden gems", sort: "score", test: (c) => c.badges.includes("hidden gem") },
    { id: "evergreen", label: "Evergreen", sort: "score", test: (c) => c.badges.includes("evergreen") },
    { id: "saved", label: "Saved", sort: "score", test: (c) => saved.has(c.id) },
  ];
  const SORTS = {
    score: ["Best ranked", (a, b) => b.score - a.score],
    trend: ["Trending", (a, b) => b.trend - a.trend || b.score - a.score],
    recommenders: ["Most recommenders", (a, b) => b.recommenders - a.recommenders || b.score - a.score],
    recent: ["Recently recommended", (a, b) => b.last - a.last],
    oldest: ["Longest-standing", (a, b) => a.first - b.first],
  };
  const ERAS = { "": "Any era", "2000s": "First recommended 2006–09", "2010s": "First recommended 2010s",
                 "2020s": "First recommended 2020s" };

  const $ = (id) => document.getElementById(id);
  const grid = $("grid"), views = $("views"), filters = $("filters"), status = $("status"), more = $("more");
  const q = $("q"), listView = $("listView"), courseView = $("courseView"), help = $("help"), about = $("about");
  const byId = new Map(DATA.courses.map((c) => [c.id, c]));

  // ---- per-viewer storage (browser only; never required to render) ----------------

  function load(key, fallback) {
    try { const v = localStorage.getItem(key); return v ? JSON.parse(v) : fallback; } catch { return fallback; }
  }
  function store(key, value) {
    try { localStorage.setItem(key, JSON.stringify(value)); } catch { /* private mode etc. */ }
  }
  const saved = new Set(load("hc.saved", []));
  const seen = new Set(load("hc.seen", []));
  const theme = load("hc.theme", null);
  if (theme) document.documentElement.dataset.theme = theme;

  // ---- helpers ----------------------------------------------------------------------

  const year = (t) => new Date(t * 1000).getUTCFullYear();
  const span = (c) => (year(c.first) === year(c.last) ? `${year(c.first)}` : `${year(c.first)}–${year(c.last)}`);
  const plural = (n, w) => `${n.toLocaleString()} ${w}${n === 1 ? "" : "s"}`;
  const threadUrl = (id) => `https://news.ycombinator.com/item?id=${id}`;
  const escapeRx = (s) => s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  const el = (tag, cls, text) => {
    const e = document.createElement(tag);
    if (cls) e.className = cls;
    if (text != null) e.textContent = text;
    return e;
  };

  function highlight(node, text, terms) {
    if (!terms.length) { node.textContent = text; return node; }
    const rx = new RegExp(`(${terms.map(escapeRx).join("|")})`, "gi");
    text.split(rx).forEach((part, i) => node.append(i % 2 ? el("mark", null, part) : part));
    return node;
  }

  const topicArt = (topic) =>
    `img/topics/${topic.toLowerCase().replace("&", "and").replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "")}.svg`;

  // The course's own preview image when it has one, else its topic illustration.
  // Remote images are hotlinked without a referrer and swap to the illustration if they fail.
  function thumb(c, cls) {
    const box = el("div", cls);
    const img = el("img");
    img.alt = "";
    img.loading = "lazy";
    img.decoding = "async";
    img.referrerPolicy = "no-referrer";
    img.src = c.img || topicArt(c.topic);
    if (!c.img) box.classList.add("art");
    img.addEventListener("error", () => {
      if (!box.classList.contains("art")) { box.classList.add("art"); img.src = topicArt(c.topic); }
    });
    box.append(img);
    return box;
  }

  function badgeEls(c) {
    // "Classic" already implies longevity, so don't repeat it with "Evergreen".
    const shown = c.badges.includes("classic") ? c.badges.filter((b) => b !== "evergreen") : c.badges;
    return shown.map((b) => el("span", `badge ${BADGE[b][1]}`, BADGE[b][0]));
  }

  // ---- list state ----------------------------------------------------------------------

  const state = { view: "best", topic: ALL, level: ALL, cost: ALL, format: ALL, era: ALL, sort: "score",
                  query: "", terms: [], list: [], shown: 0, active: 0, cols: 1 };
  let cards = [];

  function renderViews() {
    views.replaceChildren();
    VIEWS.forEach((v, i) => {
      const b = el("button");
      b.type = "button"; b.role = "tab"; b.id = `view-${v.id}`;
      b.setAttribute("aria-controls", "grid");
      b.setAttribute("aria-selected", String(v.id === state.view));
      b.tabIndex = v.id === state.view ? 0 : -1;
      b.title = `Shortcut: ${i + 1}`;
      b.append(v.label);
      if (v.id === "saved") b.append(el("span", "n", String(saved.size)));
      else if (v.test) b.append(el("span", "n", String(DATA.courses.filter(v.test).length)));
      b.addEventListener("click", () => selectView(v.id));
      views.append(b);
    });
  }

  views.addEventListener("keydown", (e) => {
    const i = VIEWS.findIndex((v) => v.id === state.view);
    const next = { ArrowRight: i + 1, ArrowLeft: i - 1, Home: 0, End: VIEWS.length - 1 }[e.key];
    if (e.key === "ArrowDown") { e.preventDefault(); focusCard(state.active); return; }
    if (next === undefined) return;
    e.preventDefault();
    selectView(VIEWS[(next + VIEWS.length) % VIEWS.length].id);
    views.querySelector('[aria-selected="true"]').focus();
  });

  function selectView(id) {
    state.view = id;
    state.sort = VIEWS.find((v) => v.id === id).sort;
    renderViews();
    renderFilters();
    apply();
  }

  function select(name, label, options, value) {
    const wrap = el("label");
    wrap.append(el("span", "visually-hidden", label));
    const s = el("select");
    s.name = name;
    Object.entries(options).forEach(([v, text]) => {
      const o = el("option", null, text); o.value = v; o.selected = v === value; s.append(o);
    });
    s.addEventListener("change", () => { state[name] = s.value; apply(); });
    wrap.append(s);
    return wrap;
  }

  function facetOptions(field, anyLabel) {
    const counts = new Map();
    DATA.courses.forEach((c) => counts.set(c[field], (counts.get(c[field]) || 0) + 1));
    const opts = { "": anyLabel };
    [...counts.entries()].filter(([v]) => v !== "unknown").sort((a, b) => b[1] - a[1])
      .forEach(([v, n]) => (opts[v] = `${v[0].toUpperCase()}${v.slice(1)} (${n})`));
    return opts;
  }

  function renderFilters() {
    filters.replaceChildren(
      select("topic", "Topic", Object.fromEntries([["", "All topics"], ...DATA.topics.map((t) => [t.name, `${t.name} (${t.count})`])]), state.topic),
      select("level", "Level", facetOptions("level", "Any level"), state.level),
      select("cost", "Cost", facetOptions("cost", "Any cost"), state.cost),
      select("format", "Format", facetOptions("format", "Any format"), state.format),
      select("era", "Era", ERAS, state.era),
      select("sort", "Sort by", Object.fromEntries(Object.entries(SORTS).map(([k, [label]]) => [k, label])), state.sort),
    );
    if (state.topic || state.level || state.cost || state.format || state.era) {
      const r = el("button", "btn reset", "Clear filters");
      r.type = "button";
      r.addEventListener("click", () => {
        Object.assign(state, { topic: ALL, level: ALL, cost: ALL, format: ALL, era: ALL });
        renderFilters(); apply();
      });
      filters.append(r);
    }
  }

  function matches(c) {
    const v = VIEWS.find((x) => x.id === state.view);
    if (v.test && !v.test(c)) return false;
    if (state.topic && c.topic !== state.topic) return false;
    if (state.level && c.level !== state.level) return false;
    if (state.cost && c.cost !== state.cost) return false;
    if (state.format && c.format !== state.format) return false;
    if (state.era) {
      const y = year(c.first);
      if (state.era === "2000s" ? y >= 2010 : state.era === "2010s" ? y < 2010 || y >= 2020 : y < 2020) return false;
    }
    if (!state.terms.length) return true;
    const hay = (c._hay ||= [c.name, c.provider, c.topic, c.summary, c.why, ...c.tags].join(" ").toLowerCase());
    return state.terms.every((t) => hay.includes(t));
  }

  function apply() {
    state.terms = state.query.toLowerCase().split(/\s+/).filter(Boolean);
    state.list = DATA.courses.filter(matches).sort(SORTS[state.sort][1]);
    state.shown = 0;
    state.active = 0;
    cards = [];
    grid.replaceChildren();
    showMore();
    const bits = [plural(state.list.length, "course")];
    if (state.topic) bits.push(`in ${state.topic}`);
    if (state.terms.length) bits.push(`matching “${state.query}”`);
    status.textContent = `${bits.join(" ")} · sorted by ${SORTS[state.sort][0].toLowerCase()}.`;
    syncHash();
  }

  function makeCard(c, index) {
    const card = el("div", "card");
    card.role = "gridcell";
    card.tabIndex = -1;
    card.dataset.index = index;
    if (seen.has(c.id)) card.classList.add("seen");

    const top = el("div", "card-top");
    top.append(el("span", "rank", `#${c.rank}`), ...badgeEls(c));
    if (saved.has(c.id)) { const s = el("span", "saved-star", "★"); s.title = "Saved"; top.append(s); }

    const h = highlight(el("h3"), c.name, state.terms);
    const prov = el("p", "provider", [c.provider, c.level !== "unknown" && c.level, c.cost !== "unknown" && c.cost]
      .filter(Boolean).join(" · "));
    const why = highlight(el("p", "why"), c.why || c.summary, state.terms);
    const meta = el("div", "meta");
    meta.append(el("span", null, `${plural(c.recommenders, "recommender")} · ${plural(c.threads, "thread")} · ${span(c)}`),
                el("span", null, c.topic));

    card.append(thumb(c, "thumb"), top, h, prov, why, meta);
    card.setAttribute("aria-label",
      `Rank ${c.rank}. ${c.name}, ${c.provider}. ${c.badges.map((b) => BADGE[b][0]).join(", ")}. ` +
      `${plural(c.recommenders, "recommender")}, ${span(c)}.${saved.has(c.id) ? " Saved." : ""}`);
    card.addEventListener("click", () => { setActive(index); openCourse(c.id); });
    return card;
  }

  function showMore() {
    const end = Math.min(state.shown + PAGE, state.list.length);
    for (let i = state.shown; i < end; i++) cards.push(makeCard(state.list[i], i));
    state.shown = end;
    layoutRows();
    if (!state.list.length) {
      const row = el("div"); row.role = "row";
      const e = el("div", "empty", state.view === "saved" && !saved.size
        ? "Nothing saved yet. Press S on any course to keep it here (stored only in this browser)."
        : "No courses match. Clear the filters or the search.");
      e.role = "gridcell";
      row.append(e); grid.replaceChildren(row);
    }
    more.hidden = state.shown >= state.list.length;
    more.textContent = `Show more (${(state.list.length - state.shown).toLocaleString()} left)`;
  }

  // ARIA grids need explicit rows, and the visual column count changes with width.
  function columns() {
    return Math.max(1, getComputedStyle(grid).gridTemplateColumns.split(" ").filter(Boolean).length);
  }

  function layoutRows() {
    state.cols = columns();
    const hadFocus = grid.contains(document.activeElement);
    grid.replaceChildren();
    for (let i = 0; i < cards.length; i += state.cols) {
      const row = el("div"); row.role = "row";
      row.append(...cards.slice(i, i + state.cols));
      grid.append(row);
    }
    cards.forEach((c, i) => (c.tabIndex = i === state.active ? 0 : -1));
    if (hadFocus) focusCard(state.active);
  }

  function setActive(i) {
    if (!cards.length) return;
    i = Math.max(0, Math.min(i, cards.length - 1));
    if (cards[state.active]) cards[state.active].tabIndex = -1;
    state.active = i;
    cards[i].tabIndex = 0;
  }

  function focusCard(i) {
    if (!cards.length) return;
    while (i >= cards.length && state.shown < state.list.length) showMore();
    setActive(i);
    cards[state.active].focus({ preventScroll: true });
    cards[state.active].scrollIntoView({ block: "nearest" });
  }

  function refreshCard(i) {
    if (!cards[i]) return;
    const fresh = makeCard(state.list[i], i);
    fresh.tabIndex = cards[i].tabIndex;
    const hadFocus = document.activeElement === cards[i];
    cards[i].replaceWith(fresh);
    cards[i] = fresh;
    if (hadFocus) fresh.focus({ preventScroll: true });
  }

  function toggleSave(id) {
    if (saved.has(id)) saved.delete(id); else saved.add(id);
    store("hc.saved", [...saved]);
    renderViews();
  }

  grid.addEventListener("keydown", (e) => {
    const card = e.target.closest(".card");
    if (!card || e.altKey || e.metaKey) return;
    const i = Number(card.dataset.index), cols = state.cols;
    const rowStart = i - (i % cols);
    const pageRows = Math.max(1, Math.floor(window.innerHeight / (card.offsetHeight + 14)) - 1);
    let next;
    switch (e.key) {
      case "ArrowRight": next = i + 1; break;
      case "ArrowLeft": next = i - 1; break;
      case "ArrowDown": next = i + cols; break;
      case "ArrowUp":
        if (i < cols) { e.preventDefault(); views.querySelector('[aria-selected="true"]').focus(); return; }
        next = i - cols; break;
      case "Home": next = e.ctrlKey ? 0 : rowStart; break;
      case "End":
        if (e.ctrlKey) { while (state.shown < state.list.length) showMore(); next = cards.length - 1; }
        else next = Math.min(rowStart + cols - 1, cards.length - 1);
        break;
      case "PageDown": next = Math.min(i + cols * pageRows, state.list.length - 1); break;
      case "PageUp": next = Math.max(i - cols * pageRows, i % cols); break;
      case "Enter": case " ": e.preventDefault(); openCourse(state.list[i].id); return;
      case "s": case "S":
        if (e.ctrlKey) return;
        e.preventDefault(); toggleSave(state.list[i].id);
        if (state.view === "saved") { apply(); focusCard(Math.min(i, state.list.length - 1)); } else refreshCard(i);
        return;
      default: return;
    }
    e.preventDefault();
    if (next < 0 || next >= state.list.length) return;
    focusCard(next);
  });

  more.addEventListener("click", () => { const at = state.shown; showMore(); focusCard(at); });

  let resizeTimer;
  window.addEventListener("resize", () => {
    clearTimeout(resizeTimer);
    resizeTimer = setTimeout(() => { if (!listView.hidden && columns() !== state.cols) layoutRows(); }, 120);
  });

  // ---- course page --------------------------------------------------------------------

  function openCourse(id) { location.hash = `#/course/${id}`; }

  function commentBody(text) {
    const body = el("div");
    text.split(/\n{2,}/).forEach((para) => {
      const quoted = /^\s*>/.test(para);
      body.append(el(quoted ? "blockquote" : "p", null, quoted ? para.replace(/^\s*>\s?/gm, "") : para));
    });
    return body;
  }

  function timeline(c) {
    const start = 2006, end = year(DATA.dataEnd);
    const counts = new Array(end - start + 1).fill(0);
    c.endorsements.forEach(([ci, s]) => { if (s >= 2) counts[year(DATA.comments[ci].t) - start]++; });
    const max = Math.max(...counts, 1);
    const wrap = el("section", "timeline");
    wrap.append(el("h2", null, "Recommendations by year"));
    const bars = el("div", "bars");
    bars.setAttribute("role", "img");
    bars.setAttribute("aria-label", counts.map((n, i) => n && `${start + i}: ${n}`).filter(Boolean).join(", "));
    counts.forEach((n, i) => {
      const b = el("span", n ? null : "zero");
      b.style.height = `${n ? Math.max(8, (n / max) * 100) : 3}%`;
      b.title = `${start + i}: ${n}`;
      bars.append(b);
    });
    const years = el("div", "years");
    years.append(el("span", null, String(start)), el("span", null, String(end)));
    wrap.append(bars, years);
    return wrap;
  }

  function renderCourse(c) {
    seen.add(c.id);
    store("hc.seen", [...seen]);
    const pos = state.list.findIndex((x) => x.id === c.id);
    const prev = pos > 0 ? state.list[pos - 1] : null;
    const next = pos >= 0 && pos < state.list.length - 1 ? state.list[pos + 1] : null;

    const crumbs = el("nav", "crumbs");
    crumbs.setAttribute("aria-label", "Course navigation");
    const back = el("a", null, "← All courses"); back.href = "#/";
    const pn = el("span");
    if (prev) { const a = el("a", null, `← ${prev.name}`); a.href = `#/course/${prev.id}`; pn.append(a, " "); }
    if (next) { const a = el("a", null, `${next.name} →`); a.href = `#/course/${next.id}`; pn.append(a); }
    crumbs.append(back, pn);

    const head = el("header", "course-head");
    const tops = el("div", "card-top");
    tops.append(el("span", "rank", `#${c.rank} overall`), ...badgeEls(c));
    const h1 = el("h1", null, c.name); h1.id = "cName";
    head.append(tops, h1, el("p", "provider", c.provider),
      el("p", "statline", `${plural(c.recommenders, "recommender")} · ${plural(c.threads, "thread")} · ` +
        `recommended in ${plural(c.years_active, "year")}, ${span(c)} · score ${c.score.toFixed(1)}`));

    const actions = el("div", "actions");
    if (c.url) {
      const go = el("a", "btn primary", "Go to course ↗"); go.href = c.url; go.target = "_blank"; go.rel = "noopener nofollow";
      actions.append(go);
    } else {
      const find = el("a", "btn primary", "Search for it ↗");
      find.href = `https://duckduckgo.com/?q=${encodeURIComponent(`${c.name} ${c.provider}`)}`;
      find.target = "_blank"; find.rel = "noopener nofollow";
      actions.append(find);
    }
    const sv = el("button", "btn", saved.has(c.id) ? "★ Saved" : "☆ Save");
    sv.type = "button";
    sv.setAttribute("aria-pressed", String(saved.has(c.id)));
    sv.addEventListener("click", () => {
      toggleSave(c.id);
      sv.textContent = saved.has(c.id) ? "★ Saved" : "☆ Save";
      sv.setAttribute("aria-pressed", String(saved.has(c.id)));
    });
    actions.append(sv);

    const facts = el("div", "facts");
    [c.topic, c.level, c.cost, c.format].filter((f) => f && f !== "unknown")
      .forEach((f) => facts.append(el("span", "chip", f)));
    c.tags.forEach((t) => facts.append(el("span", "chip plain", `#${t}`)));

    const list = el("ol", "comments");
    c.endorsements.forEach(([ci, s]) => {
      const cm = DATA.comments[ci];
      const li = el("li", "comment");
      const hd = el("header");
      hd.append(el("span", `stance s${s}`, STANCE[s]), el("strong", null, cm.by), el("span", null, String(year(cm.t))));
      if (cm.thread) hd.append(el("span", "thread", `in “${cm.thread}”`));
      const body = commentBody(cm.text);
      const ft = el("footer");
      if (cm.text.length > 600) {
        body.classList.add("clamped");
        const more = el("button", "link-btn", "Read all");
        more.type = "button";
        more.addEventListener("click", () => { body.classList.remove("clamped"); more.remove(); });
        ft.append(more);
      }
      const a = el("a", null, "Open comment ↗"); a.href = threadUrl(cm.id); a.target = "_blank"; a.rel = "noopener";
      ft.append(a);
      li.append(hd, body, ft);
      list.append(li);
    });

    const rel = el("ul", "related");
    c.related.map((id) => byId.get(id)).filter(Boolean).forEach((r) => {
      const li = el("li"), a = el("a");
      a.href = `#/course/${r.id}`;
      a.append(el("strong", null, r.name), el("span", null, `${r.provider} · ${plural(r.recommenders, "recommender")}`));
      li.append(a); rel.append(li);
    });

    const hero = el("figure", "hero");
    hero.append(thumb(c, "hero-img"));
    if (c.img && c.imgPage) {
      const cap = el("figcaption");
      const src = el("a", null, new URL(c.imgPage).hostname.replace(/^www\./, ""));
      src.href = c.imgPage; src.target = "_blank"; src.rel = "noopener nofollow";
      cap.append("Image: ", src);
      hero.append(cap);
    }

    courseView.replaceChildren(crumbs, hero, head, actions,
      el("p", "lede", c.summary), el("p", "why-long", c.why), facts, timeline(c),
      el("h2", "section-h", `What commenters said (${c.endorsements.length})`), list);
    if (rel.children.length) courseView.append(el("h2", "section-h", "Related courses"), rel);
    document.title = `${c.name} · Hacker Courses`;
  }

  // ---- routing ------------------------------------------------------------------------

  function syncHash() {
    // Keep the list view's hash bare so Back from a course returns to the same list.
    if (!location.hash.startsWith("#/course/") && location.hash !== "" && location.hash !== "#/") {
      history.replaceState(null, "", "#/");
    }
  }

  function route() {
    const m = location.hash.match(/^#\/course\/(\d+)/);
    const c = m && byId.get(Number(m[1]));
    if (c) {
      listView.hidden = true;
      courseView.hidden = false;
      renderCourse(c);
      window.scrollTo(0, 0);
      courseView.focus({ preventScroll: true });
    } else {
      const wasHidden = listView.hidden;
      courseView.hidden = true;
      listView.hidden = false;
      document.title = "Hacker Courses";
      if (wasHidden) {
        // Returning from a course: mark it seen in place and restore focus.
        const lastId = Number((sessionStorage.getItem("hc.last") || "-1"));
        const i = state.list.findIndex((x) => x.id === lastId);
        if (i >= 0) { refreshCard(i); focusCard(i); } else layoutRows();
      }
    }
    if (c) try { sessionStorage.setItem("hc.last", String(c.id)); } catch { /* ignore */ }
  }
  window.addEventListener("hashchange", route);

  courseView.addEventListener("keydown", (e) => {
    if (e.altKey || e.ctrlKey || e.metaKey) return;
    if (e.target.closest("button, a, input, select") && (e.key === "Enter" || e.key === " ")) return;
    const id = Number(location.hash.split("/")[2]);
    const pos = state.list.findIndex((x) => x.id === id);
    if (e.key === "Escape" || e.key === "Backspace") { e.preventDefault(); location.hash = "#/"; }
    else if (e.key === "ArrowRight" && pos >= 0 && pos < state.list.length - 1) { e.preventDefault(); openCourse(state.list[pos + 1].id); state.active = pos + 1; }
    else if (e.key === "ArrowLeft" && pos > 0) { e.preventDefault(); openCourse(state.list[pos - 1].id); state.active = pos - 1; }
    else if (e.key === "o" || e.key === "O") { const go = courseView.querySelector(".btn.primary"); if (go) window.open(go.href, "_blank", "noopener"); }
    else if (e.key === "s" || e.key === "S") { courseView.querySelector(".actions button")?.click(); }
  });

  // ---- global shortcuts ---------------------------------------------------------------

  let qTimer;
  function flushQuery() {
    clearTimeout(qTimer);
    if (q.value.trim() !== state.query) { state.query = q.value.trim(); apply(); }
  }
  q.addEventListener("input", () => { clearTimeout(qTimer); qTimer = setTimeout(flushQuery, 150); });
  q.addEventListener("focus", () => { if (listView.hidden) location.hash = "#/"; });
  q.addEventListener("keydown", (e) => {
    if (e.key === "Enter" || e.key === "ArrowDown") { e.preventDefault(); flushQuery(); focusCard(0); }
    if (e.key === "Escape") { q.value = ""; flushQuery(); focusCard(0); }
  });

  function toggleTheme() {
    const dark = document.documentElement.dataset.theme
      ? document.documentElement.dataset.theme === "dark"
      : matchMedia("(prefers-color-scheme: dark)").matches;
    document.documentElement.dataset.theme = dark ? "light" : "dark";
    store("hc.theme", document.documentElement.dataset.theme);
  }

  $("themeBtn").addEventListener("click", toggleTheme);
  $("helpBtn").addEventListener("click", () => help.showModal());
  $("hClose").addEventListener("click", () => help.close());
  $("aboutBtn").addEventListener("click", () => about.showModal());
  $("aClose").addEventListener("click", () => about.close());
  document.querySelector(".skip").addEventListener("click", (e) => {
    e.preventDefault();
    if (listView.hidden) courseView.focus(); else focusCard(state.active);
  });

  document.addEventListener("keydown", (e) => {
    if (help.open || about.open || e.ctrlKey || e.metaKey || e.altKey) return;
    if (e.target.closest("input, select, textarea")) return;
    if (e.key === "/") { e.preventDefault(); q.focus(); q.select(); }
    else if (e.key === "?") { e.preventDefault(); help.showModal(); }
    else if (e.key === "t" || e.key === "T") toggleTheme();
    else if (listView.hidden) return;
    else if (/^[1-5]$/.test(e.key)) { selectView(VIEWS[Number(e.key) - 1].id); focusCard(0); }
    else if (e.key === "]" || e.key === "[") {
      const names = ["", ...DATA.topics.map((t) => t.name)];
      const i = names.indexOf(state.topic);
      state.topic = names[(i + (e.key === "]" ? 1 : -1) + names.length) % names.length];
      renderFilters(); apply(); focusCard(0);
    }
  });

  // ---- boot -----------------------------------------------------------------------------

  $("summary").textContent =
    `${DATA.courses.length.toLocaleString()} courses programmers keep recommending, ranked from ` +
    `${DATA.comments.length.toLocaleString()} comments, 2006–${year(DATA.dataEnd)}.`;
  renderViews();
  renderFilters();
  apply();
  route();
})();
