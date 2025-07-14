import {select} from "../helpers.js";

export const Tabulator = (() => {
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
  }

  // formatter‐factory: interpolate ${…} → rowData[…]
  function applyTemplateFormatter(table, columnName, templateStr) {
    table.updateColumnDefinition(columnName, {
      formatter(cell) {
        const data = cell.getRow().getData();
        // make CSRF available to ${csrftoken}
        data.csrftoken = getCookie("csrftoken");
        // simple ${key} → data[key]
        return templateStr.replace(/\$\{([^}]+)\}/g, (_, key) =>
          data[key] != null ? data[key] : ""
        );
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

  const applyTabulatorWidget = (el, csrftoken) => {
    const path = el.dataset.path;         // ex: "pyfinbot/stocks/"
    const columns = JSON.parse(el.dataset.columns);
    const pageSize = parseInt(el.dataset.pageSize, 10);

    const table = new window.Tabulator(el, {
      ajaxURL: `/api/${path}`,
      ajaxConfig: {
        method: "GET",
        credentials: "same-origin",       // send the session cookie
        headers: { "X-CSRFToken": csrftoken },
      },

      // remote pagination
      pagination:     "remote",
      paginationMode: "remote",
      paginationSize: pageSize,

      // map API response → Tabulator’s defaults
      dataReceiveParams: {
        data:      "items",  // array of rows
        last_page: "pages",  // total # pages
        last_row:  "total" // overall row count (optional)
      },

      layout:      "fitColumns",
      placeholder: "No records found.",

      columns,
    });
    el._tabulator = table;

    table.on("tableBuilt", () => {
      const field = el.dataset.templateField;
      const tplId = el.dataset.templateId;
      if (field && tplId) {
        applyTemplateFormatterById(table, field, tplId);
      }
    });
  }

  const init = () => {
    document.addEventListener("DOMContentLoaded", () => {
      const csrftoken = getCookie("csrftoken");

      select(".tabulator-widget", true).forEach((el) => {
        applyTabulatorWidget(el, csrftoken);
      });
    });
  }

  return {
    init,
    applyTabulatorWidget
  };
})();
