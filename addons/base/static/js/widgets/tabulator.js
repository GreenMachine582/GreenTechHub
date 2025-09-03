import { select } from "../helpers.js";

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

const getCookie = (name) => {
  let val = null;
  if (document.cookie && document.cookie !== "") {
    document.cookie.split(";").forEach((c) => {
      c = c.trim();
      if (c.startsWith(name + "=")) {
        val = decodeURIComponent(c.slice(name.length + 1));
      }
    });
  }
  return val;
};

const debounce = (fn, wait = 300) => {
  let t;
  return (...args) => {
    clearTimeout(t);
    t = setTimeout(() => fn(...args), wait);
  };
};

function resolveConfig(el) {
  const defaults = window.tabulatorDefaults?.[el.id] || {};

  // allow optional data-* overrides
  const pageSize = el.dataset.pageSize
    ? parseInt(el.dataset.pageSize, 10)
    : (defaults.pageSize || 20);

  const columns = el.dataset.columns
    ? JSON.parse(el.dataset.columns)
    : (Array.isArray(defaults.columns) ? defaults.columns.slice() : []);
  const qbScope = el.getAttribute("data-qb-scope") || defaults.qbScope || null;

  return {
    path: el.dataset.path || defaults.path,
    columns,
    pageSize,
    templateColumns: defaults.templateColumns || [],
    qbScope,
    minReqGapMs: 500,        // throttle same requests
    _filters: null,          // latest from qb:search
    showSummary: defaults.showSummary !== false,
    includeQB: defaults.includeQB !== false,
  };
}

// ----- QueryBuilder integration -----
function parseSAF(v) {
  if (!v) return null;
  if (typeof v === "object") return v;
  try { return JSON.parse(v); } catch { return null; }
}

function findHiddenFiltersInput() {
  return (
    document.querySelector("#qb-filters") ||
    document.querySelector('input[type="hidden"][name="filters"]')
  );
}

function filtersParam(cfg, params) {
  const raw = (params && Array.isArray(params.filter)) ? params.filter : [];

  // Convert Tabulator filters -> sqlalchemy-filters style (AND group)
  const leaves = raw.map(({ field, type, value }) => {
      const t = (type || "like").toLowerCase();
      const safOp = TAB_TO_SAF_OP[t] || "ilike";
      let v = normalizeValue(value, safOp);
      if (v == null || (Array.isArray(v) && !v.length)) return null;
      if (safOp === "ilike") v = likeWrap(t, v);
      return { field, op: safOp, value: v };
    })
    .filter(Boolean);

  const rulesSpec = leaves.length ? { and: leaves } : null;

  // QB spec from live payload or hidden input
  const qbSpec = parseSAF(cfg._filters) ||
    parseSAF((() => { const h = findHiddenFiltersInput(); return h && h.value; })());

  if (rulesSpec && qbSpec) return JSON.stringify({ and: [ qbSpec, rulesSpec ] });
  if (rulesSpec)            return JSON.stringify(rulesSpec);
  if (qbSpec)               return JSON.stringify(qbSpec);
  return null;
}

function stableSorters(sorters) {
  if (!Array.isArray(sorters) || !sorters.length) return null;
  const clean = sorters.map(s => ({
    field: String(s.field || "").trim(),
    dir: (s.dir || "asc").toLowerCase() === "desc" ? "desc" : "asc",
  })).filter(s => s.field);
  return clean.length ? JSON.stringify(clean) : null;
}

function buildFinalURL(baseURL, params, cfg) {
  const u = new URL(baseURL, window.location.origin);

  // Remote pagination params from Tabulator
  if (params.page != null) u.searchParams.set("page", params.page);
  if (params.size != null) u.searchParams.set("size", params.size);

  const sortersJson = stableSorters(params.sort);
  if (sortersJson) {
    u.searchParams.set("sorters", sortersJson);
  } else {
    // legacy single-field fallback (optional; server will fallback anyway)
    const first = (params.sort && params.sort[0]) || {};
    if (first.field) u.searchParams.set("sort", (first.dir === "desc" ? "-" : "") + first.field);
  }

  // Filters from QB (raw QB JSON for now)
  const f = filtersParam(cfg, params);
  if (f) {
    u.searchParams.set("filters", f);
    params.__filters__ = f; // influence dedupe key
  } else {
    delete params.__filters__;
  }
  return u.toString();
}

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
function applyTemplateFormatterById(table, columnName, tplId) {
  const tpl = document.getElementById(tplId);
  if (!tpl) {
    console.error(`Tabulator template "${tplId}" not found`);
    return;
  }
  applyTemplateFormatter(table, columnName, tpl.innerHTML);
}

function bindQBSearch(table, cfg, el) {
  const scopeEl = (cfg.qbScope ? document.querySelector(cfg.qbScope) : null) || document;
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
    sorters: stableSorters(params.sorters) || "[]",
  });
}

const applyTabulatorWidget = (el, csrftoken) => {
  const cfg = resolveConfig(el);
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

    ajaxRequestFunc: (url, config, params) => {
      const finalUrl = buildFinalURL(url, params, cfg);

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
  }

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
      applyTemplateFormatterById(table, field, templateId);
    });
  });

  if (cfg.includeQB) {
    bindQBSearch(table, cfg, el);
  }

  // expose and return
  el._tabulator = table;
  return table;
};

const init = () => {
  document.addEventListener("DOMContentLoaded", () => {
    const csrftoken = getCookie("csrftoken");
    select(".tabulator-widget", true).forEach((el) => {
      applyTabulatorWidget(el, csrftoken);
    });
  });
};

export const Tabulator = { init, applyTabulatorWidget };
