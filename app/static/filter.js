// Live-filter the portal grid by tool name/description.
(function () {
  const input = document.getElementById("filter");
  if (!input) return;
  const tiles = [...document.querySelectorAll(".tile")];
  const families = [...document.querySelectorAll(".family")];
  const empty = document.querySelector(".empty");
  const emptyQ = document.getElementById("empty-q");

  input.addEventListener("input", () => {
    const q = input.value.trim().toLowerCase();
    let visible = 0;
    for (const tile of tiles) {
      const match = !q || tile.dataset.name.includes(q);
      tile.style.display = match ? "" : "none";
      if (match) visible++;
    }
    for (const fam of families) {
      const any = [...fam.querySelectorAll(".tile")].some((t) => t.style.display !== "none");
      fam.style.display = any ? "" : "none";
    }
    if (empty) {
      empty.hidden = visible !== 0;
      if (emptyQ) emptyQ.textContent = q;
    }
  });
})();
