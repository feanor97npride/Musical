# Fluxo n8n: avisar quando o lyric video fica pronto

O arquivo `aviso-video-pronto.json` é um fluxo para o [n8n](https://n8n.io). Você abre uma página com um formulário, envia o MP3 e a letra, e o n8n manda o vídeo para o servidor do seu PC. Depois, ele confere de tempos em tempos e manda uma mensagem no Telegram quando termina (ou quando dá erro).

**Antes de começar:** o PC com o `iniciar.bat` precisa estar ligado. Se o servidor reiniciar no meio, o envio se perde e o fluxo avisa pelo tempo esgotado.

## 1. Criar a conta no n8n

1. Entre em n8n.io e crie uma conta (há plano de teste).
2. Abra o painel. Ele tem uma barra lateral com **Workflows** (fluxos).

## 2. Importar o fluxo

1. Em **Workflows**, clique em **Add workflow** (ou o menu de três pontos → **Import from file**).
2. Escolha o arquivo `aviso-video-pronto.json`. Os blocos aparecem na tela.

## 3. Criar a senha do servidor (credencial)

O servidor pede a senha do site em um cabeçalho chamado `X-Access-Token`. Esse cabeçalho é a forma de o servidor saber que é você.

1. No menu **Credentials** (credenciais), crie uma do tipo **Header Auth**.
2. Em **Name**, escreva exatamente: `X-Access-Token`.
3. Em **Value**, cole a senha que está no `ACCESS_TOKEN` do `.env` do seu PC.
4. Salve com o nome **Senha do servidor (X-Access-Token)**. Esse é o nome que o fluxo procura.

Não cole a senha em nenhum bloco do fluxo: ela fica só nas credenciais.

## 4. Criar o bot do Telegram

1. No Telegram, procure **@BotFather** e mande `/newbot`. Siga as perguntas e copie o token que ele devolve.
2. No n8n, em **Credentials**, crie uma do tipo **Telegram API** com esse token. Dê o nome **Bot do Telegram**.
3. Mande qualquer mensagem para o seu bot. Depois, descubra o seu número de chat (o `chat id`): peça ao bot **@userinfobot** ou use o `getUpdates` do próprio bot.

## 5. Colar o número do chat

No fluxo, há três blocos de Telegram (**Avisar pronto**, **Avisar erro** e **Avisar tempo esgotado**). Em cada um, troque `COLE_O_ID_DO_CHAT` pelo seu número.

## 6. Ativar e usar

1. Clique em **Publish** (publicar) no topo. O fluxo passa a funcionar sozinho.
2. Clique no bloco **Enviar música** e copie o endereço do formulário (**Production URL**). Abra em uma aba nova.
3. Envie o MP3, cole a letra e digite `SIM` no campo de autorização. Só envie músicas suas ou com autorização.
4. Espere. A mensagem chega no Telegram quando o vídeo estiver pronto.

## O que o fluxo não faz ainda

- **Não baixa o pacote para você.** As cópias para postar ficam no PC, na pasta `output/` (dentro da pasta da música, em `para-postar/`). Pegue por lá. Baixar e entregar o pacote automaticamente fica para o próximo passo.
- **Não confere a letra.** O fluxo manda a letra como ela foi escrita.
- **Não posta em lugar nenhum.** Publicar no TikTok e no YouTube fica para depois.

## Se algo der errado

- **Mensagem de erro no Telegram:** veja a janela do `iniciar.bat` no PC. O erro completo fica lá.
- **Mensagem de tempo esgotado:** confira se o PC está ligado e o `iniciar.bat` aberto. Se o servidor reiniciou, envie de novo.
- **Página do formulário não abre:** confira se o fluxo está **publicado** (Publish), e não só salvo.

## Observações

- Este fluxo foi montado sem ser testado dentro de um n8n real. Os nomes dos campos podem mudar um pouco conforme a versão do n8n. Se algum bloco ficar vermelho ao importar, me envie a mensagem que aparece.
- A senha do servidor e o token do bot são segredos. Não os envie para ninguém nem em conversas.
