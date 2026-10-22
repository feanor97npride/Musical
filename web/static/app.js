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
const JOB_KEY = "lyricVideo.job";
const FIXED_SERVER = "https://whimsical.musicas.space"; // único endereço que o link do iniciador pode preencher
let timer = null;
let failures = 0; // falhas de rede seguidas: a página só desiste depois de algumas

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

// o id do envio fica no navegador para a página retomar após recarregar; o estado continua no servidor
function rememberJob(id) { try { localStorage.setItem(JOB_KEY, id); } catch (error) { /* sem armazenamento: não retoma */ } }
function forgetJob() { try { localStorage.removeItem(JOB_KEY); } catch (error) { /* nada a fazer */ } }
function recallJob() { try { return localStorage.getItem(JOB_KEY); } catch (error) { return null; } }

async function failure(response) {
  const body = await response.json().catch(() => ({}));
  finish();
  show(body.detail || "O servidor respondeu com erro " + response.status, true);
}

async function poll(id) {
  try {
    const response = await api(`/jobs/${id}`);
    failures = 0;
    if (response.status === 404) { // o servidor reiniciou: a fila fica só na memória
      forgetJob();
      finish();
      show("O servidor reiniciou e perdeu este envio. Envie de novo.", true);
      return;
    }
    if (!response.ok) return failure(response);
    const job = await response.json();
    if (job.status === "error") {
      forgetJob();
      finish();
      show("Falhou: " + job.stage, true);
      detail.textContent = job.message;
    } else if (job.status === "done") {
      forgetJob();
      clearInterval(timer);
      await showVideo(id, job.videos);
    } else {
      show(job.total ? `Etapa ${job.step} de ${job.total}: ${job.stage}` : job.stage + "...");
      detail.textContent = job.message;
      jobProgress.value = job.progress;
      jobProgress.hidden = !job.total;
    }
  } catch (error) {
    failures += 1;
    if (failures < 5) return; // uma falha de rede não para o acompanhamento (cerca de 10 s seguidos param)
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
  rememberJob(body.id);
  failures = 0;
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

// envio feito antes de recarregar a página: retoma o acompanhamento
const pending = recallJob();
if (pending) {
  timer = setInterval(() => poll(pending), 2000);
  poll(pending);
}
