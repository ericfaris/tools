// Design-system showcase: reads real computed token values from styles.css
// (no hand-typed values that can drift) and wires the few interactive demos.
(function () {
  const root = getComputedStyle(document.documentElement);

  function val(name) {
    return root.getPropertyValue(name).trim();
  }

  // Fill every [data-token] element with its live computed value.
  document.querySelectorAll("[data-token]").forEach((el) => {
    const name = el.getAttribute("data-token");
    const v = val(name);
    const out = el.querySelector(".token-value");
    if (out) out.textContent = v;
  });

  // Light/dark preview toggle. The real app has no manual toggle (it follows
  // the OS prefers-color-scheme, by design — see DESIGN.md §2) — this control
  // exists only so both palettes can be audited on one page without changing
  // your OS setting. It works via a small duplicate of the dark token block,
  // scoped to [data-preview-theme="dark"], defined in this page's own <style>
  // (not in styles.css) purely for that preview purpose.
  const toggle = document.getElementById("theme-toggle");
  if (toggle) {
    toggle.addEventListener("click", () => {
      const cur = document.documentElement.dataset.previewTheme;
      const next = cur === "dark" ? "light" : "dark";
      document.documentElement.dataset.previewTheme = next;
      toggle.textContent = next === "dark" ? "Preview: Dark" : "Preview: Light";
      toggle.setAttribute("aria-pressed", String(next === "dark"));
      // Re-read tokens for the new scheme so swatch labels stay accurate.
      const r2 = getComputedStyle(document.documentElement);
      document.querySelectorAll("[data-token]").forEach((el) => {
        const name = el.getAttribute("data-token");
        const out = el.querySelector(".token-value");
        if (out) out.textContent = r2.getPropertyValue(name).trim();
      });
    });
  }

  // Simulate-run demo: toggles the real .run/.busy/:disabled states used on
  // every tool page, so the spinner and press motion can be checked live.
  const demoRun = document.getElementById("demo-run");
  if (demoRun) {
    demoRun.addEventListener("click", () => {
      if (demoRun.classList.contains("busy")) return;
      demoRun.classList.add("busy");
      demoRun.disabled = true;
      setTimeout(() => {
        demoRun.classList.remove("busy");
        demoRun.disabled = false;
      }, 1600);
    });
  }

  // Dropzone demo: click toggles the real .dragover state (a live drag isn't
  // available on a static preview, so a click stands in for it).
  const demoDropzone = document.getElementById("demo-dropzone");
  if (demoDropzone) {
    demoDropzone.addEventListener("click", (e) => {
      e.preventDefault();
      demoDropzone.classList.toggle("dragover");
    });
  }

  // Toast demo
  const toastBtn = document.getElementById("demo-toast-btn");
  const toastEl = document.getElementById("demo-toast");
  if (toastBtn && toastEl) {
    let timer;
    toastBtn.addEventListener("click", () => {
      toastEl.hidden = false;
      toastEl.classList.add("show");
      clearTimeout(timer);
      timer = setTimeout(() => {
        toastEl.classList.remove("show");
        setTimeout(() => (toastEl.hidden = true), 250);
      }, 1400);
    });
  }

  // Copy-hex swatches (mirrors the real Color Picker tool behavior).
  document.querySelectorAll(".ds-swatch").forEach((sw) => {
    sw.addEventListener("click", async () => {
      const hex = sw.dataset.hex;
      try {
        await navigator.clipboard.writeText(hex);
        sw.classList.add("copied");
        setTimeout(() => sw.classList.remove("copied"), 900);
      } catch (_) {
        /* clipboard may be unavailable in this context — non-critical */
      }
    });
  });
})();
