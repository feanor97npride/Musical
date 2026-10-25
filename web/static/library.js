// música da pasta do Drive: a lista vem do servidor; a seção só aparece se DRIVE_INPUT_DIR estiver configurado (usa globals de app.js)
const library = document.getElementById("library");
const driveOpen = document.getElementById("drive-open");
const heading = Object.assign(document.createElement("h3"), { textContent: "Música da pasta do Drive" }); // h3: não entra na numeração das seções
const label = Object.assign(document.createElement("label"), { htmlFor: "library-song", textContent: "Música" });
const select = Object.assign(document.createElement("select"), { id: "library-song" });
const button = Object.assign(document.createElement("button"), { type: "button", className: "primary", textContent: "Gerar esta música" });
const status = Object.assign(document.createElement("p"), { className: "hint" });
status.setAttribute("aria-live", "polite");
library.append(heading, label, select, button, status);

async function loadSongs() {
  try {
    const response = await api("/biblioteca");
    if (!response.ok) return; // sem pasta configurada ou sem servidor: a seção continua escondida
    const { songs } = await response.json();
    select.replaceChildren(...songs.map((song) => new Option(song, song)));
    button.disabled = songs.length === 0;
    status.textContent = songs.length ? "" : "Nenhuma música na pasta. Cada música precisa de uma subpasta com um MP3 e um TXT.";
    driveOpen.hidden = false;
  } catch (error) { /* sem conexão: o botão continua escondido */ }
}

// o botão abre e fecha a lista dentro do cartão Música
driveOpen.addEventListener("click", () => {
  library.hidden = !library.hidden;
  driveOpen.textContent = library.hidden ? "Do Drive" : "Fechar Drive";
});

button.addEventListener("click", async () => {
  if (!select.value) return;
  if (submit.disabled) { show("Espere a música atual terminar antes de gerar outra.", true); return; }
  if (!form.elements["confirm"].checked) { show("Marque a caixa de autorização antes de gerar.", true); return; }
  const params = new URLSearchParams({
    style: form.elements["style"].value,
    background: form.elements["background"].value,
    format: form.elements["format"].value,
    cuts: form.elements["cuts"].value,
    confirm: "true",
  });
  submit.disabled = preview.disabled = true;
  output.innerHTML = "";
  output2.innerHTML = "";
  show("Enviando...");
  detail.textContent = "";
  let response;
  try {
    response = await api(`/biblioteca/${encodeURIComponent(select.value)}/jobs`, { method: "POST", body: params });
  } catch (error) {
    finish();
    show("Não consegui enviar. Confira o endereço do servidor e a conexão.", true);
    return;
  }
  if (!response.ok) return failure(response);
  const body = await response.json();
  rememberJob(body.id);
  chainNext = null;
  failures = 0;
  clearInterval(timer);
  timer = setInterval(() => poll(body.id), 2000);
  poll(body.id);
});

loadSongs();
// a senha e o endereço podem mudar depois do primeiro carregamento: a lista tenta de novo
document.getElementById("token").addEventListener("change", loadSongs);
document.getElementById("server").addEventListener("change", loadSongs);
