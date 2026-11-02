// Course pages are pre-rendered; this adds saving, keys and image fallback.
(() => {
  "use strict";

  const main = document.querySelector(".course-page");
  if (!main) return;
  const id = Number(main.dataset.id);
  const slug = main.dataset.slug;

  // Seen markers dim the card in the grid.
  const seen = new Set(HC.load("hc.seen", []));
  seen.add(id);
  HC.store("hc.seen", [...seen]);

  const save = document.getElementById("saveBtn");
  const paint = (on) => {
    save.textContent = on ? "★ Saved" : "☆ Save";
    save.setAttribute("aria-pressed", String(on));
  };
  paint(HC.saved().has(id));
  save.addEventListener("click", () => paint(HC.toggleSaved(id)));

  // Previous / next follow the list the visitor came from (filters, search, sort),
  // falling back to the overall ranking baked into the page.
  const grid = HC.load("hc.grid", null, "session");
  const list = grid?.slugs || [];
  const pos = list.indexOf(slug);
  const prevNext = document.getElementById("prevNext");
  if (pos >= 0) {
    const titles = grid.names || [];
    prevNext.replaceChildren();
    const link = (s, text) => { const a = document.createElement("a"); a.href = `/course/${s}/`; a.textContent = text; return a; };
    if (pos > 0) { const a = link(list[pos - 1], `← ${titles[pos - 1] || "Previous"}`); a.id = "prevLink"; prevNext.append(a, " "); }
    if (pos < list.length - 1) { const a = link(list[pos + 1], `${titles[pos + 1] || "Next"} →`); a.id = "nextLink"; prevNext.append(a); }
  }
  const go = (s) => {
    if (grid && pos >= 0) { grid.active = s; HC.store("hc.grid", grid, "session"); }
    location.href = `/course/${s}/`;
  };

  function backToGrid() {
    if (grid) { grid.active = slug; HC.store("hc.grid", grid, "session"); }
    // The grid the visitor came from; else the home the page's own back link names ("/" or "/reddit/").
    const home = grid?.source === "reddit" ? "/reddit/" : grid?.source === "hn" ? "/"
      : document.getElementById("backLink").getAttribute("href");
    const ref = document.referrer && new URL(document.referrer);
    const fromGrid = ref && ref.origin === location.origin && (ref.pathname === "/" || ref.pathname === "/reddit/");
    if (fromGrid && history.length > 1) history.back(); else location.href = home;
  }
  document.getElementById("backLink").addEventListener("click", (e) => { e.preventDefault(); backToGrid(); });

  document.addEventListener("keydown", (e) => {
    if (e.altKey || e.ctrlKey || e.metaKey || document.getElementById("help")?.open) return;
    if (e.target.closest("input, select, textarea")) return;
    if (e.target.closest("button, a") && (e.key === "Enter" || e.key === " ")) return;
    const prev = document.getElementById("prevLink"), next = document.getElementById("nextLink");
    if (e.key === "Escape" || e.key === "Backspace") { e.preventDefault(); backToGrid(); }
    else if (e.key === "ArrowRight" && next) { e.preventDefault(); go(next.pathname.split("/")[2]); }
    else if (e.key === "ArrowLeft" && prev) { e.preventDefault(); go(prev.pathname.split("/")[2]); }
    else if (e.key === "s" || e.key === "S") save.click();
    else if (e.key === "o" || e.key === "O") window.open(document.getElementById("goBtn").href, "_blank", "noopener");
  });

  document.querySelectorAll(".read-more").forEach((b) => b.addEventListener("click", () => {
    b.closest(".comment").querySelector(".clamped")?.classList.remove("clamped");
    b.remove();
  }));

  const hero = document.querySelector(".hero-img img");
  hero?.addEventListener("error", () => {
    if (!hero.parentElement.classList.contains("art")) {
      hero.parentElement.classList.add("art");
      hero.src = hero.dataset.fallback;
      document.querySelector(".hero figcaption")?.remove();
    }
  });

  main.focus({ preventScroll: true });
})();
