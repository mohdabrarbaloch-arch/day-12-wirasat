/* Wirasat — frontend application logic
 * Vanilla JS SPA: auth → heir picker → calculation → history → print view.
 */
(function () {
  "use strict";

  const API = "/api";
  let token = localStorage.getItem("wirasat_token") || "";
  let heirCatalogue = [];
  const selected = new Map(); // key -> count

  const $ = (id) => document.getElementById(id);

  async function api(path, opts = {}) {
    const headers = { "Content-Type": "application/json", ...(opts.headers || {}) };
    if (token) headers["Authorization"] = "Bearer " + token;
    const res = await fetch(API + path, { ...opts, headers });
    if (res.status === 401 && token) {
      token = "";
      localStorage.removeItem("wirasat_token");
      showAuth();
      throw new Error("Session expired — please log in again");
    }
    if (!res.ok) {
      let detail = "Request failed";
      try {
        const data = await res.json();
        detail = Array.isArray(data.detail) ? data.detail.map((d) => d.msg).join("; ") : data.detail || detail;
      } catch (_) { /* ignore */ }
      throw new Error(detail);
    }
    return res.status === 204 ? null : res.json();
  }

  function toast(msg) {
    const el = $("toast");
    el.textContent = msg;
    el.hidden = false;
    el.style.position = "fixed";
    el.style.bottom = "24px";
    el.style.zIndex = "100";
    clearTimeout(el._t);
    el._t = setTimeout(() => { el.hidden = true; }, 2200);
  }

  function fmtMoney(amount) {
    if (amount === null || amount === undefined) return "";
    return "Rs " + Number(amount).toLocaleString("en-PK", {
      minimumFractionDigits: 2, maximumFractionDigits: 2
    });
  }

  function showAuth() {
    $("auth-view").hidden = false;
    $("app-view").hidden = true;
  }

  function showApp() {
    $("auth-view").hidden = true;
    $("app-view").hidden = false;
    $("calc-view").hidden = false;
    $("history-view").hidden = true;
    loadHeirs();
  }

  let authTab = "login";
  $("auth-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const email = $("email").value.trim();
    const password = $("password").value;
    const fullName = $("full-name").value.trim();
    const err = $("auth-error");
    err.hidden = true;

    try {
      let data;
      if (authTab === "register") {
        data = await api("/auth/register", {
          method: "POST",
          body: JSON.stringify({ email, password, full_name: fullName }),
        });
      } else {
        data = await api("/auth/login/json", {
          method: "POST",
          body: JSON.stringify({ email, password }),
        });
      }
      token = data.access_token;
      localStorage.setItem("wirasat_token", token);
      $("auth-form").reset();
      showApp();
      setTimeout(() => toast("Welcome, " + (data.user.full_name || data.user.email) + " 👋"), 350);
    } catch (ex) {
      err.textContent = ex.message;
      err.hidden = false;
    }
  });

  document.querySelectorAll(".tab").forEach((tab) => {
    tab.addEventListener("click", () => {
      document.querySelectorAll(".tab").forEach((t) => t.classList.remove("active"));
      tab.classList.add("active");
      authTab = tab.dataset.tab;
      $("name-field").hidden = authTab !== "register";
      $("auth-submit").textContent = authTab === "register" ? "Create Account" : "Login";
    });
  });

  $("btn-logout").addEventListener("click", () => {
    token = "";
    localStorage.removeItem("wirasat_token");
    selected.clear();
    showAuth();
    toast("Logged out");
  });

  const EMOJI = {
    husband: "👨‍🦱", wife: "👩", son: "👦", daughter: "👧",
    father: "👨‍🦳", mother: "👩‍🦳",
    paternal_grandfather: "👴", paternal_grandmother: "👵", maternal_grandmother: "👵",
    full_brother: "🧔", full_sister: "👩‍🦰",
    paternal_brother: "🧔‍♂️", paternal_sister: "👩‍🦱",
    maternal_brother: "👨", maternal_sister: "👩",
    nephew: "👨‍🦲", paternal_nephew: "👨‍🦲",
    paternal_uncle: "🧓", paternal_uncles_son: "👨",
    son_son: "👶", son_daughter: "👧", son_sons_son: "👶",
  };

  async function loadHeirs() {
    if (heirCatalogue.length) return renderHeirs();
    try {
      const data = await api("/heirs");
      heirCatalogue = data.heirs;
      renderHeirs();
    } catch (ex) {
      $("calc-error").textContent = "Could not load heirs: " + ex.message;
      $("calc-error").hidden = false;
    }
  }

  function renderHeirs() {
    const grid = $("heir-grid");
    grid.innerHTML = "";
    heirCatalogue.forEach((h) => {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "heir-chip";
      btn.dataset.key = h.key;

      const emoji = document.createElement("span");
      emoji.className = "chip-emoji";
      emoji.textContent = EMOJI[h.key] || "👤";

      const label = document.createElement("span");
      label.textContent = h.label;

      btn.appendChild(emoji);
      btn.appendChild(label);

      const countRow = document.createElement("span");
      countRow.className = "count-row";
      countRow.hidden = true;
      const minus = document.createElement("button");
      minus.type = "button";
      minus.textContent = "−";
      const countVal = document.createElement("span");
      countVal.className = "count-val";
      countVal.textContent = "1";
      const plus = document.createElement("button");
      plus.type = "button";
      plus.textContent = "+";
      countRow.appendChild(minus);
      countRow.appendChild(countVal);
      countRow.appendChild(plus);
      btn.appendChild(countRow);

      minus.addEventListener("click", (e) => {
        e.stopPropagation();
        const c = (selected.get(h.key) || 1) - 1;
        if (c < 1) { selected.delete(h.key); updateChip(btn, countVal, countRow, false); }
        else { selected.set(h.key, c); countVal.textContent = c; }
      });
      plus.addEventListener("click", (e) => {
        e.stopPropagation();
        const c = (selected.get(h.key) || 1) + 1;
        selected.set(h.key, Math.min(c, 20));
        countVal.textContent = selected.get(h.key);
        updateChip(btn, countVal, countRow, true);
      });

      btn.addEventListener("click", () => {
        if (selected.has(h.key)) {
          selected.delete(h.key);
          updateChip(btn, countVal, countRow, false);
        } else {
          selected.set(h.key, 1);
          updateChip(btn, countVal, countRow, true);
        }
      });

      grid.appendChild(btn);
    });
  }

  function updateChip(btn, countVal, countRow, on) {
    btn.classList.toggle("selected", on);
    countRow.hidden = !on;
    countVal.textContent = selected.get(btn.dataset.key) || "1";
  }

  $("btn-calculate").addEventListener("click", async () => {
    const err = $("calc-error");
    err.hidden = true;
    if (selected.size === 0) {
      err.textContent = "Please select at least one heir.";
      err.hidden = false;
      return;
    }
    const heirs = [];
    const counts = {};
    selected.forEach((count, key) => {
      heirs.push(key);
      counts[key] = count;
    });
    const estate = parseFloat($("estate-value").value) || 0;

    try {
      const result = await api("/calculate", {
        method: "POST",
        body: JSON.stringify({
          deceased_gender: $("deceased-gender").value,
          estate_value: estate,
          heirs,
          counts,
        }),
      });
      renderResults(result, estate);
    } catch (ex) {
      err.textContent = ex.message;
      err.hidden = false;
    }
  });

  function renderResults(result, estate) {
    const results = $("results");
    results.hidden = false;
    results.scrollIntoView({ behavior: "smooth", block: "nearest" });

    const badge = $("mode-badge");
    badge.textContent = result.mode;
    badge.className = "badge " + result.mode;

    const notesBox = $("notes-box");
    notesBox.hidden = !(result.notes && result.notes.length);
    notesBox.innerHTML = "";
    (result.notes || []).forEach((n) => {
      const p = document.createElement("p");
      p.textContent = "ℹ️ " + n;
      notesBox.appendChild(p);
    });

    const list = $("result-list");
    list.innerHTML = "";
    result.entries.forEach((e) => {
      const item = document.createElement("div");
      item.className = "result-item" + (e.kind === "asabah" ? " asabah" : "");

      const info = document.createElement("div");
      info.className = "heir-info";
      const emoji = document.createElement("span");
      emoji.className = "heir-emoji";
      emoji.textContent = EMOJI[e.key] || "👤";
      const nameWrap = document.createElement("div");
      const name = document.createElement("div");
      name.className = "heir-name";
      name.textContent = e.label + (e.count > 1 ? ` ×${e.count}` : "");
      nameWrap.appendChild(name);
      if (e.kind === "asabah") {
        const tag = document.createElement("div");
        tag.className = "heir-count";
        tag.textContent = "asabah (residuary)";
        nameWrap.appendChild(tag);
      }
      info.appendChild(emoji);
      info.appendChild(nameWrap);

      const share = document.createElement("div");
      share.className = "heir-share";
      const frac = document.createElement("div");
      frac.className = "share-frac";
      const pct = (e.share_decimal * 100).toFixed(1).replace(/\.0$/, "");
      frac.textContent = `${e.share_numerator}/${e.share_denominator} (${pct}%)`;
      share.appendChild(frac);
      if (e.amount !== null && e.amount !== undefined && e.amount > 0) {
        const amt = document.createElement("div");
        amt.className = "share-amt";
        amt.textContent = fmtMoney(e.amount);
        share.appendChild(amt);
      }

      item.appendChild(info);
      item.appendChild(share);
      list.appendChild(item);
    });

    const totalRow = $("total-row");
    totalRow.innerHTML = "";
    const label = document.createElement("span");
    label.textContent = "Total";
    const val = document.createElement("span");
    const totalPct = result.entries.reduce((s, e) => s + e.share_decimal, 0) * 100;
    val.textContent = totalPct.toFixed(1).replace(/\.0$/, "") + "%";
    totalRow.appendChild(label);
    totalRow.appendChild(val);

    window.__lastResult = { result, estate };
  }

  $("btn-print").addEventListener("click", () => {
    if (!window.__lastResult) return;
    const { result, estate } = window.__lastResult;
    const printView = $("print-view");

    const rows = result.entries.map((e) => `
      <div class="print-row">
        <span>${e.label}${e.count > 1 ? ` ×${e.count}` : ""} ${e.kind === "asabah" ? "(asabah)" : ""}</span>
        <span>${e.share_numerator}/${e.share_denominator}${e.amount ? " — " + fmtMoney(e.amount) : ""}</span>
      </div>`).join("");

    printView.innerHTML = `
      <div class="print-card">
        <h2>🕌 Wirasat — Faraid Distribution</h2>
        <p style="margin:6px 0 14px;color:#666;font-size:13px;">
          Mode: <strong>${result.mode}</strong>
          ${estate ? " · Estate: <strong>" + fmtMoney(estate) + "</strong>" : ""}
        </p>
        ${result.notes.map((n) => `<p style="font-size:12px;color:#8a6d1a;">ℹ️ ${n}</p>`).join("")}
        <div style="margin-top:10px;">${rows}</div>
        <p class="print-foot">Calculated with Wirasat — a Faraid inheritance tool. This is a digital estimate; always confirm with a qualified scholar.</p>
      </div>`;

    window.print();
  });

  $("btn-history").addEventListener("click", async () => {
    $("calc-view").hidden = true;
    $("history-view").hidden = false;
    const list = $("history-list");
    list.innerHTML = '<p class="history-empty">Loading…</p>';
    try {
      const rows = await api("/history?limit=20");
      if (!rows.length) {
        list.innerHTML = '<p class="history-empty">No calculations saved yet.</p>';
        return;
      }
      list.innerHTML = "";
      rows.forEach((r) => {
        const item = document.createElement("div");
        item.className = "history-item";
        const left = document.createElement("div");
        const title = document.createElement("div");
        title.className = "h-title";
        const heirNames = JSON.parse(r.input_heirs || "[]").map((k) => k.replace(/_/g, " "));
        title.textContent = heirNames.slice(0, 4).join(", ") + (heirNames.length > 4 ? "…" : "");
        const meta = document.createElement("div");
        meta.className = "h-meta";
        meta.textContent = new Date(r.created_at).toLocaleString("en-GB") + " · " + r.mode;
        left.appendChild(title);
        left.appendChild(meta);
        const total = document.createElement("div");
        total.className = "h-total";
        const pct = (r.entries.reduce((s, e) => s + e.share_decimal, 0) * 100).toFixed(1);
        total.textContent = pct + "%";
        item.appendChild(left);
        item.appendChild(total);
        item.style.cursor = "pointer";
        item.addEventListener("click", () => renderResults(r, r.estate_value));
        list.appendChild(item);
      });
    } catch (ex) {
      list.innerHTML = `<p class="history-empty">${ex.message}</p>`;
    }
  });

  $("btn-back-calc").addEventListener("click", () => {
    $("history-view").hidden = true;
    $("calc-view").hidden = false;
  });

  (async function boot() {
    if (token) {
      try {
        await api("/auth/me");
        showApp();
        return;
      } catch (_) { /* fall through to login */ }
    }
    showAuth();
  })();
})();
