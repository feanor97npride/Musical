const form = document.getElementById("form");
const submit = document.getElementById("submit");
const preview = document.getElementById("preview");
const result = document.getElementById("result");
const stage = document.getElementById("stage");
const detail = document.getElementById("detail");
const output = document.getElementById("output");
const jobProgress = document.getElementById("job-progress");
const serverInput = document.getElementById("server");
const tokenInput = document.getElementById("token");
const SERVER_KEY = "lyricVideo.server";
const FIXED_SERVER = "https://whimsical.musicas.space"; // único endereço que o link do iniciador pode preencher
let timer = null;

try { serverInput.value = localStorage.getItem(SERVER_KEY) || ""; } catch (error) { /* navegador sem armazenamento */ }
serverInput.addEventListener("change", () => {
  try { localStorage.setItem(SERVER_KEY, serverInput.value.trim()); } catch (error) { /* nada a fazer */ }
});

// link do iniciador: #server=<endereço fixo> preenche o campo (sem gravar no localStorage)
(function applyServerFromHash() {
  const value = new URLSearchParams(location.hash.slice(1)).get("server");
  if (!value) return;
  history.replaceState(null, "", location.pathname + location.search);
  if (value !== FIXED_SERVER) return;
  serverInput.value = value;
  const notice = document.getElementById("hash-notice");
  notice.textContent = "Servidor preenchido por link: " + value + ". Se você não abriu pelo iniciador, não digite a senha.";
  notice.hidden = false;
  document.querySelector("details.server").open = true; // o aviso fica dentro de "Servidor e senha"
})();

function api(path, options = {}) {
  const base = serverInput.value.trim().replace(/\/+$/, "");
  const headers = { ...(options.headers || {}) };
  if (tokenInput.value) headers["X-Access-Token"] = tokenInput.value;
  return fetch(base + path, { ...options, headers });
}

function show(message, isError) {
  result.classList.add("visible");
  if (stage.textContent !== message) stage.textContent = message; // mesmo texto não é relido pelo leitor de tela
  stage.className = isError ? "stage error" : "stage";
}

function finish() {
  clearInterval(timer);
  jobProgress.hidden = true;
  submit.disabled = preview.disabled = false;
}

async function failure(response) {
  const body = await response.json().catch(() => ({}));
  finish();
  show(body.detail || "O servidor respondeu com erro " + response.status, true);
}

async function showVideo(id, videos) {
  if (videos.length > 1) return showCuts(id, videos);
  const response = await api(`/jobs/${id}/video`);
  if (!response.ok) return failure(response);
  const url = URL.createObjectURL(await response.blob());
  finish();
  show("Vídeo pronto");
  detail.textContent = "";
  output.innerHTML = "";
  const video = document.createElement("video");
  video.controls = true;
  video.src = url;
  const link = document.createElement("a");
  link.className = "download";
  link.href = url;
  link.download = "lyric-video.mp4";
  link.textContent = "Baixar MP4";
  output.append(video, link);
}

function showCuts(id, names) {
  finish();
  show(names.length + " cortes prontos");
  detail.textContent = "";
  output.innerHTML = "";
  output.append(...names.map((name, index) => {
    const link = document.createElement("a");
    link.className = "download";
    link.href = "#";
    link.textContent = `Baixar corte ${index + 1} de ${names.length}`;
    link.addEventListener("click", (event) => {
      event.preventDefault();
      downloadCut(id, index, name);
    });
    return link;
  }));
}

// o download passa pelo fetch para levar a senha no cabeçalho; um link comum não levaria
async function downloadCut(id, index, name) {
  try {
    const response = await api(`/jobs/${id}/video?n=${index}`);
    if (!response.ok) return failure(response);
    const link = document.createElement("a");
    link.href = URL.createObjectURL(await response.blob());
    link.download = name;
    link.click();
  } catch (error) {
    show("Não consegui baixar o corte. Confira a conexão com o servidor.", true);
  }
}

async function poll(id) {
  try {
    const response = await api(`/jobs/${id}`);
    if (!response.ok) return failure(response);
    const job = await response.json();
    if (job.status === "error") {
      finish();
      show("Falhou: " + job.stage, true);
      detail.textContent = job.message;
    } else if (job.status === "done") {
      clearInterval(timer);
      await showVideo(id, job.videos);
    } else {
      show(job.total ? `Etapa ${job.step} de ${job.total}: ${job.stage}` : job.stage + "...");
      detail.textContent = job.message;
      jobProgress.value = job.progress;
      jobProgress.hidden = !job.total;
    }
  } catch (error) {
    finish();
    show("Não consegui falar com o servidor. Confira o endereço e a conexão.", true);
  }
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  submit.disabled = preview.disabled = true;
  output.innerHTML = "";
  show("Enviando...");
  detail.textContent = "";
  let response;
  try {
    response = await api("/jobs", { method: "POST", body: new FormData(form) });
  } catch (error) {
    finish();
    show("Não consegui enviar. Confira o endereço do servidor e a conexão.", true);
    return;
  }
  if (!response.ok) return failure(response);
  const body = await response.json();
  clearInterval(timer);
  timer = setInterval(() => poll(body.id), 2000);
  poll(body.id);
  result.scrollIntoView({ block: "nearest", behavior: matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth" });
});

// prévia: envia o mesmo formulário com o trecho de 0 a 30 s; o FormData é montado na hora do envio,
// então dá para limpar o trecho logo em seguida e um envio normal não sai com 30 s por engano
preview.addEventListener("click", () => {
  const fields = ["cuts", "clip_start", "clip_end"].map((name) => form.elements[name]); // cuts é um grupo de rádios
  const saved = fields.map((field) => field.value);
  const set = (values) => {
    fields.forEach((field, index) => { field.value = values[index]; });
    // valor mudado por código não dispara "input": avisa a validação do trecho (forms.js)
    for (const name of ["clip_start", "clip_end"]) form.elements[name].dispatchEvent(new Event("input", { bubbles: true }));
  };
  set(["", "0", "30"]); // prévia é um trecho só: não junta com cortes
  form.requestSubmit();
  set(saved); // devolve o que o usuário tinha digitado
});
