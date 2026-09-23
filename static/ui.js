/*
 * Kairos UI kit - zero dependencies, no build step.
 *
 * Every function returns a detached DOM element, so a caller can place it
 * anywhere. Use them on the day instead of writing markup:
 *
 *   mount(out, UI.kpis([{label: "Total", value: 1200, format: "money"}]));
 *   mount(out, UI.table(rows));
 *   mount(out, UI.barChart({data: [{label: "groceries", value: 1200}]}));
 *   mount(out, UI.autoRender(anythingTheBackendReturned));
 */

const UI = (() => {
  const el = (tag, cls, text) => {
    const node = document.createElement(tag);
    if (cls) node.className = cls;
    if (text !== undefined && text !== null) node.textContent = String(text);
    return node;
  };

  // ---------- formatting ----------

  const nf = new Intl.NumberFormat("en-US", { maximumFractionDigits: 2 });
  const nfCompact = new Intl.NumberFormat("en-US", { notation: "compact", maximumFractionDigits: 1 });

  const fmt = {
    raw: (v) => (v === null || v === undefined ? "-" : String(v)),
    num: (v) => (typeof v === "number" ? nf.format(v) : fmt.raw(v)),
    compact: (v) => (typeof v === "number" ? nfCompact.format(v) : fmt.raw(v)),
    money: (v) => (typeof v === "number" ? nf.format(Math.round(v)) : fmt.raw(v)),
    percent: (v) => (typeof v === "number" ? `${nf.format(v * 100)}%` : fmt.raw(v)),
    auto: (v) => {
      if (v === null || v === undefined) return "-";
      if (typeof v === "number") return nf.format(v);
      if (typeof v === "boolean") return v ? "yes" : "no";
      if (typeof v === "object") return JSON.stringify(v);
      return String(v);
    },
  };

  const pick = (name) => (typeof name === "function" ? name : fmt[name] || fmt.auto);

  // ---------- states ----------

  const loading = (label = "Working...") => {
    const box = el("div", "state");
    box.append(el("span", "spinner"), el("span", null, label));
    return box;
  };

  const empty = (label = "Nothing to show.") => el("div", "state state-muted", label);

  const error = (label = "Something went wrong.") => {
    const box = el("div", "state state-error");
    box.append(el("span", "dot-error"), el("span", null, label));
    return box;
  };

  const note = (label) => el("p", "note", label);

  // ---------- text ----------

  const answer = (text) => {
    const box = el("div", "answer");
    box.textContent = text;
    return box;
  };

  const json = (value) => {
    const pre = el("pre", "json");
    pre.textContent = JSON.stringify(value, null, 2);
    return pre;
  };

  // ---------- key / value card ----------

  const keyValue = (obj, { format = "auto", title } = {}) => {
    const f = pick(format);
    const box = el("div", "card");
    if (title) box.append(el("h3", "card-title", title));
    const dl = el("dl", "kv");
    for (const [key, value] of Object.entries(obj || {})) {
      dl.append(el("dt", null, humanize(key)), el("dd", null, f(value)));
    }
    box.append(dl);
    return box;
  };

  // ---------- KPI row ----------

  const kpis = (items = []) => {
    const row = el("div", "kpis");
    for (const item of items) {
      const f = pick(item.format || "auto");
      const cell = el("div", "kpi");
      cell.append(el("div", "kpi-label", item.label));
      cell.append(el("div", "kpi-value", f(item.value)));
      if (item.hint) cell.append(el("div", "kpi-hint", item.hint));
      row.append(cell);
    }
    return row;
  };

  // ---------- table ----------

  const table = (rows = [], { columns, format = "auto", max = 100, title } = {}) => {
    if (!Array.isArray(rows) || rows.length === 0) return empty("No rows.");
    const f = pick(format);
    const cols = columns || Object.keys(rows[0]);

    const box = el("div", "card");
    if (title) box.append(el("h3", "card-title", title));

    const scroller = el("div", "table-scroll");
    const t = el("table", "table");
    const thead = el("thead");
    const hr = el("tr");
    for (const col of cols) {
      const th = el("th", null, humanize(col));
      if (isNumericColumn(rows, col)) th.classList.add("num");
      hr.append(th);
    }
    thead.append(hr);

    const tbody = el("tbody");
    for (const row of rows.slice(0, max)) {
      const tr = el("tr");
      for (const col of cols) {
        const td = el("td", null, f(row[col]));
        if (typeof row[col] === "number") td.classList.add("num");
        tr.append(td);
      }
      tbody.append(tr);
    }
    t.append(thead, tbody);
    scroller.append(t);
    box.append(scroller);

    if (rows.length > max) box.append(note(`Showing ${max} of ${rows.length} rows.`));
    return box;
  };

  // ---------- horizontal bar chart (single series) ----------

  const barChart = ({
    data = [],
    labelKey = "label",
    valueKey = "value",
    format = "compact",
    title,
    maxBars = 10,
  } = {}) => {
    const rows = normalizeSeries(data, labelKey, valueKey);
    if (rows.length === 0) return empty("No data to chart.");

    const f = pick(format);
    const shown = rows.slice(0, maxBars);
    const peak = Math.max(...shown.map((r) => Math.abs(r.value))) || 1;

    const rowH = 30;
    const gap = 2;              // surface gap between adjacent bars
    const labelW = 132;
    const valueW = 72;
    const width = 620;
    const plotW = width - labelW - valueW;
    const height = shown.length * (rowH + gap) - gap;

    const box = el("div", "card");
    if (title) box.append(el("h3", "card-title", title));

    const svg = svgEl("svg", {
      class: "chart",
      viewBox: `0 0 ${width} ${height}`,
      role: "img",
      "aria-label": title || "Bar chart",
      preserveAspectRatio: "xMidYMid meet",
    });

    shown.forEach((row, i) => {
      const y = i * (rowH + gap);
      const barW = Math.max(2, (Math.abs(row.value) / peak) * plotW);

      const label = svgEl("text", {
        x: labelW - 10,
        y: y + rowH / 2,
        class: "chart-label",
        "text-anchor": "end",
        "dominant-baseline": "central",
      });
      label.textContent = truncate(row.label, 18);

      const track = svgEl("rect", {
        x: labelW, y, width: plotW, height: rowH, rx: 4, class: "chart-track",
      });

      const bar = svgEl("rect", {
        x: labelW, y: y + 5, width: barW, height: rowH - 10, rx: 4, class: "chart-bar",
      });
      const tip = svgEl("title");
      tip.textContent = `${row.label}: ${f(row.value)}`;
      bar.append(tip);

      const value = svgEl("text", {
        x: width - 8,
        y: y + rowH / 2,
        class: "chart-value",
        "text-anchor": "end",
        "dominant-baseline": "central",
      });
      value.textContent = f(row.value);

      svg.append(track, bar, label, value);
    });

    box.append(svg);
    if (rows.length > maxBars) box.append(note(`Showing top ${maxBars} of ${rows.length}.`));
    return box;
  };

  // ---------- automatic rendering ----------

  /**
   * Best-effort rendering of an unknown backend payload. Handy in the first
   * hour; replace with explicit calls once the shape of the case is known.
   */
  const autoRender = (payload) => {
    const frag = document.createDocumentFragment();
    if (payload === null || payload === undefined) return empty();

    if (typeof payload === "string") {
      frag.append(answer(payload));
      return frag;
    }

    if (Array.isArray(payload)) {
      frag.append(isSeries(payload) ? barChart({ data: payload }) : table(payload));
      return frag;
    }

    if (typeof payload === "object") {
      const scalars = {};
      let rendered = false;
      for (const [key, value] of Object.entries(payload)) {
        if (Array.isArray(value) && value.length && typeof value[0] === "object") {
          frag.append(isSeries(value) ? barChart({ data: value, title: humanize(key) }) : table(value, { title: humanize(key) }));
          rendered = true;
        } else if (value !== null && typeof value === "object") {
          frag.append(keyValue(value, { title: humanize(key) }));
          rendered = true;
        } else {
          scalars[key] = value;
        }
      }
      if (Object.keys(scalars).length) frag.prepend(keyValue(scalars));
      if (!rendered && !Object.keys(scalars).length) frag.append(json(payload));
      return frag;
    }

    frag.append(answer(String(payload)));
    return frag;
  };

  // ---------- helpers ----------

  function humanize(key) {
    return String(key).replace(/[_-]+/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
  }

  function truncate(text, n) {
    const s = String(text);
    return s.length > n ? s.slice(0, n - 1) + "…" : s;
  }

  function isNumericColumn(rows, col) {
    return rows.some((r) => typeof r[col] === "number");
  }

  function normalizeSeries(data, labelKey, valueKey) {
    return (data || [])
      .map((row) => {
        if (Array.isArray(row)) return { label: row[0], value: Number(row[1]) };
        const label = row[labelKey] ?? row.name ?? row.category ?? row.key;
        const numericKey = valueKey in row ? valueKey : ["total", "amount", "count", "sum"].find((k) => k in row);
        return { label, value: Number(row[numericKey]) };
      })
      .filter((r) => r.label !== undefined && Number.isFinite(r.value))
      .sort((a, b) => Math.abs(b.value) - Math.abs(a.value));
  }

  function isSeries(rows) {
    if (!Array.isArray(rows) || rows.length === 0 || rows.length > 12) return false;
    if (typeof rows[0] !== "object") return false;
    const keys = Object.keys(rows[0]);
    if (keys.length > 3) return false;
    const hasLabel = keys.some((k) => ["label", "name", "category", "key"].includes(k));
    const hasValue = keys.some((k) => ["value", "total", "amount", "count", "sum"].includes(k));
    return hasLabel && hasValue;
  }

  function svgEl(tag, attrs = {}) {
    const node = document.createElementNS("http://www.w3.org/2000/svg", tag);
    for (const [k, v] of Object.entries(attrs)) node.setAttribute(k, v);
    return node;
  }

  return { el, fmt, loading, empty, error, note, answer, json, keyValue, kpis, table, barChart, autoRender };
})();

/** Replace the contents of a container with one or more nodes. */
function mount(container, ...nodes) {
  container.replaceChildren(...nodes);
}

/** Append without clearing. */
function append(container, ...nodes) {
  container.append(...nodes);
}
