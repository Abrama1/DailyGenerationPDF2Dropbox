const TZ = "Asia/Tbilisi";

const el = (id) => document.getElementById(id);

const statusMeta = (status) => {
  const s = (status || "").toLowerCase();

  const isError =
    s.includes("error") || s === "unexpected_error" || s === "pdf_extract_error" || s === "date_parse_error";
  const isUploaded = s === "uploaded";
  const isDuplicate = s.startsWith("duplicate");
  const isBusy = s === "lock_busy";

  if (isUploaded) return { label: "Uploaded", dot: "ok" };
  if (isDuplicate) return { label: "Stopped (duplicate)", dot: "warn" };
  if (isBusy) return { label: "Skipped (lock)", dot: "warn" };
  if (isError) return { label: "Error", dot: "err" };
  return { label: status || "Unknown", dot: "info" };
};

const fmtTime = (iso) => {
  if (!iso) return "—";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return new Intl.DateTimeFormat("en-GB", {
    timeZone: TZ,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  }).format(d);
};

const safeText = (v) => (v === null || v === undefined || v === "" ? "—" : String(v));

async function fetchJson(path) {
  const res = await fetch(path, { cache: "no-store" });
  if (!res.ok) throw new Error(`Failed to load ${path} (${res.status})`);
  return res.json();
}

function setCards(summary) {
  const lastRun = summary?.last_run || null;
  const meta = statusMeta(lastRun?.status);

  el("generatedAt").textContent = `Generated: ${fmtTime(summary?.generated_at)}`;
  el("lastRunStatus").textContent = meta.label;
  el("lastRunReason").textContent = safeText(lastRun?.stop_reason || lastRun?.error_message);

  el("lastSuccessKey").textContent = safeText(summary?.last_success_date_key);
  el("lastRunTime").textContent = fmtTime(lastRun?.started_at);
  el("lastRunDuration").textContent =
    lastRun?.duration_ms != null ? `${lastRun.duration_ms} ms` : "—";
}

function rowHtml(run) {
  const meta = statusMeta(run.status);
  const dateKey = run.date_key ? `<span class="mono">${run.date_key}</span>` : `<span class="small">—</span>`;
  const reason = safeText(run.stop_reason || run.error_message);

  return `
    <div class="row" data-status="${(run.status || "").toLowerCase()}" data-search="${(
      `${run.status || ""} ${run.date_key || ""} ${reason}`.toLowerCase()
    ).replaceAll('"', "")}">
      <div class="ts mono">${fmtTime(run.started_at)}</div>

      <div>
        <span class="badge">
          <span class="dot ${meta.dot}"></span>
          ${meta.label}
        </span>
      </div>

      <div>${dateKey}</div>

      <div class="reason">${reason}</div>
    </div>
  `;
}

function applyFilter(runs) {
  const filter = document.querySelector(".seg.active")?.dataset?.filter || "all";
  const q = (el("searchInput").value || "").trim().toLowerCase();

  return runs.filter((r) => {
    const s = (r.status || "").toLowerCase();

    const okFilter =
      filter === "all" ||
      (filter === "uploaded" && s === "uploaded") ||
      (filter === "duplicates" && s.startsWith("duplicate")) ||
      (filter === "errors" && (s.includes("error") || s === "unexpected_error"));

    const okSearch =
      !q ||
      `${r.status || ""} ${r.date_key || ""} ${r.stop_reason || ""} ${r.error_message || ""}`
        .toLowerCase()
        .includes(q);

    return okFilter && okSearch;
  });
}

function renderList(allRuns) {
  const filtered = applyFilter(allRuns);

  el("runsCount").textContent = `${filtered.length} shown • ${allRuns.length} total`;

  if (!filtered.length) {
    el("logList").innerHTML = `<div class="empty">No runs match your filter/search.</div>`;
    return;
  }

  el("logList").innerHTML = filtered.map(rowHtml).join("");
}

function bindControls(allRuns) {
  document.querySelectorAll(".seg").forEach((btn) => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".seg").forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      renderList(allRuns);
    });
  });

  el("searchInput").addEventListener("input", () => renderList(allRuns));
}

async function init() {
  try {
    const bust = `?v=${Date.now()}`;
    const summary = await fetchJson(`./data/summary.json${bust}`);
    const runsPayload = await fetchJson(`./data/runs.json${bust}`);
    const runs = Array.isArray(runsPayload?.runs) ? runsPayload.runs : [];

    setCards(summary);
    bindControls(runs);
    renderList(runs);
  } catch (err) {
    el("generatedAt").textContent = "Failed to load dashboard data";
    el("logList").innerHTML = `<div class="empty">${err.message}</div>`;
  }
}

init();
