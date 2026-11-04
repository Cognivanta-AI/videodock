# Verificação do VideoDock estático

## Catálogo e arquivo inicial

- Catálogo real:1canal e1vídeo; `The Noise Outside`, `review`. Demos removidos.
- MP4 publicado na árvore pública:4.665.950bytes. SHA-256 `f9e2a14018462e44b800ee4816ab4b48f2674a562bcf2f68e2ee9606e16f23dc` igual ao original antes e depois da cópia. Sem recodificação.
- Miniatura FFmpeg em14.7s:640×360 JPEG,66.769bytes.
- Servidor de desenvolvimento respondeu200 ao MP4 e206 ao pedido `Range: bytes=0-1023`, com Content-Range correto.

## Navegador real

Testado no Chromium com a aplicação local, catálogo e MP4 reais:

- Desktop1366×900: layout original, sem overflow horizontal.
- Celular390×844: biblioteca e modal sem overflow; modal354px, player314px.
- Biblioteca exibe The Noise Outside, Curious Ancestors,00:30, Em revisão. KPIs1vídeo/1emrevisão/0aprovados.
- Miniatura carregada com dimensão natural640×360.
- Player nativo: metadados30s/1280×720, readyState4; reprodução avançou para1.44052s; pause verdadeiro; seek para15s e retorno a5s.
- Controles nativos e playsInline verdadeiros.
- Link `#video=curious-ancestors-the-noise-outside` abre o modal após carregar o catálogo.
- Busca sem resultados e seleção Curious Ancestors funcionam.
- Erro do player foi injetado como evento de teste e apresentou mensagem e link direto; reabrir limpou o erro.
- Requisição do catálogo bloqueada por CDP apresentou erro e botão de nova tentativa. Remover o bloqueio permitiu carregar os dados reais novamente.
- Nenhum mecanismo de aprovação ou escrita de status foi executado.

Nota de ambiente: vídeo e clipe-controle inicialmente ficaram em readyState0 quando o navegador estava em segundo plano. Trazer a aba para frente, ativar o lifecycle e emular foco liberou a reprodução de ambos. Não foi necessária alteração no MP4 nem no pipeline. O clipe-controle temporário foi removido da pasta pública antes da publicação.

## Testes de implementação

`npm run check`, `npm run build`, `python3 scripts/validate_catalog.py --public-dir dist` e `git diff --check` passaram. Os4testes TypeScript e27testes Python passaram, incluindo regressões para formatos de data, limites de duração/fps e46mutações inválidas de caminhos comparadas com o parser real do frontend, além de build sem FFmpeg no runner. A suíte Python exercitou FFmpeg real, duplicação, colisões, rollback, locks e commit/push com leitura de SHA em remoto bare local descartável.

Também foi executado o publicador em um repositório temporário contendo o React real, seus arquivos públicos e dependências: adicionou uma publicação em canal de QA com `--no-push`, executou check/build reais, preservou a entrada anterior e produziu um JSON aceito pelo parser do frontend. Essa árvore temporária foi removida; nenhum canal ou vídeo de QA entrou no catálogo de produção.

O build final contém1canal/1vídeo, status `review`, e o MP4 de4.665.950bytes com hash igual ao original.

Nos runners GitHub sem FFmpeg/FFprobe, a validação de build verifica os átomos MP4 `ftyp/moov/mdat` e enquadramento JPEG, mas não decodifica os codecs nem revalida duração/resolução/fps. O publicador local exige FFmpeg/FFprobe e faz verificação completa de streams e miniatura antes de aceitar um novo arquivo.

## Limites e configuração remota

Documentação oficial consultada: aviso Git acima50MiB, bloqueio100MiB; Pages site1GB, repositório-fonte recomendado1GB, banda flexível100GB/mês. Primeira mídia é adequada ao repositório e dispensa otimização.

Verificação inicial: organizaçãoFree, repositório privado, Pages404. Proprietário autorizou tornar público; GitHub App recusou a mudança administrativa com403. Owner informado sobre Settings→General→Danger Zone→Public e Settings→Pages→GitHub Actions. Confirmar resultado do workflow e URLs remotas antes de declarar deploy concluído.

Os testes do publicador, check/build finais e resultado remoto devem ser consultados no commit/workflow da entrega; esta evidência descreve as verificações locais realizadas, não substitui um deploy aprovado.
