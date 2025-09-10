
import { on } from "../helpers.js";

const SHAKE_MS = 250;

/** Tiny nudge animation without CSS file dependency */
function nudge(btn) {
  btn.style.transition = "transform .05s";
  let i = 0, int = setInterval(() => {
    btn.style.transform = `translateX(${i % 2 ? -3 : 3}px)`;
    if (++i > 5) { clearInterval(int); btn.style.transform = ""; btn.style.transition = ""; }
  }, SHAKE_MS / 6);
}

function ensurePickerTarget(btn, modal) {
  if (btn.dataset.pickerTable) return btn.dataset.pickerTable;
  // Try to find a Tabulator root with an id inside this modal
  const first =
    modal.querySelector('.tabulator-widget[id]') ||
    modal.querySelector('.tabulator[id]') ||
    modal.querySelector('[data-tabulator][id]');
  if (first?.id) btn.dataset.pickerTable = `#${first.id}`;
  return btn.dataset.pickerTable;
}

function bindPickerUseButtons(modal) {
  modal.querySelectorAll('[data-role="picker-use"]').forEach((btn) => {
    if (btn._boundPickerUse) return;
    btn._boundPickerUse = true;

    btn.addEventListener("click", () => {
      const selector = ensurePickerTarget(btn, modal);
      let tableEl = selector ? modal.querySelector(selector) : null;
      if (!tableEl) tableEl = modal.querySelector('.tabulator-widget, .tabulator, [data-tabulator]');
      const table = tableEl && tableEl._tabulator;

      if (!table) {
        console.warn("Picker: Tabulator instance not found");
        return;
      }

      const sel = table.getSelectedData?.() || [];
      if (!sel.length) { nudge(btn); return; }

      // Fire a generic event for page-specific code to consume
      btn.dispatchEvent(new CustomEvent("picker:use", {
        detail: { row: sel[0], rows: sel, table, tableEl },
        bubbles: true,
      }));

      // Close modal
      const inst = bootstrap.Modal.getInstance(modal) || new bootstrap.Modal(modal);
      inst.hide();
    });
  });
}

/** Public init: call once on page load */
export function initModalPickers() {
  // When any Bootstrap modal is shown, (re)bind its buttons
  on('shown.bs.modal', document, (e) => {
    const modal = e.target;
    bindPickerUseButtons(modal);
  });
}

// Auto-init if included directly without explicit init
if (!window.__GTH_MODAL_PICKERS_INITIALISED__) {
  window.__GTH_MODAL_PICKERS_INITIALISED__ = true;
  initModalPickers();
}
