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

  // preenche a letra e os textos para postar; usado pela geração e pelo item aberto do histórico
  function fill(data) {
    lyricsInput.value = data.lyrics;
    for (const [key, id] of Object.entries(FILLED)) document.getElementById(id).value = data[key] || "";
    document.getElementById("hashtags").value = (data.hashtags || []).join(" ");
    document.getElementById("posting").hidden = false;
    // o pacote para postar leva esses textos; o servidor recusa textos pela metade, então só vai se estiverem completos
    const posting = { youtube_title: data.youtube_title, youtube_description: data.youtube_description, tiktok_caption: data.tiktok_caption, hashtags: data.hashtags };
    document.getElementById("draft").value = Object.values(posting).every(Boolean) ? JSON.stringify(posting) : "";
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
      fill(data);
      say("Letra pronta: " + data.title + ". Revise antes de usar.");
      loadHistory();
    } catch (error) {
      say("Não consegui falar com o servidor, ou ele demorou demais. Confira o endereço e tente de novo.", true);
    } finally {
      writeButton.disabled = lyricsInput.readOnly = false;
    }
  });

  // histórico: as letras geradas ficam guardadas no computador do servidor; a lista mostra só data e título
  const historyList = document.getElementById("history-list");
  const historyStatus = document.getElementById("history-status");

  function historyItem(item) {
    const li = document.createElement("li");
    const label = document.createElement("span");
    label.textContent = `${new Date(item.created_at).toLocaleString("pt-BR")} · ${item.title}`;
    const open = document.createElement("button");
    open.type = "button";
    open.textContent = "Abrir";
    open.addEventListener("click", async () => {
      if (lyricsInput.value.trim() && !confirm("Trocar a letra que já está no campo pela letra do histórico?")) return;
      const response = await api(`/historico/${item.id}`);
      if (!response.ok) return (historyStatus.textContent = "Não consegui abrir esta letra do histórico.");
      fill(await response.json());
      historyStatus.textContent = "Letra aberta do histórico. Revise antes de usar.";
    });
    const remove = document.createElement("button");
    remove.type = "button";
    remove.textContent = "Apagar";
    remove.addEventListener("click", async () => {
      if (!confirm("Apagar esta letra do histórico?")) return;
      await api(`/historico/${item.id}`, { method: "DELETE" });
      loadHistory();
    });
    li.append(label, open, remove);
    return li;
  }

  async function loadHistory() {
    try {
      const response = await api("/historico");
      if (!response.ok) throw new Error(String(response.status));
      const items = await response.json();
      historyList.replaceChildren(...items.map(historyItem));
      historyStatus.textContent = items.length ? "" : "Nenhuma letra gerada ainda.";
    } catch (error) {
      historyList.replaceChildren();
      historyStatus.textContent = "Não consegui carregar o histórico. Confira o endereço e a senha do servidor.";
    }
  }
  loadHistory();

  // aviso único (visível e anunciado): o bloco da IA pode estar fechado, então o aviso de copiar não fica nele
  const announcer = document.getElementById("announcer");
  let announceTimer = null;
  function announce(text) {
    clearTimeout(announceTimer);
    announcer.textContent = "";
    setTimeout(() => { announcer.textContent = text; }, 50); // limpar antes faz o mesmo texto ser anunciado de novo
    announceTimer = setTimeout(() => { announcer.textContent = ""; }, 3500);
  }

  // copia o campo indicado no data-copy; sem permissão de área de transferência, deixa o texto selecionado para Ctrl+C
  function copyFrom(button, field, done) {
    if (!field.value.trim()) return announce("Ainda não há nada para copiar. Gere a letra primeiro.");
    // Promise.resolve: sem navigator.clipboard (página fora de https), o erro cai no mesmo aviso
    Promise.resolve().then(() => navigator.clipboard.writeText(field.value)).then(
      () => {
        announce(done);
        button.dataset.copied = "";
        setTimeout(() => delete button.dataset.copied, 1500);
      },
      () => {
        field.select();
        announce("Não consegui copiar sozinho. O texto ficou selecionado: use Ctrl+C.");
      },
    );
  }

  document.querySelectorAll("[data-copy]").forEach((button) => {
    button.addEventListener("click", () => copyFrom(button, document.getElementById(button.dataset.copy), button.dataset.done));
  });
})();
