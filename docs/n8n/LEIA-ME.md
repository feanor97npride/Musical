# Fluxo n8n: enviar a música e avisar quando ficar pronta

O n8n roda num VPS (um servidor alugado na Hostinger, ligado 24 horas). Você abre o formulário pelo celular ou pelo computador, envia o MP3, a letra e escolhe um atalho (TikTok, YouTube ou Full). O n8n manda para o servidor do seu PC, acompanha e avisa no Telegram quando termina.

**Antes de começar:** o PC com o `iniciar.bat` precisa estar ligado e com o túnel aberto. Sem ele, o n8n não alcança o servidor e avisa que o tempo esgotou.

## 1. Criar o VPS na Hostinger
1. No painel da Hostinger, contrate um **VPS** com **Ubuntu** e **Docker** (há um modelo pronto de Docker na hora de criar).
2. Anote o **IP** do VPS (aparece na página do serviço).

## 2. Apontar um subdomínio para o VPS
1. No painel onde está o seu domínio (pode ser a própria Hostinger), crie um registro **A**: nome `n8n`, valor = o IP do VPS.
2. Deixe em **somente DNS**, se o painel perguntar. Isso é o que faz o endereço apontar para o VPS.
3. Seu endereço do n8n será `n8n.SEU-DOMINIO`.

## 3. Subir o n8n no VPS
Conecte no VPS pelo terminal do painel da Hostinger (botão **Terminal**), depois rode:

1. Crie a pasta e entre nela:
   ```
   mkdir -p ~/n8n && cd ~/n8n
   ```
   (cria uma pasta para os arquivos do n8n)
2. Copie para essa pasta os arquivos `docker-compose.yml`, `Caddyfile` e `.env.example` de `docs/n8n/vps/` do projeto. O mais fácil é colar o conteúdo de cada um com `nano`.
3. Crie o arquivo de configuração:
   ```
   cp .env.example .env
   nano .env
   ```
   Troque `SEU-DOMINIO` pelo seu subdomínio (nos três lugares). Em `N8N_ENCRYPTION_KEY`, gere uma chave com:
   ```
   openssl rand -hex 32
   ```
   e cole o resultado no lugar de `TROQUE_POR_UMA_CHAVE_LONGA`. Essa chave protege as senhas salvas no n8n: guarde num lugar seguro.
4. Troque também `n8n.SEU-DOMINIO` no arquivo `Caddyfile`.
5. Suba o n8n:
   ```
   docker compose up -d
   ```
   Na primeira vez baixa as imagens e pode levar alguns minutos. O Caddy cuida do HTTPS (o cadeado) sozinho.

## 4. Criar a conta do n8n
Abra `https://n8n.SEU-DOMINIO` no navegador e crie a conta de dono (e-mail e senha só seus).

## 5. Importar o fluxo
1. No n8n, clique em **Add workflow** → menu de três pontos → **Import from file**.
2. Escolha `docs/n8n/aviso-video-pronto.json`. Os blocos aparecem na tela.
3. Se algum bloco ficar vermelho, tire print e me mande.

## 6. Criar as credenciais
- **Senha do servidor:** menu **Credentials** → nova do tipo **Header Auth**. Em **Name** escreva `X-Access-Token`; em **Value**, cole a senha que está no `ACCESS_TOKEN` do `.env` do seu PC. Salve com o nome **Senha do servidor (X-Access-Token)**.
- **Bot do Telegram:** nova do tipo **Telegram API** com o token do bot (pegue no @BotFather, comando `/newbot`). Salve com o nome **Bot do Telegram**.
- **Número do chat:** em cada um dos três blocos **Avisar** (pronto, erro e tempo esgotado), troque `COLE_O_ID_DO_CHAT` pelo seu número de chat.

Não cole senha nem token em nenhum bloco do fluxo: eles ficam só nas credenciais.

## 7. Proteger o formulário
O formulário fica na internet, então qualquer pessoa com o endereço poderia enviar música. Proteja-o:
- No bloco **Enviar música**, procure a opção de **autenticação** (login e senha básicos). Se a sua versão do n8n não tiver essa opção, confirme no menu de ajuda do n8n e me avise.
- Mantenha a pergunta de autorização: a pessoa precisa digitar `SIM` para confirmar que a música é dela.

## 8. Publicar e testar
1. Clique em **Publish** no topo do fluxo.
2. Clique no bloco **Enviar música** e copie o **Production URL**. Abra em outra aba.
3. Envie um MP3 curto, a letra, escolha **YouTube** e digite `SIM`.
4. Espere. O aviso chega no Telegram quando o vídeo estiver pronto.
5. Teste **Full**: chegam dois avisos (16:9 e 9:16).

## 9. Desligar o Activepieces
Depois que o n8n estiver funcionando, desligue os fluxos antigos do Activepieces para não receber aviso duplicado.

## Se algo der errado
- **Aviso de erro no Telegram:** veja a janela do `iniciar.bat` no PC: o erro completo fica lá.
- **Aviso de tempo esgotado:** confira se o PC está ligado e o `iniciar.bat` aberto. Se o servidor reiniciou, envie de novo.
- **Página do formulário não abre:** confira se o fluxo está **publicado** (Publish), e não só salvo.
- **Bloco vermelho ao importar:** os nomes dos campos podem mudar entre versões do n8n. Tire print e me mande.

## Observações
- Este fluxo foi montado sem ser testado dentro de um n8n real. Teste com uma música curta antes de usar.
- A chave de criptografia, a senha do servidor e o token do bot são segredos. Não os envie para ninguém nem em conversas.
