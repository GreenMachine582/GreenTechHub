import { select, safeParseJSON, debounce, getCookie } from "../helpers.js";

// Map Tabulator header-filter ops -> SAF ops
const TAB_TO_SAF_OP = Object.freeze({
  "=": "==", "==": "==", "!=": "!=",
  ">": ">", ">=": ">=", "<": "<", "<=": "<=",
  like: "ilike", starts: "ilike", ends: "ilike", in: "in",
});

function likeWrap(op, val) {
  if (val == null) return val;
  if (op === 'contains' || op === 'like')   return `%${val}%`;
  if (op === 'startswith') return `${val}%`;
  if (op === 'endswith')   return `%${val}`;
  return val;
}

function normalizeValue(val, op) {
  if (val == null) return null;
  if (Array.isArray(val)) return val.filter(v => v != null && String(v).trim() !== "");
  const s = String(val).trim();
  if (!s) return null;
  if (s.toLowerCase() === "true") return true;
  if (s.toLowerCase() === "false") return false;
  if (op === "in") return s.split(",").map(x => x.trim()).filter(Boolean);
  return s;
}

const deepMerge = (base, ...rest) => {
  const out = {...base};
  for (const src of rest) {
    if (!src || typeof src !== "object") continue;
    for (const [k, v] of Object.entries(src)) {
      if (v && typeof v === "object" && !Array.isArray(v)) {
        out[k] = deepMerge(out[k] || {}, v);
      } else {
        out[k] = v;
      }
    }
  }
  return out;
};

const toBool = (v, fallback) => {
  if (v == null) return fallback;
  if (typeof v === "boolean") return v;
  const s = String(v).trim().toLowerCase();
  if (s === "true" || s === "1" || s === "yes" || s === "on")  return true;
  if (s === "false"|| s === "0" || s === "no"  || s === "off") return false;
  return fallback;
};

const pickInt = (v, fallback) => {
  if (v == null) return fallback;
  const n = parseInt(v, 10);
  return Number.isFinite(n) && n > 0 ? n : fallback;
};

// Modal root helper
const closestModal = (el) => el.closest?.(".modal") || document;

// Try to load JSON config from a <script type="application/json"> node
const loadScriptConfig = (el) => {
  // explicit data-config-src selector OR default to #{id}-config if id exists
  const sel = el.getAttribute("data-config-src") || (el.id ? `#${el.id}-config` : null);
  if (!sel) return null;
  const node = closestModal(el)?.querySelector(sel);
  if (!node) return null;
  const type = (node.getAttribute("type") || "").toLowerCase();
  if (type && type !== "application/json") return null; // only parse JSON script
  return safeParseJSON(node.textContent, null);
};

/* ----------------- Config ----------------- */
function resolveConfig(el) {
  // 1) Config from a JSON script block
  const scriptCfg = loadScriptConfig(el);

  // 2) Inline data-config JSON on the element itself
  const dataCfg = el.dataset.config ? safeParseJSON(el.dataset.config, null) : null;

  // Merge precedence: data-config > script-config > window-defaults
  const defaults = deepMerge({}, scriptCfg || {}, dataCfg || {});

  // 3) Inline overrides (highest precedence for common fields)
  const columnsAttr         = el.dataset.columns ? safeParseJSON(el.dataset.columns, null) : null;
  const templateColumnsAttr = el.dataset.templateColumns ? safeParseJSON(el.dataset.templateColumns, null) : null;

  const path     = el.dataset.path || defaults.path || ""; // REQUIRED for remote data
  const pageSize = pickInt(el.dataset.pageSize, pickInt(defaults.pageSize, 20));
  const qbScope  = el.getAttribute("data-qb-scope") || defaults.qbScope || null;

  // booleans: dataset wins if present, else defaults, else sensible fallback
  const showSummary = toBool(el.dataset.showSummary, toBool(defaults.showSummary, true));
  const includeQB   = toBool(el.dataset.includeQb,  toBool(defaults.includeQB,   true));

  // final columns
  const columns = Array.isArray(columnsAttr) ? columnsAttr
                 : Array.isArray(defaults.columns) ? defaults.columns.slice()
                 : [];

  const templateColumns = Array.isArray(templateColumnsAttr) ? templateColumnsAttr
                         : Array.isArray(defaults.templateColumns) ? defaults.templateColumns
                         : [];

  return {
    path,
    columns,
    pageSize,
    templateColumns,
    qbScope,
    minReqGapMs: pickInt(defaults.minReqGapMs, 500),
    _filters: null,
    showSummary,
    includeQB,
  };
}

/* --------------- QB + Filters --------------- */
function parseSAF(v) {
  if (!v) return null;
  if (typeof v === "object") return v;
  try { return JSON.parse(v); } catch { return null; }
}

function findHiddenFiltersInput(root = document) {
  return (
    root.querySelector("#qb-filters") ||
    root.querySelector('input[type="hidden"][name="filters"]')
  );
}

function filtersParam(cfg, params, root = document) {
  const raw = (params && Array.isArray(params.filter)) ? params.filter : [];

  // Convert Tabulator filters -> sqlalchemy-filters style (AND group)
  const leaves = raw.map(({ field, type, value }) => {
      const t = (type || "like").toLowerCase();
      const safOp = TAB_TO_SAF_OP[t] || "ilike";
      let v = normalizeValue(value, safOp);
      if (v == null || (Array.isArray(v) && !v.length)) return null;
      if (safOp === "ilike") v = likeWrap(t, v);
      return { field, op: safOp, value: v };
    }).filter(Boolean);

  const rulesSpec = leaves.length ? { and: leaves } : null;

  // QB spec from live payload or hidden input
  const qbSpec = parseSAF(cfg._filters) ||
    parseSAF((() => { const h = findHiddenFiltersInput(root); return h && h.value; })());

  if (rulesSpec && qbSpec) return JSON.stringify({ and: [ qbSpec, rulesSpec ] });
  if (rulesSpec)            return JSON.stringify(rulesSpec);
  if (qbSpec)               return JSON.stringify(qbSpec);
  return null;
}

/* --------------- Sorters + URL --------------- */
function extractSorters(params = {}) {
  return Array.isArray(params.sorters) ? params.sorters :
         Array.isArray(params.sort)    ? params.sort    : [];
}

function stableSorters(sortersLike) {
  const sorters = Array.isArray(sortersLike) ? sortersLike : [];
  if (!sorters.length) return null;
  const clean = sorters.map(s => ({
    field: String(s.field || "").trim(),
    dir: (s.dir || "asc").toLowerCase() === "desc" ? "desc" : "asc",
  })).filter(s => s.field);
  return clean.length ? JSON.stringify(clean) : null;
}

function buildFinalURL(baseURL, params, cfg, root = document) {
  const u = new URL(baseURL, window.location.origin);

  // Remote pagination params from Tabulator
  if (params.page != null) u.searchParams.set("page", params.page);
  if (params.size != null) u.searchParams.set("size", params.size);

  const sortersJson = stableSorters(extractSorters(params));
  if (sortersJson) {
    u.searchParams.set("sorters", sortersJson);
  } else {
    const first = extractSorters(params)[0] || {};
    if (first.field) u.searchParams.set("sort", (first.dir === "desc" ? "-" : "") + first.field);
  }

  // Filters from QB (raw QB JSON for now)
  const f = filtersParam(cfg, params, root);
  if (f) {
    u.searchParams.set("filters", f);
    params.__filters__ = f; // influence dedupe key
  } else {
    delete params.__filters__;
  }
  return u.toString();
}

/* --------------- Template formatters --------------- */
// formatter-factory: interpolate ${…} → rowData[…]
function applyTemplateFormatter(table, columnName, templateStr) {
  table.updateColumnDefinition(columnName, {
    formatter(cell) {
      const data = cell.getRow().getData();
      // make CSRF available to ${csrftoken}
      data.csrftoken = getCookie("csrftoken");
      // simple ${key} → data[key] (supports dot paths)
      return templateStr.replace(/\$\{([^}]+)\}/g, (_, key) => {
        const parts = key.split(".");
        let v = data;
        for (const p of parts) v = v?.[p];
        return v != null ? String(v) : "";
      });
    },
  });
}

// fetch a <script type="text/template"> by ID
function applyTemplateFormatterById(table, columnName, tplId, root) {
  const tpl = root.querySelector(`#${tplId}`);
  if (!tpl) {
    console.error(`Tabulator template "${tplId}" not found within root`, root);
    return;
  }
  applyTemplateFormatter(table, columnName, tpl.innerHTML);
}

function bindQBSearch(table, cfg, el, root) {
  const scopeEl = cfg.qbScope ? document.querySelector(cfg.qbScope) : root;
  const refresh = debounce(() => table.setData(), 150);

  const handler = (e) => {
    const { qb, json } = e.detail || {};
    if (scopeEl !== document) {
      const container = qb?.root || qb; // support either element or instance.root
      if (!container || !scopeEl.contains(container)) return;
    }
    cfg._filters = json || '';
    refresh();                     // trigger request
  };

  scopeEl.addEventListener('qb:search', handler);
  el._qbSearchDetach = () => scopeEl.removeEventListener('qb:search', handler);
}

// Build a stable key for dedup/throttle
function buildRequestKey(finalUrl, params) {
  return JSON.stringify({
    url: finalUrl,
    page: params.page,
    size: params.size,
    filters: params.__filters__ || null,
    sorters: stableSorters(extractSorters(params)) || "[]",
  });
}

const applyTabulatorWidget = (el, csrftoken) => {
  if (!el || el._tabulator) return el?._tabulator; // don't double init

  const cfg = resolveConfig(el);
  const root = closestModal(el); // modal element or document
  el.classList.add("tabulator-bootstrap5");

  const paginationCounterFn = (pageSize, currentRow, currentPage, totalRows, totalPages) => {
    // currentRow is 1-based index of the first visible row
    if (!totalRows || totalRows <= 0) return "Showing 0";
     // number of rows currently visible on THIS page (respects header filters on the page)
    const activeOnPage = table ? table.getDataCount("active") : Math.min(pageSize, Math.max(0, totalRows - currentRow + 1));
    const start = activeOnPage ? currentRow : 0;
    const end   = activeOnPage ? (currentRow + activeOnPage - 1) : 0;
    return `Showing ${start}–${end} of ${totalRows} (${currentPage} of ${totalPages} pages)`;
  };

  // per-element request gate
  const gate = { lastKey: null, lastTime: 0, pending: null };

  const options = {
    ajaxURL: `/api/${cfg.path}`,
    ajaxConfig: {
      method: "GET",
      credentials: "same-origin",       // send the session cookie
      headers: { "X-CSRFToken": csrftoken },
    },
    pagination: true,
    paginationMode: "remote",
    paginationSize: cfg.pageSize,
    paginationSizeSelector: true,
    // Map API response → Tabulator’s defaults
    dataReceiveParams: {
      data:      "items",  // array of rows
      last_page: "pages",  // total # pages
      last_row:  "total",  // overall row count (optional)
    },

    ajaxRequestFunc: (url, config, params = {}) => {
      const finalUrl = buildFinalURL(url, params, cfg, root);

      // throttle identical requests
      const now = Date.now();
      const key = buildRequestKey(finalUrl, params);
      const sameAsLast = key === gate.lastKey;
      const since = now - gate.lastTime;

      const runFetch = () => {
        gate.lastKey = key; gate.lastTime = Date.now();
        return fetch(finalUrl, config).then((r) => {
          if (!r.ok) throw r;
          return r.json();
        });
      };

      if (sameAsLast && since < cfg.minReqGapMs) {
        // delay until min gap elapses; merge concurrent calls
        if (!gate.pending) {
          const wait = cfg.minReqGapMs - since;
          gate.pending = new Promise((resolve, reject) => {
            setTimeout(() => {
              runFetch().then(resolve).catch(reject).finally(() => (gate.pending = null));
            }, wait);
          });
        }
        return gate.pending;
      }

      // different request or enough time passed
      return runFetch();
    },

    filterMode: "remote",
    sortMode: "remote",
    layout: "fitColumns",
    placeholder: "No records found.",
    columns: cfg.columns,
  };

  if (cfg.showSummary) {
    const summarySelector = `#${el.id}-summary`;
    if (document.querySelector(summarySelector)) {
      options.paginationCounter = paginationCounterFn;
      options.paginationCounterElement = summarySelector;
    } else {
      console.warn(`Tabulator summary element ${summarySelector} not found; disabling counter.`);
    }
  }

  const table = new window.Tabulator(el, options);

  // Apply any template formatters
  table.on("tableBuilt", () => {
    (cfg.templateColumns || []).forEach(({ field, templateId }) => {
      applyTemplateFormatterById(table, field, templateId, root);
    });
    el._tableBuilt = true;
  });

  if (cfg.includeQB) {
    bindQBSearch(table, cfg, el, root);
  }

  // expose and return
  el._tabulator = table;
  el._root = root;
  el._tabulatorDestroy = () => {
    try { el._qbSearchDetach?.(); } catch {}
    try { table.destroy(); } catch {}
    el._tabulator = null;
    el._tableBuilt = false;
  };

  return table;
};

/* --------------- Public init helpers --------------- */
function initWithin(root = document) {
  const csrftoken = getCookie("csrftoken");
  select(".tabulator-widget", true, root).forEach((el) => {
    applyTabulatorWidget(el, csrftoken);
  });
}

// redraw only when safe: after built AND visible
function safeRedraw(el) {
  const t = el?._tabulator;
  if (!t) return;
  const doRedraw = () => { try { t.redraw(true); } catch {} };
  if (el._tableBuilt && el.offsetParent) doRedraw();
  else t.on?.("tableBuilt", () => { if (el.offsetParent) doRedraw(); });
}

function enableModalAutoInit() {
  if (!window.bootstrap?.Modal) return;

  document.addEventListener("shown.bs.modal", (e) => {
    const modalEl = e.target;
    initWithin(modalEl);
    // Redraw all tables once visible (fixes width calcs)
    select(".tabulator-widget", true, modalEl).forEach((el) => safeRedraw(el));
  });

  document.addEventListener("hidden.bs.modal", (e) => {
    const modalEl = e.target;
    select(".tabulator-widget", true, modalEl).forEach((el) => el._tabulatorDestroy?.());
  });
}

const init = () => {
  document.addEventListener("DOMContentLoaded", () => {
    // Page-level widgets
    initWithin(document);
    // Auto-manage widgets inside Bootstrap modals
    enableModalAutoInit();
  });
};

export const Tabulator = { init, applyTabulatorWidget, initWithin, enableModalAutoInit };
