(() => {
  const MODES = {
    "word-to-pdf": { accept: ".doc,.docx,.odt,.rtf", hint: "DOC, DOCX, ODT or RTF", exts: ["doc", "docx", "odt", "rtf"] },
    "pdf-to-word": { accept: ".pdf", hint: "PDF", exts: ["pdf"] },
  };

  const $ = (id) => document.getElementById(id);
  const form = $("form"), input = $("file"), drop = $("drop"), go = $("go"), status = $("status");
  let mode = "word-to-pdf";
  let file = null;
  let lastUrl = null;

  function setStatus(html, cls = "") {
    status.className = "status " + cls;
    status.innerHTML = html;
  }

  function escape(s) {
    return s.replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  }

  function setMode(m) {
    mode = m;
    document.querySelectorAll(".tab").forEach((t) => {
      const on = t.dataset.mode === m;
      t.classList.toggle("active", on);
      t.setAttribute("aria-selected", on);
    });
    input.accept = MODES[m].accept;
    $("drop-hint").textContent = `${MODES[m].hint} · up to ${window.MAX_MB} MB`;
    setFile(null);
  }

  function setFile(f) {
    file = null;
    setStatus("");
    if (f) {
      const ext = f.name.split(".").pop().toLowerCase();
      if (!MODES[mode].exts.includes(ext)) {
        setStatus(`Please choose a ${MODES[mode].hint} file.`, "error");
      } else if (f.size > window.MAX_MB * 1024 * 1024) {
        setStatus(`That file is larger than ${window.MAX_MB} MB.`, "error");
      } else {
        file = f;
      }
    }
    $("drop-text").innerHTML = file
      ? `<strong>${escape(file.name)}</strong>`
      : "<strong>Choose a file</strong> or drag it here";
    go.disabled = !file;
  }

  document.querySelectorAll(".tab").forEach((t) => t.addEventListener("click", () => setMode(t.dataset.mode)));
  input.addEventListener("change", () => setFile(input.files[0]));

  ["dragenter", "dragover"].forEach((e) =>
    drop.addEventListener(e, (ev) => { ev.preventDefault(); drop.classList.add("over"); }));
  ["dragleave", "drop"].forEach((e) =>
    drop.addEventListener(e, (ev) => { ev.preventDefault(); drop.classList.remove("over"); }));
  drop.addEventListener("drop", (ev) => setFile(ev.dataTransfer.files[0]));

  form.addEventListener("submit", async (ev) => {
    ev.preventDefault();
    if (!file) return;
    go.disabled = true;
    setStatus('<span class="spinner"></span>Converting…');

    const body = new FormData();
    body.append("file", file);
    try {
      const res = await fetch(`/api/convert/${mode}`, { method: "POST", body });
      if (!res.ok) {
        let msg = `Conversion failed (${res.status}).`;
        try { msg = (await res.json()).error || msg; } catch {}
        throw new Error(msg);
      }
      const blob = await res.blob();
      const outName = file.name.replace(/\.[^.]+$/, "") + (mode === "word-to-pdf" ? ".pdf" : ".docx");
      if (lastUrl) URL.revokeObjectURL(lastUrl);
      lastUrl = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = lastUrl;
      a.download = outName;
      a.click();
      setStatus(`Done! <a href="${lastUrl}" download="${escape(outName)}">Download ${escape(outName)}</a>`, "ok");
    } catch (err) {
      setStatus(escape(err.message || "Something went wrong."), "error");
    } finally {
      go.disabled = !file;
    }
  });

  setMode(mode);
})();
