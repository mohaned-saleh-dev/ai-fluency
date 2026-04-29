(function () {
  const $ = (s) => document.querySelector(s);
  const msgBox = $("#msgBox");
  const stepIntro = $("#step-intro");
  const stepChat = $("#step-chat");
  const stepResults = $("#step-results");
  const endModal = $("#endModal");
  const sessionState = {
    id: null,
    t0: null,
    interval: null,
    lastDimCode: null,
    assessment: null,
    wrapCtaActive: false,
  };
  /** Persisted so reload / new tab / recovery after errors can continue the same server session. */
  const STORAGE_KEY = "aiq_csuite_active_session";
  let wrapCtaCountdown = null;

  function persistActiveSession(sid) {
    if (!sid) return;
    try {
      localStorage.setItem(STORAGE_KEY, sid);
      const u = new URL(location.href);
      u.searchParams.set("session", sid);
      history.replaceState({}, "", u.pathname + u.search + (u.hash || ""));
    } catch (_) {}
  }

  function clearActiveSession() {
    try {
      localStorage.removeItem(STORAGE_KEY);
      const u = new URL(location.href);
      if (u.searchParams.has("session")) {
        u.searchParams.delete("session");
        history.replaceState({}, "", u.pathname + (u.search || "") + (u.hash || ""));
      }
    } catch (_) {}
  }

  async function tryResumeOnLoad() {
    const params = new URLSearchParams(location.search);
    let sid = (params.get("session") || "").trim();
    if (!sid) {
      try {
        sid = (localStorage.getItem(STORAGE_KEY) || "").trim();
      } catch (_) {}
    }
    if (!sid) return false;
    let st;
    try {
      st = await apiGet("/api/session/" + encodeURIComponent(sid));
    } catch (_) {
      clearActiveSession();
      return false;
    }
    if (st.ended || !st.messages || !st.messages.length) {
      clearActiveSession();
      if (st.ended) {
        const berr = $("#startErr");
        if (berr) {
          showErr(
            berr,
            "That session already ended (results were finalized). Start a new assessment below."
          );
        }
      }
      return false;
    }
    sessionState.id = st.session_id;
    sessionState.assessment = st.assessment || null;
    sessionState.lastDimCode = null;
    sessionState.wrapCtaActive = false;
    const shifts = st.dimension_shifts || [];
    const byIdx = {};
    shifts.forEach(function (s) {
      if (s.insert_before_index != null) byIdx[s.insert_before_index] = s;
    });
    if (shifts.length) {
      sessionState.lastDimCode = shifts[shifts.length - 1].code;
    }
    persistActiveSession(st.session_id);
    msgBox.innerHTML = "";
    for (let i = 0; i < st.messages.length; i++) {
      if (byIdx[i]) addDimBanner(byIdx[i]);
      const m = st.messages[i];
      addBubble(m.content, (m.role || "") === "user");
    }
    stepIntro.style.display = "none";
    stepChat.style.display = "block";
    if (stepResults) stepResults.style.display = "none";
    if ($("#app")) $("#app").classList.remove("results-only");
    const sa = st.started_at;
    if (sa != null && typeof sa === "number" && sa > 1) {
      sessionState.t0 = Date.now() - Math.max(0, Date.now() / 1000 - sa) * 1000;
    } else {
      sessionState.t0 = Date.now();
    }
    startTimer();
    return true;
  }

  const DIM_ORDER = ["D1", "D2", "D3", "D4", "D5", "D6"];
  const DIM_META = {
    D1: "Awareness & opportunity",
    D2: "Prompts & comms",
    D3: "Critical judgment",
    D4: "Workflows & org design",
    D5: "Clarity, craft & output fit",
    D6: "Risk & responsible use",
  };
  function dimStripTitle(code) {
    return escapeHtml(code) + " · " + escapeHtml(DIM_META[code] || "");
  }

  function escapeHtml(s) {
    return String(s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }
  function formatTimeTotalSec(total) {
    const t = Math.max(0, Math.floor(Number(total) || 0));
    const m = Math.floor(t / 60);
    const r = t % 60;
    return m + ":" + String(r).padStart(2, "0");
  }
  function formatShortMinApprox(sec) {
    const s = Math.round(Math.max(0, Number(sec) || 0));
    if (s < 50) return "<1 min";
    const m = Math.max(1, Math.round(s / 60));
    return "~" + m + " min";
  }
  function ensureTypingVisible() {
    const box = document.getElementById("msgBox");
    const t = document.getElementById("typ");
    if (!box) return;
    if (t) t.scrollIntoView({ block: "end", behavior: "smooth" });
    box.scrollTop = box.scrollHeight;
  }
  function formatAssistantHtml(t) {
    return escapeHtml(t)
      .split(/\n\n+/)
      .filter((p) => p.trim().length)
      .map((p) => {
        const inner = p
          .trim()
          .split("\n")
          .map((line) => line.trim())
          .join("<br />");
        return '<p class="bubble-para">' + inner + "</p>";
      })
      .join("");
  }
  function addDimBanner(shift) {
    if (!shift || !shift.code) return;
    const w = document.createElement("div");
    w.className = "aiq-dim-shift";
    w.setAttribute("role", "status");
    w.setAttribute("aria-label", "Topic shift");
    w.innerHTML =
      '<span class="dim-next">New angle</span>' +
      '<span class="dim-code">' +
      escapeHtml(shift.code) +
      "</span>" +
      '<span class="dim-lbl">' +
      escapeHtml(shift.label || "") +
      "</span>";
    msgBox.appendChild(w);
  }
  function addBubble(text, me) {
    const d = document.createElement("div");
    d.className = "bubble " + (me ? "me" : "them");
    if (me) d.textContent = text;
    else d.innerHTML = formatAssistantHtml(text);
    msgBox.appendChild(d);
    msgBox.scrollTop = msgBox.scrollHeight;
  }

  function setTyping(on) {
    let el = document.getElementById("typ");
    if (on) {
      if (!el) {
        el = document.createElement("div");
        el.id = "typ";
        el.className = "typing";
        el.textContent = "Interviewer is thinking…";
        msgBox.appendChild(el);
      }
      requestAnimationFrame(function () {
        requestAnimationFrame(ensureTypingVisible);
      });
    } else if (el) el.remove();
  }

  async function api(path, body) {
    const r = await fetch(path, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: body ? JSON.stringify(body) : "{}",
    });
    const raw = await r.text();
    let j = {};
    try {
      j = JSON.parse(raw);
    } catch (_) {
      j = { error: raw.slice(0, 300) || r.statusText };
    }
    if (!r.ok) {
      const msg = j.error || j.message || (raw && raw.length < 400 ? raw : r.statusText);
      const err = new Error(msg);
      err.status = r.status;
      throw err;
    }
    return j;
  }

  async function apiGet(path) {
    const r = await fetch(path);
    const raw = await r.text();
    let j = {};
    try {
      j = JSON.parse(raw);
    } catch (_) {
      j = { error: raw.slice(0, 300) || r.statusText };
    }
    if (!r.ok) {
      const err = new Error(j.error || j.message || (raw && raw.length < 400 ? raw : r.statusText));
      err.status = r.status;
      throw err;
    }
    return j;
  }

  function showErr(el, msg) {
    if (!el) return;
    el.textContent = msg;
    el.classList.add("show");
  }

  function startTimer() {
    sessionState.t0 = Date.now();
    if (sessionState.interval) clearInterval(sessionState.interval);
    sessionState.interval = setInterval(() => {
      const s = Math.floor((Date.now() - sessionState.t0) / 1000);
      const m = Math.floor(s / 60);
      const r = s % 60;
      const el = $("#timer");
      if (el) el.textContent = `${m}:${String(r).padStart(2, "0")} / ~10:00`;
    }, 800);
  }

  function _focusEventPayload(visibilityHint) {
    return {
      type: visibilityHint,
      t: Date.now(),
      page_title: typeof document !== "undefined" ? document.title : "",
      page_url: typeof location !== "undefined" ? (location.pathname || "") + (location.search || "") : "",
      visibility: document.visibilityState || "unknown",
      has_focus: typeof document.hasFocus === "function" ? document.hasFocus() : true,
      note:
        "This page’s title/URL only. Browsers do not allow seeing other tabs or apps you switched to (privacy).",
    };
  }

  function visBeacon() {
    if (!sessionState.id) return;
    const typ = document.hidden ? "tab_blur" : "tab_focus";
    const payload = _focusEventPayload(typ);
    api("/api/session/" + sessionState.id + "/event", payload).catch(() => {});
  }
  (function () {
    const tx = document.getElementById("txt");
    const fChat = document.getElementById("fChat");
    if (!tx || !fChat) return;
    tx.addEventListener("keydown", (ev) => {
      if (ev.key === "Enter" && !ev.shiftKey) {
        ev.preventDefault();
        const s = document.getElementById("sendBtn");
        if (s && s.disabled) return;
        fChat.requestSubmit();
      }
    });
  })();

  document.addEventListener("visibilitychange", visBeacon);
  window.addEventListener("blur", () => {
    if (!sessionState.id) return;
    api("/api/session/" + sessionState.id + "/event", {
      type: "window_blur",
      t: Date.now(),
      page_title: typeof document !== "undefined" ? document.title : "",
      page_url: typeof location !== "undefined" ? (location.pathname || "") + (location.search || "") : "",
      visibility: document.visibilityState || "unknown",
      note: "The browser window lost focus. We still cannot read which other tab or app received focus (same-origin privacy).",
    }).catch(() => {});
  });

  function closeEndModal() {
    if (endModal) {
      endModal.setAttribute("hidden", "");
      endModal.classList.remove("end-modal--warn-strong");
    }
    const ex = document.getElementById("endModalError");
    if (ex) {
      ex.setAttribute("hidden", "");
      ex.textContent = "";
    }
  }
  function openEndModal() {
    if (endModal) endModal.removeAttribute("hidden");
  }

  function buildEndModalBody(r) {
    const n = r.dimensions_touched;
    const pct = r.dimension_breadth_percent;
    const gRem = r.guide_time_remaining_sec;
    const extra = r.approx_time_for_remaining_angles_sec;
    const wl = r.warning_level;
    const guideM = Math.max(1, Math.round((r.target_sec || 600) / 60));
    const tln = (r.topic_label_note || "")
      ? "<p class='end-modal__tln'>" + escapeHtml(r.topic_label_note) + "</p>"
      : "";
    const stats =
      '<div class="end-modal__stats" role="group" aria-label="At a glance">' +
      '<div class="end-modal__stat"><span class="end-modal__n">' +
      (r.has_coverage_signal ? n : "—") +
      "/6" +
      '</span><span class="end-modal__l">Topic labels (not a checklist)</span></div>' +
      '<div class="end-modal__stat"><span class="end-modal__n">' +
      (r.user_turns || 0) +
      "</span><span class='end-modal__l'>Your replies</span></div>" +
      '<div class="end-modal__stat"><span class="end-modal__n">' +
      formatTimeTotalSec(gRem) +
      "</span><span class='end-modal__l'>~ " +
      guideM +
      " min guide left</span></div></div>";
    let lede;
    if (!r.has_coverage_signal) {
      lede =
        "<p class='end-modal__lede hint'>We couldn’t count focus shifts in this run yet. Time-on-guide and replies still help you decide whether to <strong>continue</strong> or <strong>end here</strong>.</p>";
    } else if (wl === "strong") {
      lede =
        "<p class='end-modal__lede end-modal__lede--warn'>You’re ending with <strong>only " +
        n +
        " of 6</strong> areas signalled so far (<strong>~" +
        pct +
        "%</strong> breadth). That’s fine — the summary is a snapshot.</p><p class='end-modal__hint'>More time often surfaces other angles: <strong>" +
        formatShortMinApprox(extra) +
        "</strong> — optional.</p>";
    } else if (r.breadth_incomplete) {
      lede =
        "<p class='end-modal__lede'>About <strong>" +
        (r.user_turns || 0) +
        "</strong> reply turns. Roughly <strong>~" +
        formatShortMinApprox(extra) +
        "</strong> can surface more focus areas if you want them — or end here.</p>";
    } else {
      lede = "<p class='end-modal__lede'>The one-page view uses the answers you already gave in this session.</p>";
    }
    return stats + tln + lede;
  }

  function numScore(s) {
    if (s == null) return 0;
    const v = Number(s);
    if (isNaN(v)) return 0;
    return Math.max(0, Math.min(10, v));
  }

  function buildRadarPath(S) {
    const n = 6;
    const cx = 100;
    const cy = 100;
    const maxR = 58;
    const angles = Array.from({ length: n }, (_, i) => -Math.PI / 2 + (i * 2 * Math.PI) / n);
    const pts = DIM_ORDER.map((code, i) => {
      const v = numScore(S[code] && S[code].score);
      const r = (maxR * v) / 10;
      return [cx + r * Math.cos(angles[i]), cy + r * Math.sin(angles[i])];
    });
    const oPts = Array.from({ length: n }, (_, i) => {
      const r = maxR;
      return [cx + r * Math.cos(angles[i]), cy + r * Math.sin(angles[i])];
    });
    const ring =
      "M " + oPts.map((p) => p[0].toFixed(1) + " " + p[1].toFixed(1)).join(" L ") + " Z";
    const inPts = "M " + pts.map((p) => p[0].toFixed(1) + " " + p[1].toFixed(1)).join(" L ") + " Z";
    return { fill: inPts, outline: ring, angles, cx, cy, maxR, pts };
  }

  function buildProfileChip(ass) {
    if (!ass || !ass.level_label) return "";
    return (
      "<p class='profile-chip' role='note'>Scored for: <span class='profile-w'>" +
      escapeHtml(ass.level_label) +
      "</span> · <span class='profile-w'>" +
      escapeHtml(ass.job_family_label || ass.job_family || "") +
      "</span></p>"
    );
  }

  var TYPICAL_FALLBACK = { ic: [28, 50], people_manager: [36, 58], head_of: [45, 68], executive: [52, 75] };

  function getTypicalComposite(ass) {
    if (ass && ass.typical_composite && ass.typical_composite.low != null) return ass.typical_composite;
    var s = (ass && ass.level) || "head_of";
    var r = TYPICAL_FALLBACK[s] || [40, 60];
    return {
      low: r[0],
      high: r[1],
      mid: (r[0] + r[1]) / 2,
      caption: "Directional band for this level in this experience — coaching, not a performance target.",
    };
  }

  function positionVsTypicalScore(aiqN, low, high) {
    if (aiqN == null || isNaN(aiqN)) return { key: "unknown", label: "—" };
    var a = Math.max(0, Math.min(100, aiqN));
    if (a < low - 8) return { key: "well_below", label: "Well below the typical range for your level", cl: "report-bmk-signal--amber" };
    if (a < low) return { key: "below", label: "Below the typical range for your level", cl: "report-bmk-signal--amber" };
    if (a <= high) return { key: "within", label: "Within the typical range for your level", cl: "report-bmk-signal--emerald" };
    if (a <= high + 9) return { key: "above", label: "Above the typical range for your level", cl: "report-bmk-signal--violet" };
    return { key: "well_above", label: "Well above the typical range for your level", cl: "report-bmk-signal--violet" };
  }

  function buildBenchmarkBlock(ass, aiqN) {
    if (!ass || !ass.level) return "";
    var tc = getTypicalComposite(ass);
    var lo = Number(tc.low);
    var hi = Number(tc.high);
    if (isNaN(lo) || isNaN(hi) || lo >= hi) return "";
    var p = positionVsTypicalScore(Number(aiqN), lo, hi);
    if (p.key === "unknown") return "";
    var zl = lo;
    var zw = Math.max(0, hi - lo);
    var mlp = Math.max(0, Math.min(100, Number(aiqN) || 0));
    var cap = tc.caption ? "<p class='report-bmk-cap'>" + escapeHtml(tc.caption) + "</p>" : "";
    return (
      '<div class="report-bmk" role="img" aria-label="Composite score versus typical band for this level">' +
        '<h3 class="report-bmk-title">How this run compares (your level)</h3>' +
        "<p class='report-bmk-lede'>For <strong>" +
        escapeHtml(ass.level_label || "") +
        "</strong>, a directional band on the 0–100 scale is <strong>" +
        lo.toFixed(0) +
        "–" +
        hi.toFixed(0) +
        "</strong> in this product. Your composite is marked on the line.</p>" +
        '<div class="report-bmk-scale" aria-hidden="true">' +
        "<span class='report-bmk-end'>0</span>" +
        '<div class="report-bmk-rail"><div class="report-bmk-zone" style="left:' +
        zl +
        "%;width:" +
        zw +
        '%"></div><div class="report-bmk-tick" style="left:' +
        mlp +
        '%" title="Your result"></div></div>' +
        "<span class='report-bmk-end'>100</span></div>" +
        "<p class='report-bmk-signal " +
        p.cl +
        "'><span class='report-bmk-eyebrow'>Verdict</span> " +
        aiqN.toFixed(1) +
        " — " +
        escapeHtml(p.label) +
        "</p>" +
        cap +
        "</div>"
    );
  }

  function buildResultsHTML(S, ass) {
    const sid = sessionState.id || "";
    const savePdf =
      sid
        ? '<a class="btn btn--secondary report-save-pdf" id="btnSaveReportPdf" href="/api/session/' +
          escapeHtml(sid) +
          '/report.pdf" download="AiQ-snapshot.pdf">Save PDF</a>'
        : "";
    const aiq = S.AiQ_0_100;
    const band = S.maturity_band || "—";
    const R = 44;
    const C = 2 * Math.PI * R;
    const aiqN = aiq == null || aiq === "" ? 0 : Math.max(0, Math.min(100, Number(aiq)));
    const arc = C * (aiqN / 100);
    const radar = buildRadarPath(S);
    const axis = [];
    for (let i = 0; i < 6; i++) {
      const t = -Math.PI / 2 + (i * 2 * Math.PI) / 6;
      axis.push(
        "<line x1='100' y1='100' x2='" + (100 + 58 * Math.cos(t)).toFixed(1) + "' y2='" + (100 + 58 * Math.sin(t)).toFixed(1) + "' />"
      );
    }
    const strip = DIM_ORDER.map((d) => {
      const o = S[d] || {};
      const sc = numScore(o.score);
      const pw = (sc * 10).toFixed(0);
      const sw = ass && ass.weights && ass.weights[d] != null ? "<span class='rstrip-w'>" + (Number(ass.weights[d]) * 100).toFixed(0) + "% w</span>" : "";
      return (
        '<div class="rstrip-c">' +
        "<span class='rstrip-t'>" + dimStripTitle(d) + " " + sw + "</span>" +
        "<span class='rstrip-s'>" + (o.score != null ? o.score : "—") + "/10</span>" +
        '<div class="dim-bar rstrip-bar" role="presentation"><div class="dim-bar__fill" style="width:' + pw + '%"></div></div></div>'
      );
    }).join("");

    let rlines = "";
    DIM_ORDER.forEach((d) => {
      const o = S[d] || {};
      if (o.rationale_1line) {
        rlines +=
          '<p class="rline"><strong class="rline-d">' +
          dimStripTitle(d) +
          "</strong> " +
          escapeHtml(o.rationale_1line) +
          "</p>";
      }
    });
    const pull = S.strength_1line
      ? '<p class="report-pull">' + escapeHtml(S.strength_1line) + "</p>"
      : "";
    const caut = S.risk_1line
      ? '<p class="report-caut"><span class="caut-l">Watch</span> ' + escapeHtml(S.risk_1line) + "</p>"
      : "";
    const aiqOut = aiqN.toFixed(1);

    return (
      '<article class="report-onepage slide-plate no-hero-num" aria-label="Your AiQ one-page summary">' +
      '<p class="report-print-actions no-print">' +
      savePdf +
      "</p>" +
      '<div class="report-hero-row">' +
      "<div class='report-gau'>" +
      "<svg class='r-svg' viewBox='0 0 120 120' width='108' height='108' aria-hidden='true'>" +
      "<circle cx='60' cy='60' r='" + R + "' fill='none' stroke='#e2daf5' stroke-width='7' />" +
      "<circle transform='rotate(-90 60 60)' cx='60' cy='60' r='" + R + "' fill='none' stroke='var(--zingy-purple)' stroke-width='7' stroke-linecap='round' stroke-dasharray='" +
      arc.toFixed(2) +
      " " +
      C.toFixed(2) +
      "' />" +
      "</svg><div class='r-num'>" + aiqOut + '</div><div class="r-subl">AiQ · 0–100</div></div>' +
      "<div class='report-hero-words'>" +
      "<span class='band-pill'>" + escapeHtml(String(band)) + "</span>" +
      "<h2 class='report-ht'>Your AiQ snapshot</h2>" +
      buildProfileChip(ass) +
      buildBenchmarkBlock(ass, aiqN) +
      pull + caut + "</div></div>" +
      "<div class='rstrip' role='group' aria-label='Dimension scores'>" + strip + "</div>" +
      '<div class="report-radar-embed" aria-label="Shape of scores">' +
      ("<svg class='radar-compact' viewBox='0 0 200 200' style='height:8rem' role='img' aria-label='radar'>") +
      (radar.outline ? "<path d='" + radar.outline + "' fill='none' stroke='#d1d0e0' />" : "") +
      (axis.length ? "<g stroke='#e8e4f2' stroke-width='0.4'>" + axis.join("") + "</g>" : "") +
      (radar.fill
        ? "<path d='" + radar.fill + "' fill='rgba(150,0,241,0.12)' stroke='var(--zingy-purple)' stroke-width='1.2' />"
        : "") +
      (radar.pts
        ? radar.pts
            .map(
              (p) => "<circle cx='" + p[0].toFixed(1) + "' cy='" + p[1].toFixed(1) + "' r='2' fill='var(--zingy-purple)' />"
            )
            .join("")
        : "") +
      "<circle cx='100' cy='100' r='1.5' fill='var(--ink)' />" +
      "</svg></div>" +
      (rlines ? "<div class='report-rlines'>" + rlines + "</div>" : "") +
      '<p class="report-foot">Provisional · for reflection and coaching from this one chat, not a hiring score or final label.</p>' +
      "</article>"
    );
  }

  function showResultsView(S, ass) {
    const ap = ass || sessionState.assessment || null;
    const appEl = document.getElementById("app");
    if (appEl) appEl.classList.add("results-only");
    if (stepIntro) stepIntro.style.display = "none";
    if (stepChat) stepChat.style.display = "none";
    const sr = document.getElementById("step-results");
    const mount = document.getElementById("resultsMount");
    if (!sr || !mount) return;
    if (S._raw) {
      const sid2 = sessionState.id || "";
      const pdf2 =
        sid2
          ? "<p class='no-print' style='margin:0 0 0.5rem 0'><a class='btn btn--secondary' href='/api/session/" +
            escapeHtml(sid2) +
            "/report.pdf' download='AiQ-snapshot.pdf'>Save PDF</a></p>"
          : "";
      mount.innerHTML =
        "<div class='slide-plate' style='padding:1.5rem'>" + pdf2 + "<pre style='font-size:0.78rem;white-space:pre-wrap'>" +
        escapeHtml(JSON.stringify(S._raw, null, 2)) +
        "</pre></div>";
    } else {
      try {
        mount.innerHTML = buildResultsHTML(S, ap);
      } catch (e) {
        const sid3 = sessionState.id || "";
        const pdf3 =
          sid3
            ? "<p class='no-print' style='margin:0.5rem 0'><a class='btn btn--secondary' href='/api/session/" +
              escapeHtml(sid3) +
              "/report.pdf' download='AiQ-snapshot.pdf'>Save PDF</a></p>"
            : "";
        mount.innerHTML =
          "<div class='slide-plate' style='padding:1.5rem'><p class='deck-kicker no-print' style='margin-top:0'>Your scores are below; the full layout could not be drawn.</p>" +
          pdf3 +
          "<pre style='font-size:0.75rem;white-space:pre-wrap;overflow:auto;max-height:50vh'>" +
          escapeHtml(JSON.stringify(S, null, 2)) +
          "</pre></div>";
      }
    }
    sr.style.display = "block";
    try {
      mount.scrollIntoView({ block: "start", behavior: "smooth" });
    } catch (_) {
      window.scrollTo(0, 0);
    }
  }

  async function runCompleteAndShowResults() {
    if (!sessionState.id) return;
    const o = await api("/api/session/" + sessionState.id + "/complete", {});
    clearActiveSession();
    if (o.assessment) sessionState.assessment = o.assessment;
    if (sessionState.interval) clearInterval(sessionState.interval);
    const S = o && o.scores;
    const d1s = S && S.D1 && (S.D1.score != null || S.D1.score === 0);
    const hasBody = S && typeof S === "object" && (S.AiQ_0_100 != null || d1s);
    if (!hasBody) {
      showResultsView({ _raw: o }, o.assessment);
    } else {
      showResultsView(S, o.assessment);
    }
  }

  function setEndModalScoringState(on) {
    const m = document.getElementById("endModal");
    if (m) m.setAttribute("data-loading", on ? "1" : "");
    const lo = document.getElementById("endModalLoading");
    if (lo) {
      if (on) lo.removeAttribute("hidden");
      else lo.setAttribute("hidden", "");
    }
  }

  async function completeSession() {
    if (!sessionState.id) return;
    const btn = document.getElementById("endModalConfirm");
    const cont = document.getElementById("endModalContinue");
    const errEl = document.getElementById("endModalError");
    const otxt = btn ? btn.textContent : "";
    if (errEl) {
      errEl.setAttribute("hidden", "");
      errEl.textContent = "";
    }
    if (btn) {
      btn.disabled = true;
      btn.textContent = "Scoring…";
    }
    if (cont) cont.disabled = true;
    setEndModalScoringState(true);
    try {
      await runCompleteAndShowResults();
      setEndModalScoringState(false);
      if (btn) {
        btn.disabled = false;
        btn.textContent = otxt;
      }
      if (cont) cont.disabled = false;
      closeEndModal();
    } catch (e3) {
      setEndModalScoringState(false);
      if (btn) {
        btn.disabled = false;
        btn.textContent = otxt;
      }
      if (cont) cont.disabled = false;
      if (errEl) {
        errEl.textContent = (e3 && e3.message) || "Couldn’t build your summary. Try again.";
        errEl.removeAttribute("hidden");
      } else {
        alert((e3 && e3.message) || "Error");
      }
    }
  }

  if ($("#endModalContinue")) {
    $("#endModalContinue").onclick = closeEndModal;
  }
  if ($("#endModalBackdrop")) {
    $("#endModalBackdrop").onclick = function () {
      const em = document.getElementById("endModal");
      if (em && em.getAttribute("data-loading") === "1") return;
      closeEndModal();
    };
  }
  if ($("#endModalConfirm")) {
    $("#endModalConfirm").onclick = function () {
      completeSession();
    };
  }

  $("#btnBegin").onclick = async function () {
    const berr = $("#startErr");
    berr.classList.remove("show");
    this.disabled = true;
    try {
      const s = String(Math.random()).slice(2) + String(Date.now());
      const levelEl = document.getElementById("selLevel");
      const famEl = document.getElementById("selJobFamily");
      const o = await api("/api/session/start", {
        seed: s,
        client_meta: { ui: "web" },
        level: levelEl ? levelEl.value : undefined,
        job_family: famEl ? famEl.value : undefined,
      });
      sessionState.id = o.session_id;
      sessionState.lastDimCode = null;
      sessionState.assessment = o.assessment || null;
      sessionState.wrapCtaActive = false;
      persistActiveSession(o.session_id);
      if (wrapCtaCountdown) {
        clearInterval(wrapCtaCountdown);
        wrapCtaCountdown = null;
      }
      const w0 = document.getElementById("wrapCta");
      const wtime0 = document.getElementById("wrapCtaTimer");
      if (w0) w0.setAttribute("hidden", "");
      if (wtime0) {
        wtime0.setAttribute("hidden", "");
        wtime0.textContent = "";
      }
      stepIntro.style.display = "none";
      stepChat.style.display = "block";
      if (stepResults) stepResults.style.display = "none";
      if ($("#app")) $("#app").classList.remove("results-only");
      addBubble(o.opening, false);
      startTimer();
    } catch (e) {
      showErr(berr, e.message || "Could not start. Check API key / server logs.");
      this.disabled = false;
    }
  };

  $("#fChat").onsubmit = async function (e) {
    e.preventDefault();
    const t = $("#txt");
    const tx = t.value.trim();
    if (!tx) return;
    t.value = "";
    addBubble(tx, true);
    setTyping(true);
    $("#sendBtn").disabled = true;
    try {
      const o = await api("/api/session/" + sessionState.id + "/message", { text: tx });
      setTyping(false);
      if (o.dimension_shift) {
        const c = o.dimension_shift.code;
        if (c && c !== sessionState.lastDimCode) {
          addDimBanner(o.dimension_shift);
          sessionState.lastDimCode = c;
        }
      }
      addBubble(o.reply, false);
      if (o.session_suggests_complete) {
        const w = document.getElementById("wrapCta");
        const wtext = w && w.querySelector(".wrap-cta__text");
        if (w) w.removeAttribute("hidden");
        if (wtext) wtext.textContent = "Session complete. Opening your report…";
        const wtime = document.getElementById("wrapCtaTimer");
        if (wtime) {
          wtime.setAttribute("hidden", "");
          wtime.textContent = "";
        }
        if (wrapCtaCountdown) {
          clearInterval(wrapCtaCountdown);
          wrapCtaCountdown = null;
        }
        if (t) t.disabled = true;
        setTyping(true);
        try {
          await runCompleteAndShowResults();
          setTyping(false);
        } catch (e3) {
          setTyping(false);
          if (t) t.disabled = false;
          $("#sendBtn").disabled = false;
          showErr(
            $("#chatErr"),
            (e3 && e3.message) || "Couldn’t build your summary. Use View results to try again."
          );
        }
        return;
      }
    } catch (e2) {
      setTyping(false);
      const st = e2.status;
      const retriable = st === 502 || st === 503 || st === 504 || !st;
      const detail = retriable
        ? "Temporary connection issue — your session is still saved. Wait a moment and press Send again, or refresh this page to continue."
        : (e2.message || "Something went wrong — try again.");
      showErr($("#chatErr"), detail);
      addBubble(
        retriable
          ? "Could not reach the server just now. Your chat is still here — send again when ready."
          : "Could not get a reply. See the note under the input.",
        false
      );
    }
    $("#sendBtn").disabled = false;
  };

  $("#linkDone").onclick = async function (e) {
    e.preventDefault();
    if (!sessionState.id) return;
    this.style.pointerEvents = "none";
    let rj;
    try {
      rj = await apiGet("/api/session/" + sessionState.id + "/readiness");
    } catch (err) {
      this.style.pointerEvents = "auto";
      showErr($("#chatErr"), err.message || "Could not load session");
      return;
    }
    if (rj.warning_level === "strong") {
      this.style.pointerEvents = "auto";
      $("#endModalTitle").textContent = "You’re still early on breadth";
      if (endModal) endModal.classList.add("end-modal--warn-strong");
      const exm = document.getElementById("endModalError");
      if (exm) {
        exm.setAttribute("hidden", "");
        exm.textContent = "";
      }
      $("#endModalBody").innerHTML = buildEndModalBody(rj);
      openEndModal();
      return;
    }
    setTyping(true);
    try {
      await runCompleteAndShowResults();
      setTyping(false);
    } catch (err) {
      setTyping(false);
      this.style.pointerEvents = "auto";
      showErr($("#chatErr"), (err && err.message) || "Couldn’t build your summary.");
      return;
    }
    this.style.pointerEvents = "auto";
  };

  (function resumeBoot() {
    const bb = $("#btnBegin");
    if (bb) bb.disabled = true;
    tryResumeOnLoad().finally(function () {
      if (bb && !sessionState.id) bb.disabled = false;
    });
  })();

  (async function initAssessmentSelects() {
    const sl = document.getElementById("selLevel");
    const sf = document.getElementById("selJobFamily");
    if (!sl || !sf) return;
    try {
      const o = await apiGet("/api/assessment/options");
      const opt = (items) =>
        items
          .map(
            (x) =>
              "<option value='" +
              String(x.slug).replace(/'/g, "&#39;") +
              "'>" +
              escapeHtml(x.label) +
              "</option>"
          )
          .join("");
      sl.innerHTML = opt(o.levels || []);
      sf.innerHTML = opt(o.job_families || []);
      if (o.defaults) {
        if (o.defaults.level) sl.value = o.defaults.level;
        if (o.defaults.job_family) sf.value = o.defaults.job_family;
      }
    } catch (_) {
      sl.innerHTML =
        "<option value='ic'>Individual contributor</option><option value='people_manager'>People manager</option><option value='head_of' selected>Head of / director</option><option value='executive'>Executive</option>";
      sf.innerHTML = "<option value='general_management' selected>General management / P&L</option><option value='other'>Other</option>";
    }
  })();
})();
