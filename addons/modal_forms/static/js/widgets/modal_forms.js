import { select, on, toBool } from "../helpers.js";
import { Bootstrap } from "../bootstrap.js";

(function () {
  "use strict";

  async function handleAuthRedirect(res) {
    // 1) HTMX-compatible redirect header
    const hx = res.headers.get("HX-Redirect");
    if (hx) {
      window.location.assign(hx);
      return true;
    }

    // 2) JSON payload: {redirect: "..."}
    const ct = res.headers.get("content-type") || "";
    if (ct.includes("application/json")) {
      try {
        const data = await res.json();
        if (data && data.redirect) {
          window.location.assign(data.redirect);
          return true;
        }
      } catch {
        // ignore JSON parse errors and fall through
      }
    }

    // 3) Fallbacks: try the response URL or reload
    if (res.url) {
      window.location.assign(res.url);
      return true;
    }
    window.location.reload();
    return true;
  }

  // Click handler for any .js-modal trigger
  on("click", document, async (e) => {
    const trigger = e.target.closest(".js-modal");
    if (!trigger) return;

    const url =
      trigger.getAttribute("data-form-url") ||
      trigger.getAttribute("data-url") ||
      trigger.getAttribute("href");

    if (!url || url === "#") return;
    e.preventDefault();

    const modalEl = select("#globalModal");
    if (!modalEl) {
      console.error("globalModal root not found");
      return;
    }

    // If django-bootstrap-modal-forms is available, prefer it
    if (window.jQuery && typeof window.jQuery.fn.modalForm === "function") {
      window.jQuery(trigger).modalForm({ formURL: url, modalID: "#globalModal" });
      return;
    }

    // Fallback: fetch partial into modal then show
    const modalContent = select(".modal-content", false, modalEl);
    if (!modalContent) {
      console.error("No .modal-content found inside #globalModal");
      return;
    }

    try {
      const res = await fetch(url, {
        headers: { "X-Requested-With": "XMLHttpRequest" },
      });

      // If unauthenticated, backend returns 401 with redirect info
      if (res.status === 401) {
        await handleAuthRedirect(res);
        return;
      }

      // In case some middleware returned a 3xx we didn't expect (fetch follows redirects)
      const html = await res.text();
      modalContent.innerHTML = html;

      // Re-init any widgets inside the modal
      if (Bootstrap?.widgets?.Password?.init) {
        Bootstrap.widgets.Password.init();
      }

      // Look for the static flag inside the newly loaded content
      const headerEl = modalContent.querySelector(".modal-header");
      const staticFlag = headerEl?.dataset.modalStatic;
      const isStatic = toBool(staticFlag);

      // Create a modal instance with per-popup options
      const modal = bootstrap.Modal.getOrCreateInstance(modalEl, {
        backdrop: isStatic ? "static" : true,
        keyboard: !isStatic,
      });

      // Look for the scrollable flag
      const scrollFlag = headerEl?.dataset.modalScrollable;
      const isScrollable = toBool(scrollFlag);

      // Apply scrollability to the modal-dialog element
      const dialogEl = modalEl.querySelector(".modal-dialog");
      if (dialogEl) {
        dialogEl.classList.toggle("modal-dialog-scrollable", isScrollable);
      }

      modal.show();
    } catch (err) {
      console.error("Failed to load modal content:", err);
    }
  });

  // Sanity check that the global modal host exists
  on("DOMContentLoaded", document, () => {
    if (!select("#globalModal")) {
      console.error("globalModal NOT in DOM at DOMContentLoaded");
    }
  });

  // Enable/disable confirm button when modal is shown
  on("shown.bs.modal", document, (e) => {
    const modal = select(e.target);
    const input = select('input[data-required-text]', false, modal);
    const btn   = select('button[id$="SubmitBtn"]', false, modal);
    if (!input || !btn) return;

    const required = input.dataset.requiredText || "";
    const check = () => { btn.disabled = (input.value.trim() !== required); };

    // Avoid duplicate listeners if the modal is opened repeatedly
    input.removeEventListener("input", input._confirmHandler || (() => {}));
    input._confirmHandler = check;

    on("input", input, check);
    check();
  });

  // Cleanup when modal is hidden
  on("hidden.bs.modal", document, (e) => {
    const modal = select(e.target);
    const input = select('input[data-required-text]', false, modal);
    if (input && input._confirmHandler) {
      input.removeEventListener("input", input._confirmHandler);
      delete input._confirmHandler;
    }
  });

})();