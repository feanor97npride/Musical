// atalhos de geração: preenchem estilo, formato e cortes; o preset full também pede o segundo formato (presetNext)
const PRESETS = {
  personalizado: { label: "Personalizado", hint: "Você escolhe cada opção" },
  full: { label: "Full", hint: "16:9 inteiro e 9:16 em cortes de 90 s", format: "horizontal", cuts: "",
          next: { format: "vertical", cuts: "90" } },
  tiktok: { label: "TikTok", hint: "9:16 em cortes de 90 s", format: "vertical", cuts: "90" },
  yt: { label: "YouTube", hint: "16:9 com o vídeo inteiro", format: "horizontal", cuts: "" },
};

const presetBox = document.getElementById("presets");
for (const [key, preset] of Object.entries(PRESETS)) {
  const input = Object.assign(document.createElement("input"), { type: "radio", name: "preset", value: key });
  input.checked = key === "personalizado";
  const span = document.createElement("span");
  span.append(Object.assign(document.createElement("strong"), { textContent: preset.label }),
              Object.assign(document.createElement("small"), { textContent: preset.hint }));
  const label = document.createElement("label");
  label.className = "choice";
  label.append(input, span);
  presetBox.append(label);
}

// escolher um preset preenche os campos; o usuário pode mudar qualquer um depois
function choose(key) {
  const preset = PRESETS[key];
  presetNext = preset.next || null;
  if (!preset.format) return;
  form.elements["style"].value = "karaoke";
  form.elements["format"].value = preset.format;
  form.elements["cuts"].value = preset.cuts;
}

presetBox.addEventListener("change", (event) => choose(event.target.value));

// mudar qualquer campo na mão volta para "Personalizado" (valor mudado por código não dispara "change")
form.addEventListener("change", (event) => {
  if (!["style", "format", "background", "cuts"].includes(event.target.name)) return; // letra e MP3 não mudam o preset
  presetNext = null;
  form.elements["preset"].value = "personalizado";
});
