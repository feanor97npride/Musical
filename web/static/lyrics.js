// gerar letra com IA: envia o contexto para /lyrics e preenche letra, estilo e informações para postar (usa api() do app.js)
(() => {
  const contextInput = document.getElementById("context");
  const lyricsInput = document.getElementById("lyrics");
  const writeButton = document.getElementById("write-lyrics");
  const status = document.getElementById("lyrics-status");
  // campos da resposta que viram texto direto; hashtags é uma lista e é tratada à parte
  const FILLED = { style: "suno-style", youtube_title: "yt-title", youtube_description: "yt-description", tiktok_caption: "tiktok-caption" };

  function say(text, isError) {
    status.textContent = text;
    status.className = isError ? "hint error" : "hint";
  }

  writeButton.addEventListener("click", async () => {
    if (!contextInput.value.trim()) return say("Escreva o contexto da música primeiro.", true);
    if (lyricsInput.value.trim() && !confirm("Trocar a letra que já está no campo pela letra nova?")) return;
    writeButton.disabled = lyricsInput.readOnly = true;  // a letra nova não apaga o que for digitado durante a espera
    say("Escrevendo a letra... pode levar até 1 minuto e meio.");
    try {
      const body = new FormData();
      body.append("context", contextInput.value);
      const response = await api("/lyrics", { method: "POST", body });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) return say(data.detail || "O servidor respondeu com erro " + response.status, true);
      lyricsInput.value = data.lyrics;
      for (const [key, id] of Object.entries(FILLED)) document.getElementById(id).value = data[key] || "";
      document.getElementById("hashtags").value = (data.hashtags || []).join(" ");
      document.getElementById("posting").hidden = false;
      say("Letra pronta: " + data.title + ". Revise antes de usar.");
    } catch (error) {
      say("Não consegui falar com o servidor, ou ele demorou demais. Confira o endereço e tente de novo.", true);
    } finally {
      writeButton.disabled = lyricsInput.readOnly = false;
    }
  });

  // copia o campo indicado no data-copy; sem permissão de área de transferência, deixa o texto selecionado para Ctrl+C
  function copyFrom(field, done) {
    if (!field.value.trim()) return say("Ainda não há nada para copiar. Gere a letra primeiro.", true);
    // Promise.resolve: sem navigator.clipboard (página fora de https), o erro cai no mesmo aviso
    Promise.resolve().then(() => navigator.clipboard.writeText(field.value)).then(
      () => say(done),
      () => {
        field.select();
        say("Não consegui copiar sozinho. O texto ficou selecionado: use Ctrl+C.", true);
      },
    );
  }

  document.querySelectorAll("[data-copy]").forEach((button) => {
    button.addEventListener("click", () => copyFrom(document.getElementById(button.dataset.copy), button.dataset.done));
  });
})();
