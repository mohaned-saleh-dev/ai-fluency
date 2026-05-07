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
    targetSec: 900,
    progressTouched: [],
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
      sessionState.t0 = sa * 1000;
    } else {
      sessionState.t0 = Date.now();
    }
    sessionState.targetSec = Number(st.target_duration_sec) || 900;
    startTimer({ keepT0: true });
    renderProgress(st.progress);
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
      escapeHtml(shift.label || DIM_META[shift.code] || "") +
      "</span>";
    msgBox.appendChild(w);
  }

  function renderProgress(progress) {
    const chips = document.getElementById("aiqProgressChips");
    const count = document.getElementById("aiqProgressCount");
    if (!chips) return;
    const touched = (progress && Array.isArray(progress.touched)) ? progress.touched : sessionState.progressTouched;
    sessionState.progressTouched = touched;
    if (progress && progress.target_sec) sessionState.targetSec = Number(progress.target_sec) || sessionState.targetSec;
    const current = (progress && progress.current) || (touched.length ? touched[touched.length - 1] : null);
    const set = new Set(touched);
    const html = DIM_ORDER.map((code) => {
      const isOn = set.has(code);
      const isCur = code === current;
      const cls = "aiq-chip" + (isOn ? " is-on" : "") + (isCur ? " is-current" : "");
      const labelTxt = DIM_META[code] || code;
      return (
        '<span class="' + cls + '" title="' + escapeHtml(code + " · " + labelTxt) +
        '" aria-label="' + escapeHtml(code + " " + labelTxt + (isOn ? " covered" : " pending")) + '">' +
        '<span class="aiq-chip__c">' + escapeHtml(code) + "</span>" +
        '<span class="aiq-chip__l">' + escapeHtml(labelTxt) + "</span>" +
        "</span>"
      );
    }).join("");
    chips.innerHTML = html;
    if (count) count.textContent = touched.length + " / 6";
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

  function startTimer(opts) {
    if (!opts || !opts.keepT0) sessionState.t0 = Date.now();
    if (sessionState.interval) clearInterval(sessionState.interval);
    const tick = () => {
      const elapsed = Math.max(0, Math.floor((Date.now() - sessionState.t0) / 1000));
      const m = Math.floor(elapsed / 60);
      const r = elapsed % 60;
      const el = $("#timer");
      if (el) el.textContent = `${m}:${String(r).padStart(2, "0")}`;
      const fill = document.getElementById("aiqProgressFill");
      if (fill) {
        const tgt = Math.max(60, Number(sessionState.targetSec) || 900);
        const pct = Math.min(100, Math.max(0, (elapsed / tgt) * 100));
        fill.style.width = pct.toFixed(1) + "%";
      }
    };
    tick();
    sessionState.interval = setInterval(tick, 800);
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

  function numScore(s) {
    if (s == null) return 0;
    const v = Number(s);
    if (isNaN(v)) return 0;
    return Math.max(0, Math.min(10, v));
  }

  var TYPICAL_FALLBACK = { ic: [28, 50], people_manager: [36, 58], head_of: [45, 68], executive: [52, 75] };

  function getTypicalComposite(ass) {
    if (ass && ass.typical_composite && ass.typical_composite.low != null) return ass.typical_composite;
    var s = (ass && ass.level) || "head_of";
    var r = TYPICAL_FALLBACK[s] || [40, 60];
    return { low: r[0], high: r[1], mid: (r[0] + r[1]) / 2 };
  }

  function positionVsTypicalScore(aiqN, low, high) {
    if (aiqN == null || isNaN(aiqN)) return { key: "unknown" };
    var a = Math.max(0, Math.min(100, aiqN));
    if (a < low) return { key: "below", cl: "report-bmk-signal--amber" };
    if (a <= high) return { key: "within", cl: "report-bmk-signal--emerald" };
    return { key: "above", cl: "report-bmk-signal--violet" };
  }

  function buildBandRail(ass, aiqN) {
    if (!ass || !ass.level) return "";
    const tc = getTypicalComposite(ass);
    const lo = Number(tc.low);
    const hi = Number(tc.high);
    if (isNaN(lo) || isNaN(hi) || lo >= hi) return "";
    const p = positionVsTypicalScore(Number(aiqN), lo, hi);
    if (p.key === "unknown") return "";
    const mlp = Math.max(0, Math.min(100, Number(aiqN) || 0));
    const verdictMap = {
      well_below: "Below the typical range",
      below: "Below the typical range",
      within: "Within the typical range",
      above: "Above the typical range",
      well_above: "Above the typical range",
    };
    const verdict = verdictMap[p.key] || "";
    return (
      '<div class="report-bmk-scale" aria-hidden="true">' +
      "<span class='report-bmk-end'>0</span>" +
      '<div class="report-bmk-rail"><div class="report-bmk-zone" style="left:' +
      lo +
      "%;width:" +
      Math.max(0, hi - lo) +
      '%"></div><div class="report-bmk-tick" style="left:' +
      mlp +
      '%" title="Your result"></div></div>' +
      "<span class='report-bmk-end'>100</span></div>" +
      "<p class='report-bmk-signal " +
      (p.cl || "") +
      "'>" +
      escapeHtml(verdict) +
      " <span class='report-bmk-range'>(" +
      lo.toFixed(0) +
      "–" +
      hi.toFixed(0) +
      ")</span></p>"
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
    const aiqN = aiq == null || aiq === "" ? 0 : Math.max(0, Math.min(100, Number(aiq)));
    const aiqOut = aiqN.toFixed(1);

    const profileLine =
      ass && ass.level_label
        ? "<p class='report-section__sub'>For " +
          escapeHtml(ass.level_label) +
          (ass.job_family_label || ass.job_family
            ? " · " + escapeHtml(ass.job_family_label || ass.job_family)
            : "") +
          "</p>"
        : "";

    const dimCards = DIM_ORDER.map((d) => {
      const o = S[d] || {};
      const sc = numScore(o.score);
      const pw = (sc * 10).toFixed(0);
      const why = o.rationale_1line ? String(o.rationale_1line).trim() : "";
      const whyHtml = why
        ? '<p class="dim-card__why">' + escapeHtml(why.length > 220 ? why.slice(0, 217) + "…" : why) + "</p>"
        : "";
      return (
        '<div class="dim-card">' +
        "<span class='dim-card__t'>" + escapeHtml(d) + " · " + escapeHtml(DIM_META[d] || "") + "</span>" +
        "<span class='dim-card__s'>" + (o.score != null ? o.score : "—") + "<span class='dim-card__s-out'>/10</span></span>" +
        '<div class="dim-bar dim-card__bar" role="presentation"><div class="dim-bar__fill" style="width:' + pw + '%"></div></div>' +
        whyHtml +
        "</div>"
      );
    }).join("");

    const strength = S.strength_1line ? String(S.strength_1line).trim() : "";
    const risk = S.risk_1line ? String(S.risk_1line).trim() : "";
    const summaryBlock =
      strength || risk
        ? '<section class="report-section">' +
          '<h3 class="report-section__h">What this run suggests</h3>' +
          (strength ? '<p class="report-blurb report-blurb--up">' + escapeHtml(strength) + "</p>" : "") +
          (risk ? '<p class="report-blurb report-blurb--watch"><span class="report-blurb__tag">Watch</span>' + escapeHtml(risk) + "</p>" : "") +
          "</section>"
        : "";

    return (
      '<article class="report-simple slide-plate no-hero-num" aria-label="Your AiQ result">' +
      '<p class="report-print-actions no-print">' +
      savePdf +
      "</p>" +
      // 1. Overall result
      '<section class="report-section report-section--hero">' +
      '<h3 class="report-section__h">Your overall result</h3>' +
      '<div class="report-hero-num"><span class="report-hero-num__n">' + aiqOut + "</span><span class='report-hero-num__u'>AiQ · 0–100</span></div>" +
      '<p class="report-section__lede">Composite from this conversation — useful directionally, not a performance label.</p>' +
      "</section>" +
      summaryBlock +
      // 2. Where you're expected to be
      '<section class="report-section">' +
      '<h3 class="report-section__h">Where you’re expected to be</h3>' +
      profileLine +
      buildBandRail(ass, aiqN) +
      "</section>" +
      // 3. AiQ level (maturity band)
      '<section class="report-section">' +
      '<h3 class="report-section__h">Your AiQ level</h3>' +
      "<span class='band-pill band-pill--lg'>" + escapeHtml(String(band)) + "</span>" +
      '<p class="report-section__sub">Band label from your composite for this experience.</p>' +
      "</section>" +
      // 4. Per-dimension scores
      '<section class="report-section">' +
      '<h3 class="report-section__h">Score per dimension</h3>' +
      '<p class="report-section__sub">Each score is 0–10 with a short note from your answers in this chat.</p>' +
      "<div class='dim-card-grid'>" + dimCards + "</div>" +
      "</section>" +
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
      sessionState.targetSec = Number(o.target_duration_sec) || 900;
      sessionState.progressTouched = [];
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
      renderProgress(o.progress);
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
      renderProgress(o.progress);
      if (o.session_suggests_complete) {
        const w = document.getElementById("wrapCta");
        const wtext = w && w.querySelector(".wrap-cta__text");
        if (w) w.removeAttribute("hidden");
        if (wtext) {
          wtext.textContent = "Whenever you’re ready, tap End session & view results below — or keep going.";
        }
        const wtime = document.getElementById("wrapCtaTimer");
        if (wtime) {
          wtime.setAttribute("hidden", "");
          wtime.textContent = "";
        }
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

  $("#linkDone").onclick = function (e) {
    e.preventDefault();
    if (!sessionState.id) return;
    if (endModal) endModal.classList.remove("end-modal--warn-strong");
    const tEl = document.getElementById("endModalTitle");
    if (tEl) tEl.textContent = "End this session?";
    const bEl = document.getElementById("endModalBody");
    if (bEl) {
      bEl.innerHTML =
        "<p class='end-modal__lede'>Ending will close the chat and generate your one-page summary from this conversation. You can keep going if you’d rather continue.</p>";
    }
    const errEl = document.getElementById("endModalError");
    if (errEl) {
      errEl.setAttribute("hidden", "");
      errEl.textContent = "";
    }
    openEndModal();
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
