// Drag-and-drop, submit-via-fetch, download, and a celebratory finish.
(function () {
  const form = document.getElementById("tool-form");
  if (!form) return;

  const input = document.getElementById("file-input");
  const dropzone = document.getElementById("dropzone");
  const list = document.getElementById("file-list");
  const runBtn = document.getElementById("run-btn");
  const errorEl = document.getElementById("error");
  const resultEl = document.getElementById("result");
  const toastEl = document.getElementById("toast");
  const multiple = form.dataset.multiple === "true";
  const requiresFile = form.dataset.requiresFile !== "false";
  const action = form.dataset.action;

  function setFiles(fileList) {
    const dt = new DataTransfer();
    const files = multiple ? [...fileList] : fileList.length ? [fileList[0]] : [];
    files.forEach((f) => dt.items.add(f));
    input.files = dt.files;
    render();
  }

  function render() {
    list.innerHTML = "";
    for (const f of input.files) {
      const li = document.createElement("li");
      li.textContent = f.name;
      list.appendChild(li);
    }
    runBtn.disabled = requiresFile && input.files.length === 0;
  }

  if (requiresFile) {
    dropzone.addEventListener("click", () => input.click());
    dropzone.addEventListener("keydown", (e) => {
      if (e.key === "Enter" || e.key === " ") { e.preventDefault(); input.click(); }
    });
    input.addEventListener("change", () => render());

    ["dragenter", "dragover"].forEach((ev) =>
      dropzone.addEventListener(ev, (e) => { e.preventDefault(); dropzone.classList.add("dragover"); })
    );
    ["dragleave", "drop"].forEach((ev) =>
      dropzone.addEventListener(ev, (e) => { e.preventDefault(); dropzone.classList.remove("dragover"); })
    );
    dropzone.addEventListener("drop", (e) => {
      if (e.dataTransfer?.files?.length) setFiles(e.dataTransfer.files);
    });
  } else {
    runBtn.disabled = false;
  }

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    if (requiresFile && !input.files.length) return;
    errorEl.hidden = true;
    resultEl.hidden = true;
    resultEl.innerHTML = "";
    runBtn.classList.add("busy");
    runBtn.disabled = true;

    try {
      const data = new FormData(form);
      const res = await fetch(action, { method: "POST", body: data });
      if (!res.ok) {
        let detail = `Error ${res.status}`;
        try { detail = (await res.json()).detail || detail; } catch (_) {}
        throw new Error(detail);
      }

      const type = res.headers.get("Content-Type") || "";
      if (type.includes("application/json")) {
        renderInline(await res.json());
      } else {
        const blob = await res.blob();
        const name = filenameFrom(res.headers.get("Content-Disposition")) || "result";
        downloadBlob(blob, name);
        showDownloadNote(name);
      }
      celebrate();
    } catch (err) {
      errorEl.textContent = err.message || "Something went wrong.";
      errorEl.hidden = false;
    } finally {
      runBtn.classList.remove("busy");
      runBtn.disabled = requiresFile && input.files.length === 0;
    }
  });

  // --- Inline results --------------------------------------------------------
  function showResultNote(text) {
    resultEl.innerHTML = "";
    const p = document.createElement("p");
    p.className = "result-note";
    p.textContent = text;
    resultEl.appendChild(p);
    resultEl.hidden = false;
  }

  // The filename is server-controlled but can derive from a user upload, so it
  // is inserted as text (never HTML) to avoid any injection via the name.
  function showDownloadNote(name) {
    resultEl.innerHTML = "";
    const p = document.createElement("p");
    p.className = "result-note";
    p.append("Done — downloaded ");
    const strong = document.createElement("strong");
    strong.textContent = name;
    p.appendChild(strong);
    resultEl.appendChild(p);
    resultEl.hidden = false;
  }

  function renderInline(data) {
    if (data.render === "palette") return renderPalette(data.colors || []);
    showResultNote("Done.");
  }

  function renderPalette(colors) {
    resultEl.innerHTML = "";
    const grid = document.createElement("div");
    grid.className = "swatches";
    for (const c of colors) {
      const sw = document.createElement("button");
      sw.type = "button";
      sw.className = "swatch";
      sw.style.setProperty("--c", c.hex);
      sw.innerHTML = `<span class="chip" style="background:${c.hex}"></span><code>${c.hex}</code>`;
      sw.title = `Copy ${c.hex}`;
      sw.addEventListener("click", () => copy(c.hex));
      grid.appendChild(sw);
    }
    resultEl.appendChild(grid);
    resultEl.hidden = false;
  }

  async function copy(text) {
    try {
      await navigator.clipboard.writeText(text);
      toast(`Copied ${text}`);
    } catch (_) {
      toast("Copy failed");
    }
  }

  let toastTimer;
  function toast(msg) {
    toastEl.textContent = msg;
    toastEl.hidden = false;
    toastEl.classList.add("show");
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => {
      toastEl.classList.remove("show");
      setTimeout(() => (toastEl.hidden = true), 250);
    }, 1400);
  }

  function filenameFrom(header) {
    if (!header) return null;
    const m = /filename="?([^"]+)"?/.exec(header);
    return m ? m[1] : null;
  }

  function downloadBlob(blob, name) {
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = name;
    document.body.appendChild(a);
    a.click();
    a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }

  // --- Tiny dependency-free confetti burst -----------------------------------
  function celebrate() {
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    const canvas = document.getElementById("confetti");
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    const dpr = window.devicePixelRatio || 1;
    canvas.width = innerWidth * dpr;
    canvas.height = innerHeight * dpr;
    ctx.scale(dpr, dpr);

    const colors = ["#7c5cff", "#2dd4bf", "#ffd166", "#ff6b6b", "#9a7bff"];
    const parts = Array.from({ length: 140 }, () => ({
      x: innerWidth / 2,
      y: innerHeight / 3,
      vx: (Math.random() - 0.5) * 12,
      vy: Math.random() * -14 - 4,
      size: Math.random() * 6 + 4,
      color: colors[(Math.random() * colors.length) | 0],
      rot: Math.random() * Math.PI,
      vr: (Math.random() - 0.5) * 0.4,
      life: 1,
    }));

    let raf;
    (function frame() {
      ctx.clearRect(0, 0, innerWidth, innerHeight);
      let alive = false;
      for (const p of parts) {
        p.vy += 0.4; // gravity
        p.x += p.vx; p.y += p.vy; p.rot += p.vr; p.life -= 0.012;
        if (p.life > 0 && p.y < innerHeight + 20) {
          alive = true;
          ctx.save();
          ctx.globalAlpha = Math.max(p.life, 0);
          ctx.translate(p.x, p.y);
          ctx.rotate(p.rot);
          ctx.fillStyle = p.color;
          ctx.fillRect(-p.size / 2, -p.size / 2, p.size, p.size * 0.6);
          ctx.restore();
        }
      }
      if (alive) raf = requestAnimationFrame(frame);
      else { cancelAnimationFrame(raf); ctx.clearRect(0, 0, innerWidth, innerHeight); }
    })();
  }
})();
