// toca o MP3 escolhido; "Marcar início/fim" copia o tempo atual do player para o campo de trecho
const audioInput = document.getElementById("audio");
const player = document.getElementById("player");

audioInput.addEventListener("change", () => {
  const file = audioInput.files[0];
  if (player.src) URL.revokeObjectURL(player.src);
  player.hidden = !file;
  player.src = file ? URL.createObjectURL(file) : "";
});

for (const button of document.querySelectorAll("[data-mark]")) {
  button.addEventListener("click", () => {
    const field = document.getElementById(button.dataset.mark);
    field.value = player.currentTime.toFixed(1);
    field.dispatchEvent(new Event("input", { bubbles: true })); // a validação de fim > início do forms.js escuta "input"
  });
}
