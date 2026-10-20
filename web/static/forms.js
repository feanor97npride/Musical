// validação dos campos: aria-invalid acompanha o :user-invalid (erro só depois da interação) e o trecho confere início e fim
(() => {
  const sync = (event) => {
    const field = event.target;
    if (!field.matches?.("input, textarea")) return;
    if (field.matches(":user-invalid")) field.setAttribute("aria-invalid", "true");
    else field.removeAttribute("aria-invalid");
  };
  document.addEventListener("blur", sync, true); // blur e invalid não sobem na árvore: captura
  document.addEventListener("invalid", (event) => queueMicrotask(() => sync(event)), true); // tentativa de envio
  document.addEventListener("change", sync);
  document.addEventListener("input", (event) => { if (event.target.hasAttribute?.("aria-invalid")) sync(event); });

  const start = document.getElementById("clip_start");
  const end = document.getElementById("clip_end");
  const checkClip = () => {
    const wrong = start.value !== "" && end.value !== "" && Number(end.value) <= Number(start.value);
    end.setCustomValidity(wrong ? "O fim precisa ser depois do início." : "");
  };
  start.addEventListener("input", checkClip);
  end.addEventListener("input", checkClip);
})();
