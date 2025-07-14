import {select} from "../helpers.js";

export const Tabulator = (() => {
  const getCookie = (name) => {
    let cookieValue = null;
    if (document.cookie && document.cookie !== "") {
      document.cookie.split(";").forEach((cookie) => {
        cookie = cookie.trim();
        if (cookie.startsWith(name + "=")) {
          cookieValue = decodeURIComponent(cookie.slice(name.length + 1));
        }
      });
    }
    return cookieValue;
  }

  const applyTabulatorWidget = (el, csrftoken) => {
    const path = el.dataset.path;         // ex: "pyfinbot/stocks/"
    const columns = JSON.parse(el.dataset.columns);
    const pageSize = parseInt(el.dataset.pageSize, 10);

    const ajaxURL = `/api/${path}`;

    el._tabulator = new window.Tabulator(el, {
      ajaxURL,
      ajaxConfig: {
        method: "GET",
        credentials: "same-origin",       // send the session cookie
        headers: { "X-CSRFToken": csrftoken },
      },

      // remote pagination
      pagination:     "remote",
      paginationMode: "remote",
      paginationSize: pageSize,

      // map your API response → Tabulator’s defaults
      dataReceiveParams: {
        data:      "items",  // array of rows
        last_page: "pages",  // total # pages
        last_row:  "total" // overall row count (optional)
      },

      layout:      "fitColumns",
      placeholder: "No records found.",

      columns,
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
