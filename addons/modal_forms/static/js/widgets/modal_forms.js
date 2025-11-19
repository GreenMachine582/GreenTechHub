import { select, on, toBool } from "../helpers.js";
import { Bootstrap } from "../bootstrap.js";

(function () {
  "use strict";

  const MODAL_SELECTOR = "#globalModal";
  let pendingModalUrl = null;

  // ----- Shared helpers -----------------------------------------------------

  function getModalElements() {
    const modalEl = select(MODAL_SELECTOR);
    if (!modalEl) {
      console.error("globalModal root not found");
      return {};
    }

    const modalContent = select(".modal-content", false, modalEl);
    if (!modalContent) {
      console.error("No .modal-content found inside #globalModal");
      return {};
    }

    return { modalEl, modalContent };
  }

  function initModalWidgets(modalContent) {
    // Re-init any widgets inside the modal
    if (Bootstrap?.widgets?.Password?.init) {
      Bootstrap.widgets.Password.init();
    }
  }

  function applyModalOptions(modalEl, modalContent) {
    const headerEl = modalContent.querySelector(".modal-header");

    // Static / dismissible flag
    const staticFlag = headerEl?.dataset.modalStatic;
    const isStatic = toBool(staticFlag);

    const modal = bootstrap.Modal.getOrCreateInstance(modalEl, {
      backdrop: isStatic ? "static" : true,
      keyboard: !isStatic,
    });

    // Scrollable flag
    const scrollFlag = headerEl?.dataset.modalScrollable;
    const isScrollable = toBool(scrollFlag);

    const dialogEl = modalEl.querySelector(".modal-dialog");
    if (dialogEl) {
      dialogEl.classList.toggle("modal-dialog-scrollable", isScrollable);
    }

    return modal;
  }

  async function loadModalFromResponse(res, { show = true } = {}) {
    const { modalEl, modalContent } = getModalElements();
    if (!modalEl || !modalContent) return;

    const html = await res.text();
    modalContent.innerHTML = html;

    initModalWidgets(modalContent);
    const modal = applyModalOptions(modalEl, modalContent);

    if (show) {
      modal.show();
    }
  }

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

  async function handleJsonModalResponse(res) {
    const ct = res.headers.get("content-type") || "";
    if (!ct.includes("application/json")) {
      return false; // not JSON, let caller handle
    }

    let data;
    try {
      data = await res.json();
    } catch {
      return false;
    }

    const { modalEl } = getModalElements();
    if (!modalEl) return true;

    // Close modal if requested
    if (data.close) {
      const modal = bootstrap.Modal.getInstance(modalEl)
        || bootstrap.Modal.getOrCreateInstance(modalEl);
      modal.hide();
    }

    // Optional actions
    if (data.redirect) {
      window.location.assign(data.redirect);
    } else if (data.reload) {
      window.location.reload();
    }

    return true; // JSON handled
  }

  function setGlobalLoading(isLoading) {
    document.body.style.cursor = isLoading ? "wait" : "";
  }

  function setButtonLoading(button, isLoading) {
    if (!button) return;

    if (isLoading) {
      if (!button.dataset.originalHtml) {
        button.dataset.originalHtml = button.innerHTML;
      }
      button.disabled = true;
      const loadingText = button.getAttribute("data-loading-text");
      if (loadingText) {
        button.innerHTML = loadingText;
      }
    } else {
      button.disabled = false;
      if (button.dataset.originalHtml) {
        button.innerHTML = button.dataset.originalHtml;
      }
    }
  }

  // ----- Open modal on .js-modal click --------------------------------------

  on("click", document, async (e) => {
    const trigger = e.target.closest(".js-modal");
    if (!trigger) return;

    const url =
      trigger.getAttribute("data-form-url") ||
      trigger.getAttribute("data-url") ||
      trigger.getAttribute("href");

    if (!url || url === "#") return;
    e.preventDefault();

    const { modalEl, modalContent } = getModalElements();
    if (!modalEl || !modalContent) return;

    // If django-bootstrap-modal-forms is available, prefer it
    if (window.jQuery && typeof window.jQuery.fn.modalForm === "function") {
      window.jQuery(trigger).modalForm({ formURL: url, modalID: MODAL_SELECTOR });
      return;
    }

    const bsModal = bootstrap.Modal.getInstance(modalEl);

    // If modal is already shown, treat this as a "toggle":
    // close first, then load the new content in hidden.bs.modal
    if (bsModal && modalEl.classList.contains("show")) {
      pendingModalUrl = url;
      bsModal.hide();
      return;
    }

    setGlobalLoading(true);
    try {
      const res = await fetch(url, {
        headers: { "X-Requested-With": "XMLHttpRequest" },
      });

      // If unauthenticated or redirected, let handler take over
      if (res.status === 401 || res.redirected) {
        await handleAuthRedirect(res);
        return;
      }

      await loadModalFromResponse(res, { show: true });
    } catch (err) {
      console.error("Failed to load modal content:", err);
    } finally {
      setGlobalLoading(false);
    }
  });

  // ----- AJAX submit for forms inside the modal -----------------------------

  on("submit", document, async (e) => {
    const form = e.target;
    if (!(form instanceof HTMLFormElement)) return;

    // Only handle forms inside the global modal
    if (!form.closest(MODAL_SELECTOR)) return;

    e.preventDefault();

    const { modalEl, modalContent } = getModalElements();
    if (!modalEl || !modalContent) return;

    const formData = new FormData(form);
    const submitBtn =
      form.querySelector('button[id$="SubmitBtn"]') ||
      form.querySelector('button[type="submit"], input[type="submit"]');

    setGlobalLoading(true);
    setButtonLoading(submitBtn, true);

    try {
      const res = await fetch(form.action || window.location.href, {
        method: form.method || "POST",
        body: formData,
        headers: { "X-Requested-With": "XMLHttpRequest" },
      });

      // Redirect / auth handling
      if (res.status === 401 || res.redirected) {
        await handleAuthRedirect(res);
        return;
      }

      // JSON semantic responses: {close: true, redirect: "...", reload: true}
      const handledJson = await handleJsonModalResponse(res);
      if (handledJson) {
        return; // we've already handled close/redirect/reload
      }

      // Otherwise, treat it as a re-render (errors or success message)
      await loadModalFromResponse(res, { show: false });
    } catch (err) {
      console.error("Modal form submit failed:", err);
    } finally {
      setButtonLoading(submitBtn, false);
      setGlobalLoading(false);
    }
  });

  // ----- Misc: sanity check & confirm-text handling -------------------------

  // Sanity check that the global modal host exists
  on("DOMContentLoaded", document, () => {
    if (!select(MODAL_SELECTOR)) {
      console.error("globalModal NOT in DOM at DOMContentLoaded");
    }
  });

  // Enable/disable confirm button when modal is shown
  on("shown.bs.modal", document, (e) => {
    const modal = select(e.target);
    const input = select('input[data-required-text]', false, modal);
    const btn = select('button[id$="SubmitBtn"]', false, modal);
    if (!input || !btn) return;

    const required = input.dataset.requiredText || "";
    const check = () => {
      btn.disabled = input.value.trim() !== required;
    };

    // Avoid duplicate listeners if the modal is opened repeatedly
    input.removeEventListener("input", input._confirmHandler || (() => {}));
    input._confirmHandler = check;

    on("input", input, check);
    check();
  });

  // Cleanup + toggle-next-modal when modal is hidden
  on("hidden.bs.modal", document, async (e) => {
    const modal = select(e.target);
    const input = select('input[data-required-text]', false, modal);
    if (input && input._confirmHandler) {
      input.removeEventListener("input", input._confirmHandler);
      delete input._confirmHandler;
    }

    // If we have a pending URL, load that modal now and show it
    if (pendingModalUrl) {
      setGlobalLoading(true);
      try {
        const res = await fetch(pendingModalUrl, {
          headers: { "X-Requested-With": "XMLHttpRequest" },
        });

        if (res.status === 401 || res.redirected) {
          await handleAuthRedirect(res);
        } else {
          await loadModalFromResponse(res, { show: true });
        }
      } catch (err) {
        console.error("Failed to load toggled modal content:", err);
      } finally {
        pendingModalUrl = null;
        setGlobalLoading(false);
      }
    }
  });
})();
