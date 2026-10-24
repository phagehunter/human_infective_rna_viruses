/* Human-Infective RNA Viruses — catalogue browser, no dependencies.
 *
 * The page is rendered by build.py and every aggregate number in it is already
 * correct before this script runs. This file adds search, filtering and the
 * detail dialog, and keeps the current view in the URL so a filtered catalogue
 * can be linked to.
 */
(function () {
  "use strict";

  var $ = function (id) { return document.getElementById(id); };
  var cards = $("cards"), countEl = $("count"), emptyEl = $("empty"), failedEl = $("failed");
  if (!cards) return;

  var fQ = $("f-q"), fFamily = $("f-family"), fGenome = $("f-genome"),
      fRoute = $("f-route"), fLevel = $("f-level"), fReset = $("f-reset");

  var DATA = [];
  var view = [];
  var PAGE = 60;
  var shown = PAGE;

  var LEVEL_TEXT = {
    "2": "limited onward transmission between humans",
    "3": "longer chains of transmission between humans",
    "4a": "sustained human-to-human transmission, with an animal reservoir",
    "4b": "sustained human-to-human transmission, no animal reservoir needed"
  };

  /* ---- helpers ---- */

  function esc(s) {
    return String(s === null || s === undefined ? "" : s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }
  function fold(s) {
    return (s || "").normalize("NFKD").replace(/[̀-ͯ]/g, "").toLowerCase();
  }
  function num(v) { return Number(v).toLocaleString(); }
  function routesOf(rec) {
    var out = [];
    if (rec.vector) out.push("Vector");
    Object.keys(rec.routes).forEach(function (k) { if (rec.routes[k]) out.push(k); });
    return out;
  }
  function hostsOf(rec) {
    return Object.keys(rec.hosts).filter(function (k) { return rec.hosts[k]; });
  }
  function marked(rec, label) {
    return rec.sourceMarked && rec.sourceMarked.indexOf(label) !== -1;
  }

  /* ---- filtering ---- */

  function readControls() {
    return {
      q: fold(fQ.value.trim()),
      family: fFamily.value,
      genome: fGenome.value,
      route: fRoute.value,
      level: fLevel.value
    };
  }

  function matches(rec, f) {
    if (f.family !== "ALL" && rec.family !== f.family) return false;
    if (f.genome !== "ALL" && rec.genome !== f.genome) return false;
    if (f.level !== "ALL" && rec.transmissionLevel !== f.level) return false;
    if (f.route !== "ALL" && routesOf(rec).indexOf(f.route) === -1) return false;
    if (f.q && rec._hay.indexOf(f.q) === -1) return false;
    return true;
  }

  function apply(pushUrl) {
    var f = readControls();
    view = DATA.filter(function (r) { return matches(r, f); });
    shown = PAGE;
    renderCards();
    if (pushUrl !== false) syncUrl(f);
  }

  /* ---- rendering ---- */

  function cardHtml(rec) {
    var lv = rec.transmissionLevel;
    var tag = lv ? '<span class="tag l' + esc(lv) + '"><span class="dot"></span>Level ' + esc(lv) + "</span>" : "";
    var bits = [];
    if (rec.genome) bits.push("<span>" + esc(rec.genome) + "</span>");
    if (rec.country) bits.push("<span>" + esc(rec.country) + "</span>");
    if (rec.year) bits.push("<span>" + esc(rec.year) + "</span>");
    if (rec.spillover) bits.push('<span>SpillOver ' + esc(rec.spillover.score) + "</span>");
    return '<button type="button" class="card" data-i="' + rec._i + '">' +
      tag +
      '<span class="cname">' + esc(rec.name) + "</span>" +
      '<span class="csp">' + esc(rec.species) + "</span>" +
      '<span class="cmeta">' + bits.join("") + "</span>" +
      "</button>";
  }

  function renderCards() {
    var slice = view.slice(0, shown);
    cards.innerHTML = slice.map(cardHtml).join("");
    emptyEl.hidden = view.length !== 0;
    if (view.length > shown) {
      var more = document.createElement("button");
      more.type = "button";
      more.className = "btn ghost";
      more.style.margin = "16px auto 0";
      more.style.display = "block";
      more.textContent = "Show " + num(Math.min(PAGE, view.length - shown)) + " more of " +
        num(view.length - shown) + " remaining";
      more.addEventListener("click", function () {
        shown += PAGE;
        renderCards();
        var next = cards.querySelectorAll(".card")[slice.length];
        if (next) next.focus();
      });
      cards.appendChild(more);
    }
    countEl.innerHTML = view.length === DATA.length
      ? "Showing all <b>" + num(DATA.length) + "</b> species."
      : "<b>" + num(view.length) + "</b> of " + num(DATA.length) +
        (view.length === 1 ? " species matches" : " species match") + " these filters.";
  }

  /* ---- detail dialog ---- */

  var backdrop = $("detail"), panel = $("detail-panel"), body = $("d-body"),
      closeBtn = $("d-close"), lastFocus = null;

  function pill(label, on, rec) {
    var mark = marked(rec, label) ? ' <span class="mark" title="Marked with an asterisk in the source">*</span>' : "";
    return '<span class="pill' + (on ? " on" : "") + '">' + esc(label) + mark + "</span>";
  }

  function pubmedLinks(ids) {
    if (!ids || !ids.length) return "";
    return ids.map(function (id) {
      return '<a class="pill" href="https://pubmed.ncbi.nlm.nih.gov/' + esc(id) + '/" rel="noopener">PMID ' +
        esc(id) + "</a>";
    }).join(" ");
  }

  function openDetail(rec) {
    var lv = rec.transmissionLevel;
    var h = "";
    h += '<h2 id="d-name">' + esc(rec.name) + "</h2>";
    h += '<p class="d-species">' + esc(rec.species) + "</p>";
    if (lv) {
      h += '<span class="tag l' + esc(lv) + '"><span class="dot"></span>Level ' + esc(lv) + "</span> " +
        '<span style="color:var(--ink-dim);font-size:.9rem">' + esc(LEVEL_TEXT[lv] || "") +
        (marked(rec, "Transmission level") ? " (marked in the source)" : "") + "</span>";
    }

    h += '<dl class="d-grid">';
    h += "<div><dt>Family</dt><dd>" + esc(rec.family || "not recorded") + "</dd></div>";
    h += "<div><dt>Genus</dt><dd>" + esc(rec.genus || "not recorded") + "</dd></div>";
    h += "<div><dt>Genome</dt><dd>" + esc(rec.genome || "not recorded") + "</dd></div>";
    h += "<div><dt>Envelope</dt><dd>" +
      (rec.enveloped === null ? "not recorded" : (rec.enveloped ? "enveloped" : "non-enveloped")) + "</dd></div>";
    h += "<div><dt>First human report</dt><dd>" + esc(rec.year || "not recorded") + "</dd></div>";
    h += "<div><dt>Reported from</dt><dd>" + esc(rec.country || "not recorded") +
      (rec.region ? " <span style=\"color:var(--muted)\">· " + esc(rec.region) + "</span>" : "") + "</dd></div>";
    h += "<div><dt>Reference sequence</dt><dd>" +
      (rec.seqId
        ? '<a href="https://www.ncbi.nlm.nih.gov/nuccore/' + esc(rec.seqId) + '" rel="noopener">' +
          esc(rec.seqId) + "</a>"
        : "none in the source") + "</dd></div>";
    if (rec.spillover) {
      h += "<div><dt>SpillOver risk</dt><dd>" + esc(rec.spillover.score) +
        (rec.spillover.rank ? ' <span style="color:var(--muted)">· rank ' + esc(rec.spillover.rank) + "</span>" : "") +
        "</dd></div>";
    }
    h += "</dl>";

    var routes = routesOf(rec);
    h += "<h3>Transmission routes</h3>";
    if (routes.length) {
      h += '<div class="pills">' + routes.map(function (r) { return pill(r, true, rec); }).join("") + "</div>";
      if (rec.vectorOrder) {
        h += '<p class="d-note">Vector order: ' + esc(rec.vectorOrder) +
          (marked(rec, "Vector order") ? " (marked in the source)" : "") + ".</p>";
      }
    } else {
      h += '<p class="d-note">No route recorded in the source. That is an absence of recorded evidence, ' +
        "not evidence that no route exists.</p>";
    }

    var hosts = hostsOf(rec);
    h += "<h3>Host range</h3>";
    h += hosts.length
      ? '<div class="pills">' + hosts.map(function (x) { return pill(x, true, rec); }).join("") + "</div>"
      : '<p class="d-note">No host category recorded in the source.</p>';

    h += "<h3>Cited literature</h3><div class=\"pills\">";
    h += pubmedLinks(rec.refs.discovery);
    h += pubmedLinks(rec.refs.transmissionLevel.filter(function (x) {
      return rec.refs.discovery.indexOf(x) === -1;
    }));
    h += "</div>";

    h += '<div class="d-links">';
    if (rec.ictvId) {
      h += '<a class="pill" href="https://ictv.global/taxonomy/taxondetails?taxnode_id=' + esc(rec.ictvId) +
        '" rel="noopener">ICTV taxonomy</a>';
    }
    h += "</div>";

    if (rec.sourceMarked && rec.sourceMarked.length) {
      h += '<p class="d-note">The source marks ' + esc(rec.sourceMarked.join(", ")) +
        " with an asterisk for this species. The dataset does not define what the mark means, so the " +
        "value is shown as recorded.</p>";
    }

    body.innerHTML = h;
    lastFocus = document.activeElement;
    backdrop.hidden = false;
    document.body.style.overflow = "hidden";
    closeBtn.focus();
    document.addEventListener("keydown", onKey, true);
  }

  function closeDetail() {
    if (backdrop.hidden) return;
    backdrop.hidden = true;
    document.body.style.overflow = "";
    document.removeEventListener("keydown", onKey, true);
    if (lastFocus && lastFocus.focus) lastFocus.focus();
    lastFocus = null;
  }

  function onKey(ev) {
    if (ev.key === "Escape") { ev.preventDefault(); closeDetail(); return; }
    if (ev.key !== "Tab") return;
    // Keep focus inside the dialog while it is open.
    var items = panel.querySelectorAll('a[href], button, [tabindex]:not([tabindex="-1"])');
    if (!items.length) return;
    var first = items[0], last = items[items.length - 1];
    if (ev.shiftKey && document.activeElement === first) { ev.preventDefault(); last.focus(); }
    else if (!ev.shiftKey && document.activeElement === last) { ev.preventDefault(); first.focus(); }
  }

  closeBtn.addEventListener("click", closeDetail);
  backdrop.addEventListener("mousedown", function (ev) {
    if (ev.target === backdrop) closeDetail();
  });

  cards.addEventListener("click", function (ev) {
    var b = ev.target.closest(".card");
    if (!b) return;
    var rec = DATA[Number(b.getAttribute("data-i"))];
    if (rec) openDetail(rec);
  });

  /* ---- URL state ---- */

  function syncUrl(f) {
    var u = new URL(location.href);
    var p = u.searchParams;
    [["q", fQ.value.trim()], ["family", f.family], ["genome", f.genome],
     ["route", f.route], ["level", f.level]].forEach(function (kv) {
      if (kv[1] && kv[1] !== "ALL") p.set(kv[0], kv[1]); else p.delete(kv[0]);
    });
    history.replaceState(null, "", u);
  }

  function readUrl() {
    var p = new URL(location.href).searchParams;
    if (p.get("q")) fQ.value = p.get("q");
    [["family", fFamily], ["genome", fGenome], ["route", fRoute], ["level", fLevel]].forEach(function (kv) {
      var want = p.get(kv[0]);
      if (!want) return;
      var opt = Array.prototype.find.call(kv[1].options, function (o) { return o.value === want; });
      if (opt) kv[1].value = want;
    });
  }

  /* ---- start-up ---- */

  function fillSelect(sel, values, labeller) {
    values.forEach(function (v) {
      var o = document.createElement("option");
      o.value = v;
      o.textContent = labeller ? labeller(v) : v;
      sel.appendChild(o);
    });
  }

  function start(records) {
    DATA = records;
    DATA.forEach(function (r, i) {
      r._i = i;
      r._hay = fold([r.name, r.species, r.genus, r.family, r.country, r.region].join(" "));
    });

    var families = {}, genomes = {}, routes = {}, levels = {};
    DATA.forEach(function (r) {
      if (r.family) families[r.family] = (families[r.family] || 0) + 1;
      if (r.genome) genomes[r.genome] = (genomes[r.genome] || 0) + 1;
      if (r.transmissionLevel) levels[r.transmissionLevel] = (levels[r.transmissionLevel] || 0) + 1;
      routesOf(r).forEach(function (x) { routes[x] = (routes[x] || 0) + 1; });
    });
    var byCount = function (o) {
      return Object.keys(o).sort(function (a, b) { return o[b] - o[a] || a.localeCompare(b); });
    };

    fillSelect(fFamily, byCount(families), function (v) { return v + " (" + families[v] + ")"; });
    fillSelect(fGenome, byCount(genomes), function (v) { return v + " (" + genomes[v] + ")"; });
    fillSelect(fRoute, byCount(routes), function (v) { return v + " (" + routes[v] + ")"; });
    fillSelect(fLevel, Object.keys(levels).sort(), function (v) {
      return "Level " + v + " (" + levels[v] + ")";
    });

    readUrl();
    apply(false);

    var t;
    fQ.addEventListener("input", function () {
      clearTimeout(t);
      t = setTimeout(apply, 120);
    });
    [fFamily, fGenome, fRoute, fLevel].forEach(function (s) {
      s.addEventListener("change", function () { apply(); });
    });
    fReset.addEventListener("click", reset);
    var er = $("empty-reset");
    if (er) er.addEventListener("click", reset);
    $("filters").addEventListener("submit", function (ev) { ev.preventDefault(); apply(); });
  }

  function reset() {
    fQ.value = "";
    [fFamily, fGenome, fRoute, fLevel].forEach(function (s) { s.value = "ALL"; });
    apply();
    fQ.focus();
  }

  fetch("data/viruses.json", { cache: "no-cache" })
    .then(function (r) {
      if (!r.ok) throw new Error("HTTP " + r.status);
      return r.json();
    })
    .then(start)
    .catch(function () {
      countEl.textContent = "";
      failedEl.hidden = false;
    });
})();
