// The course grid (home page). Course pages are separate, pre-rendered pages.
(() => {
  "use strict";

  const DATA = window.HACKER_COURSES || { topics: [], courses: [], comments: 0 };
  const SOURCE = DATA.source === "reddit" ? "reddit" : "hn";
  const PAGE = 60;
  const ALL = "";
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
  const FILTERS = ["topic", "level", "cost", "format", "era"];

  const $ = (id) => document.getElementById(id);
  const grid = $("grid"), views = $("views"), filters = $("filters"), status = $("status"), more = $("more"), q = $("q");

  let saved = HC.saved();
  const seen = new Set(HC.load("hc.seen", []));

  // ---- helpers ----------------------------------------------------------------------

  const year = (t) => new Date(t * 1000).getUTCFullYear();
  const span = (c) => (year(c.first) === year(c.last) ? `${year(c.first)}` : `${year(c.first)}–${year(c.last)}`);
  const plural = (n, w) => `${n.toLocaleString()} ${w}${n === 1 ? "" : "s"}`;
  const courseUrl = (c) => `/course/${c.slug}/`;
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
    `/img/topics/${topic.toLowerCase().replace("&", "and").replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "")}.svg`;

  // The course's own preview image when it has one, else its topic illustration.
  // Remote images are hotlinked without a referrer and swap to the illustration if they fail.
  function thumb(c) {
    const box = el("div", "thumb");
    const img = el("img");
    img.alt = "";
    img.loading = "lazy";
    img.decoding = "async";
    img.referrerPolicy = "no-referrer";
    img.src = c.img || topicArt(c.topic);
    if (!c.img) box.classList.add("art");
    else if (c.imgTall) box.classList.add("tall");
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

  // ---- state ------------------------------------------------------------------------

  const state = { view: "best", topic: ALL, level: ALL, cost: ALL, format: ALL, era: ALL, sort: "score",
                  query: "", terms: [], list: [], shown: 0, active: 0, cols: 1 };
  let cards = [];

  // Remember the grid across course pages so Back/Esc returns to the same list and card,
  // and course pages can step through this list with ← →.
  function remember(activeSlug) {
    HC.store("hc.grid", {
      source: SOURCE,
      view: state.view, sort: state.sort, query: state.query,
      ...Object.fromEntries(FILTERS.map((f) => [f, state[f]])),
      slugs: state.list.map((c) => c.slug), names: state.list.map((c) => c.name),
      active: activeSlug ?? state.list[state.active]?.slug,
    }, "session");
  }

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
    if (FILTERS.some((f) => state[f])) {
      const r = el("button", "btn reset", "Clear filters");
      r.type = "button";
      r.addEventListener("click", () => { FILTERS.forEach((f) => (state[f] = ALL)); renderFilters(); apply(); });
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
    remember();
  }

  // ---- cards ------------------------------------------------------------------------

  function makeCard(c, index) {
    const card = el("div", "card");
    card.role = "gridcell";
    card.tabIndex = -1;
    card.dataset.index = index;
    if (seen.has(c.id)) card.classList.add("seen");

    const top = el("div", "card-top");
    top.append(el("span", "rank", `#${c.rank}`), ...badgeEls(c));
    if (saved.has(c.id)) { const s = el("span", "saved-star", "★"); s.title = "Saved"; top.append(s); }

    // A real link (for crawlers, middle-click, copy link); the card itself handles keys.
    const h = el("h3");
    const a = el("a");
    a.href = courseUrl(c);
    a.tabIndex = -1;
    highlight(a, c.name, state.terms);
    h.append(a);
    const prov = el("p", "provider", [c.provider, c.level !== "unknown" && c.level, c.cost !== "unknown" && c.cost]
      .filter(Boolean).join(" · "));
    const why = highlight(el("p", "why"), c.why || c.summary, state.terms);
    const meta = el("div", "meta");
    meta.append(el("span", null, `${plural(c.recommenders, "recommender")} · ${plural(c.threads, "thread")} · ${span(c)}`),
                el("span", null, c.topic));

    card.append(thumb(c), top, h, prov, why, meta);
    card.setAttribute("aria-label",
      `Rank ${c.rank}. ${c.name}, ${c.provider}. ${c.badges.map((b) => BADGE[b][0]).join(", ")}. ` +
      `${plural(c.recommenders, "recommender")}, ${span(c)}.${saved.has(c.id) ? " Saved." : ""}`);
    card.addEventListener("click", (e) => {
      if (e.target.closest("a")) { remember(c.slug); return; }  // let the link (or middle-click) work
      setActive(index); open(c);
    });
    return card;
  }

  function open(c) { remember(c.slug); location.href = courseUrl(c); }

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
      case "Enter": case " ": e.preventDefault(); open(state.list[i]); return;
      case "s": case "S":
        if (e.ctrlKey) return;
        e.preventDefault();
        HC.toggleSaved(state.list[i].id);
        saved = HC.saved();
        renderViews();
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
    resizeTimer = setTimeout(() => { if (columns() !== state.cols) layoutRows(); }, 120);
  });

  // ---- search & shortcuts -----------------------------------------------------------

  let qTimer;
  function flushQuery() {
    clearTimeout(qTimer);
    if (q.value.trim() !== state.query) { state.query = q.value.trim(); apply(); }
  }
  q.form.addEventListener("submit", (e) => { e.preventDefault(); flushQuery(); focusCard(0); });
  q.addEventListener("input", () => { clearTimeout(qTimer); qTimer = setTimeout(flushQuery, 150); });
  q.addEventListener("keydown", (e) => {
    if (e.key === "ArrowDown") { e.preventDefault(); flushQuery(); focusCard(0); }
    if (e.key === "Escape") { q.value = ""; flushQuery(); focusCard(0); }
  });

  document.querySelector(".skip").addEventListener("click", (e) => { e.preventDefault(); focusCard(state.active); });

  document.addEventListener("keydown", (e) => {
    if ($("help").open || e.ctrlKey || e.metaKey || e.altKey) return;
    if (e.target.closest("input, select, textarea")) return;
    if (/^[1-5]$/.test(e.key)) { selectView(VIEWS[Number(e.key) - 1].id); focusCard(0); }
    else if (e.key === "]" || e.key === "[") {
      const names = ["", ...DATA.topics.map((t) => t.name)];
      const i = names.indexOf(state.topic);
      state.topic = names[(i + (e.key === "]" ? 1 : -1) + names.length) % names.length];
      renderFilters(); apply(); focusCard(0);
    }
  });

  // Returning from a course page via Back restores the page from cache; re-sync saved/seen marks.
  window.addEventListener("pageshow", (e) => {
    if (!e.persisted) return;
    saved = HC.saved();
    HC.load("hc.seen", []).forEach((id) => seen.add(id));
    renderViews();
    cards.forEach((_, i) => refreshCard(i));
    restoreFocus();
  });

  function restoreFocus() {
    const back = HC.load("hc.grid", null, "session");
    const i = back?.active ? state.list.findIndex((c) => c.slug === back.active) : -1;
    if (i >= 0) focusCard(i);
  }

  // ---- boot -------------------------------------------------------------------------

  $("summary").textContent = SOURCE === "reddit"
    ? `${DATA.courses.length.toLocaleString()} courses Redditors keep recommending, ranked from ` +
      `${DATA.comments.toLocaleString()} comments, ${DATA.dataStart ? `${year(DATA.dataStart)}–` : ""}${year(DATA.dataEnd)}.`
    : `${DATA.courses.length.toLocaleString()} courses programmers keep recommending, ranked from ` +
      `${DATA.comments.toLocaleString()} comments, 2006–${year(DATA.dataEnd)}.`;

  const params = new URLSearchParams(location.search);
  const lastGrid = HC.load("hc.grid", null, "session");
  // Another source's list (different slugs) must not be restored here.
  const back = lastGrid && (lastGrid.source || "hn") === SOURCE ? lastGrid : null;
  if (params.has("q")) {
    state.query = params.get("q").trim();
  } else if (back) {
    // Coming back to the grid in the same tab: restore the list the visitor left.
    Object.assign(state, { view: back.view || "best", sort: back.sort || "score", query: back.query || "" },
      Object.fromEntries(FILTERS.map((f) => [f, back[f] || ALL])));
  }
  q.value = state.query;
  renderViews();
  renderFilters();
  const activeSlug = back?.active;
  apply();
  if (activeSlug && !params.has("q")) {
    const i = state.list.findIndex((c) => c.slug === activeSlug);
    if (i >= 0) focusCard(i);
  }
})();
