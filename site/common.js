// Shared by every page. Loaded in <head> so the saved theme applies before first paint.
(() => {
  "use strict";

  // Per-viewer storage: browser only, never required to render.
  function load(key, fallback, area = "local") {
    try {
      const v = (area === "session" ? sessionStorage : localStorage).getItem(key);
      return v ? JSON.parse(v) : fallback;
    } catch { return fallback; }
  }
  function store(key, value, area = "local") {
    try { (area === "session" ? sessionStorage : localStorage).setItem(key, JSON.stringify(value)); } catch { /* private mode */ }
  }

  const theme = load("hc.theme", null);
  if (theme) document.documentElement.dataset.theme = theme;

  function toggleTheme() {
    const root = document.documentElement;
    const dark = root.dataset.theme ? root.dataset.theme === "dark" : matchMedia("(prefers-color-scheme: dark)").matches;
    root.dataset.theme = dark ? "light" : "dark";
    store("hc.theme", root.dataset.theme);
  }

  const saved = () => new Set(load("hc.saved", []));
  function toggleSaved(id) {
    const s = saved();
    if (s.has(id)) s.delete(id); else s.add(id);
    store("hc.saved", [...s]);
    return s.has(id);
  }

  // Which source the visitor last chose (Hacker News or Reddit). Anything unexpected means "hn".
  const source = () => (load("hc.source", "hn") === "reddit" ? "reddit" : "hn");

  window.HC = { load, store, toggleTheme, saved, toggleSaved, source };

  // Remember the choice before navigating. Capture phase, so it runs even if a page handler stops the click.
  document.addEventListener("click", (e) => {
    const a = e.target instanceof Element && e.target.closest(".source-switch a");
    if (a && a.dataset.source) store("hc.source", a.dataset.source);
  }, true);

  // Only the home page redirects; /reddit/ never does, so the switch back to Hacker News cannot loop.
  if (location.pathname === "/" && source() === "reddit") location.replace("/reddit/" + location.search);

  // Pre-rendered cards (topic pages, the grid before app.js runs) swap a broken remote image
  // for their topic illustration. Image errors don't bubble, so listen in the capture phase.
  document.addEventListener("error", (e) => {
    const img = e.target;
    const box = img instanceof HTMLImageElement && img.closest(".thumb");
    if (box && img.dataset.fallback && !box.classList.contains("art")) {
      box.classList.add("art");
      img.src = img.dataset.fallback;
    }
  }, true);

  document.addEventListener("DOMContentLoaded", () => {
    const help = document.getElementById("help");
    const q = document.getElementById("q");
    document.getElementById("themeBtn")?.addEventListener("click", toggleTheme);
    document.getElementById("helpBtn")?.addEventListener("click", () => help.showModal());
    document.getElementById("hClose")?.addEventListener("click", () => help.close());

    document.addEventListener("keydown", (e) => {
      if (help?.open || e.ctrlKey || e.metaKey || e.altKey) return;
      if (e.target.closest("input, select, textarea")) return;
      if (e.key === "/") { e.preventDefault(); q.focus(); q.select(); }
      else if (e.key === "?") { e.preventDefault(); help.showModal(); }
      else if (e.key === "t" || e.key === "T") toggleTheme();
    });
  });
})();
