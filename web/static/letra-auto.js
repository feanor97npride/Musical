// letra pelo áudio: envia só o MP3 e põe o texto gerado no campo de letra, para revisão (usa globals de app.js)
const lyricsField = document.getElementById("lyrics");
const letraButton = Object.assign(document.createElement("button"), { type: "button", className: "secondary", textContent: "Gerar letra pelo áudio" });
const letraHint = Object.assign(document.createElement("p"), { className: "hint", textContent: "Revise a letra antes de gerar o vídeo. Música cantada costuma sair com erros." });
lyricsField.after(letraButton, letraHint);

letraButton.addEventListener("click", async () => {
  const audio = form.elements["audio"].files[0];
  if (!audio) { show("Escolha o MP3 antes de gerar a letra.", true); return; }
  if (submit.disabled) { show("Espere o envio atual terminar.", true); return; }
  const body = new FormData();
  body.append("audio", audio);
  submit.disabled = preview.disabled = true;
  output.replaceChildren();
  output2.replaceChildren();
  show("Enviando o áudio para gerar a letra...");
  let response;
  try {
    response = await api("/letra", { method: "POST", body });
  } catch (error) {
    finish();
    show("Não consegui enviar. Confira o endereço do servidor e a conexão.", true);
    return;
  }
  if (!response.ok) return failure(response);
  const job = await response.json();
  rememberJob(job.id);
  chainNext = null;
  failures = 0;
  clearInterval(timer);
  timer = setInterval(() => poll(job.id), 2000);
  poll(job.id);
});

// chamado por app.js quando o job de letra termina
async function loadLetra(id) {
  const response = await api(`/jobs/${id}/letra`);
  if (!response.ok) return failure(response);
  lyricsField.value = await response.text();
  finish();
  show("Letra gerada. Revise antes de gerar o vídeo.");
  detail.textContent = "";
}
