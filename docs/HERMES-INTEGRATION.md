# Hermes → VideoDock: publicação estática

Este fluxo substitui a antiga proposta de backend privado. **Nenhum endpoint de upload, banco ou autenticação faz parte desta versão.** Git e arquivos estáticos são o mecanismo de publicação.

## Contrato do catálogo

`public/data/videos.json`:

```json
{
  "channels": [{"id":"curious-ancestors","name":"Curious Ancestors"}],
  "videos": [{
    "id":"curious-ancestors-the-noise-outside",
    "channel_id":"curious-ancestors",
    "title":"The Noise Outside",
    "description":"A fictional prehistoric suspense micro-story with an ironic ending.",
    "status":"review",
    "duration_seconds":30,
    "resolution":"1280x720",
    "fps":30,
    "video_path":"videos/curious-ancestors/the-noise-outside/preview.mp4",
    "thumbnail_path":"videos/curious-ancestors/the-noise-outside/thumbnail.jpg",
    "generator":"FLUX.1 Schnell",
    "style":"A3 Prehistoric Cave",
    "created_at":"2026-11-04"
  }]
}
```

IDs são slugs seguros e únicos; caminhos nunca são absolutos, URLs externas ou contêm travessia. `channel_id` precisa corresponder a um canal existente. `created_at` aceita data ISO real ou timestamp ISO com fuso; duração e fps devem ser finitos e positivos. O publicador inclui tamanho/hash para rastreabilidade. Todos os canais do frontend vêm deste JSON: não requer mudanças React para adicionar canais.

Status: `review`, `rendering`, `approved`, `rejected`, `published`, `failed`. Novo registro usa `review`; `approved` exige decisão editorial humana explícita. Publicação do arquivo não altera aprovação.

## Uso operacional

1. Trabalhar no clone canônico `/home/sysadmin/workspace/videodock` com git limpo e atualizado.
2. Confirmar que a exposição pública do conteúdo está autorizada. Não colocar segredos no catálogo ou em variáveis Vite.
3. Validar o MP4 original e sua permissão de divulgação. O script nunca altera a produção-fonte.
4. Publicar com o wrapper:

```bash
./scripts/publish-video.sh \
  --channel curious-ancestors \
  --channel-name "Curious Ancestors" \
  --title "Título do próximo vídeo" \
  --file "/caminho/da/producao/preview.mp4" \
  --status review
```

Use `--help` para os demais metadados e modo de preparação sem push. O fluxo padrão prepara os arquivos, gera JPEG com FFmpeg, valida o catálogo, executa `npm run check` e `npm run build`, cria um commit com os arquivos da publicação e envia ao GitHub. Não misturar alterações de implementação no mesmo disparo do publicador: finalize essas alterações antes.

É recusado reutilizar o mesmo arquivo no mesmo canal. Colisões de título recebem um identificador distinto em vez de sobrescrever o vídeo anterior. Se o build falhar antes do commit, os arquivos novos e a atualização do catálogo são desfeitos. Uma falha de push não deve apagar um commit já criado: resolver acesso/rede e reenviar o commit existente, sem produzir outra cópia do vídeo.

`--optimize` recodifica apenas a cópia de publicação usando FFmpeg; avaliar qualidade e tamanho. Se ainda ultrapassar o teto prático, parar e propor armazenamento externo. Não usar LFS, remover o original ou resetar o histórico para contornar limites.

## Frontend

A aplicação busca o JSON com a base Vite e apresenta estados de carregamento, catálogo inválido, falha com nova tentativa e filtros sem resultados. O modal preserva o layout existente e usa `<video controls playsInline>` com poster, metadados, erro e link direto ao MP4. A reprodução não faz chamadas ao YouTube.

Links de vídeo usam fragmentos, compatíveis com Pages sem roteamento no servidor:

`/videodock/#video=curious-ancestors-the-noise-outside`

O modal fecha com botão, fundo ou Escape, controla foco e pausa ao desmontar. Controles nativos permitem tocar, pausar e buscar para frente/trás. Nenhum dado de aprovação é escrito pelo navegador.

## Deploy e verificação remota

GitHub Actions publica `dist/` inteiro, incluindo catálogo e mídia, sob `/videodock/`. Conferir:

- check, testes, build e validação do artefato aprovados;
- SHA remoto corresponde ao commit enviado;
- deploy concluído, não apenas build;
- HTML, JSON, JPEG e MP4 acessíveis na URL publicada;
- Range HTTP funciona para buscar o MP4;
- browser toca, pausa, avança e retrocede; celular não tem overflow;
- catálogo remoto mantém `status: review` para a primeira prévia;
- hash do MP4 original de produção permanece igual.

No plano Free da organização, Pages exige repositório público. O agente recebeu autorização para torná-lo público, mas o App atual recusou a operação administrativa com403. Se isso continuar, o proprietário deve alterar a visibilidade em General e escolher GitHub Actions em Pages, depois repetir o workflow. Nunca declarar um link publicado sem resposta remota confirmada.

## Limites

Política local:50MiB por MP4 e900MiB em `public/`. GitHub: aviso50MiB/bloqueio100MiB, Pages publicado1GB e banda flexível100GB/mês. Consultar novamente a documentação antes de aumentar a biblioteca. Git retém os binários de versões antigas. Segredos e mídia sensível devem ficar fora deste site estático público.
