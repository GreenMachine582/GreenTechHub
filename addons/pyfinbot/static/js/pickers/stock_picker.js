document.addEventListener("picker:use", function (e) {
  const { row } = e.detail || {};
  if (!row) return;

  // Update your fields
  const idEl  = document.getElementById("stock_id");
  const disp  = document.getElementById("stock_display");
  if (idEl)  idEl.value = row.id ?? "";
  if (disp)  disp.value = `${row.market ?? ""}:${row.symbol ?? ""} - ${row.name ?? ""}`
                            .replace(/^:| - $/g, "").trim();
});