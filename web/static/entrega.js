// entrega do job pronto: pacote para postar (ZIP) e os vídeos brutos (usa api, show, finish e failure do app.js)
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
  output.append(video, packButton(id), link);
}

function showCuts(id, names) {
  finish();
  show(names.length + " cortes prontos");
  detail.textContent = "";
  output.innerHTML = "";
  output.append(packButton(id), ...names.map((name, index) => {
    const link = document.createElement("a");
    link.className = "download";
    link.href = "#";
    link.textContent = `Baixar corte ${index + 1} de ${names.length}`;
    link.addEventListener("click", (event) => {
      event.preventDefault();
      download(`/jobs/${id}/video?n=${index}`, name);
    });
    return link;
  }));
}

// o pacote traz as cópias prontas para subir e o postar.txt com os textos de cada parte
function packButton(id) {
  const button = document.createElement("button");
  button.type = "button";
  button.className = "primary";
  button.textContent = "Baixar pacote para postar (ZIP)";
  button.addEventListener("click", () => download(`/jobs/${id}/pacote.zip`, "pacote.zip"));
  return button;
}

// o download passa pelo fetch para levar a senha no cabeçalho; um link comum não levaria
async function download(path, name) {
  try {
    const response = await api(path);
    if (!response.ok) return failure(response);
    const link = Object.assign(document.createElement("a"), { href: URL.createObjectURL(await response.blob()), download: name });
    link.click();
  } catch (error) {
    show("Não consegui baixar. Confira a conexão com o servidor.", true);
  }
}
