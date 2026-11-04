# VideoDock

Painel estático multicanal para visualizar e revisar vídeos de produção. React + TypeScript + Vite, mantendo a interface compacta original: canais, busca, indicadores, miniaturas, status e player modal.

**Esta versão não tem backend, banco, autenticação ou API de upload.** O GitHub armazena o catálogo e os arquivos públicos. Publicar no VideoDock não significa aprovar o vídeo nem publicá-lo no YouTube.

## Primeiro vídeo

- **The Noise Outside** — Curious Ancestors; micro-história ficcional pré-histórica.
- **Em revisão** (`review`), 30 segundos, 1280×720, 30 fps.
- MP4: **4.665.950 bytes**, copiado sem recodificação e com SHA-256 idêntico ao original.
- Miniatura: JPEG 640×360 extraído do vídeo com FFmpeg, 66.769 bytes.
- Original de produção preservado em `/home/sysadmin/workspace/curious-ancestors-productions/test01-flux-30s/output/preview.mp4`.

## Desenvolvimento e validação

Requisitos: Node22+, npm, Python3.11+, FFmpeg e FFprobe. Sem dependências Python externas.

```bash
npm ci
npm run check
npm test
npm run build
npm run dev
```

`npm run check` valida TypeScript, catálogo e mídia. O build inclui `public/data/videos.json`, os MP4s e as miniaturas em `dist/`. O site usa `import.meta.env.BASE_URL`, configurado como `/videodock/`; não há origem absoluta fixa no player.

```text
public/
  data/videos.json
  videos/curious-ancestors/the-noise-outside/
    preview.mp4
    thumbnail.jpg
src/
scripts/
tests/
AGENTS.md
```

## Publicar próximos vídeos

No clone de trabalho, com git limpo, credencial GitHub e identidade de commit já configuradas:

```bash
./scripts/publish-video.sh \
  --channel curious-ancestors \
  --title "Título do próximo vídeo" \
  --file "/caminho/da/producao/preview.mp4" \
  --status review
```

O publicador cria uma pasta segura e única, copia o MP4 sem alterar a fonte, extrai uma miniatura, acrescenta o registro sem apagar os anteriores, valida, executa check/build e faz commit/push. Arquivos iguais no mesmo canal e sobrescritas acidentais são rejeitados. `--optimize` permite preparar uma cópia H.264/AAC otimizada; não é necessário para o primeiro vídeo. Use `--channel-name` para dar nome legível a um canal novo. Consulte [o fluxo completo](docs/HERMES-INTEGRATION.md) e `./scripts/publish-video.sh --help`.

O status padrão é `review`. Não há botão nem automação de aprovação. A decisão editorial permanece com o proprietário.

## GitHub Pages

Workflow: `.github/workflows/deploy-pages.yml`; dispara em push para `main` ou manualmente. Faz instalação reproduzível, check, testes, build, validação de `dist` e publicação via Actions Pages.

Configuração do proprietário:

1. Em **Settings → General → Danger Zone → Change repository visibility**, tornar **Public** se a organização estiver no plano Free.
2. Em **Settings → Pages → Build and deployment → Source**, selecionar **GitHub Actions**.
3. Executar novamente o workflow se necessário.

Endereços esperados **após um deploy bem-sucedido**:

- Painel: https://cognivanta-ai.github.io/videodock/
- Vídeo aberto no modal: https://cognivanta-ai.github.io/videodock/#video=curious-ancestors-the-noise-outside
- MP4: https://cognivanta-ai.github.io/videodock/videos/curious-ancestors/the-noise-outside/preview.mp4

A credencial GitHub App do agente não possui permissão administrativa para mudar a visibilidade (`403 Resource not accessible by integration` na verificação inicial). A existência do workflow ou um build aprovado não comprova que Pages está habilitado. O resultado real do deploy deve ser conferido no Actions e nas URLs.

## Publicidade, limites e escala

**Os arquivos do site podem ser públicos mesmo se a origem for privada em um plano compatível.** O proprietário autorizou a exposição deste repositório e seus arquivos; não publicar segredos nem mídia confidencial. `.env`, tokens e chaves não entram no build. Não usar Git LFS para mídia servida pelo Pages.

Limites consultados na documentação oficial:

- Git: aviso acima de50MiB por arquivo; bloqueio acima de100MiB.
- Pages: site publicado no máximo1GB; repositório-fonte recomendado até1GB; banda mensal com limite flexível de100GB; deploy com timeout de10minutos. Builds pelo workflow customizado não estão sujeitos ao limite flexível de10builds/hora.
- Política conservadora deste projeto: MP4 até50MiB e diretório público até900MiB, preservando margem. O histórico Git continua crescendo mesmo ao excluir vídeos.

Para vídeos longos ou bibliotecas maiores, migrar os binários para armazenamento externo e manter o catálogo estático; não forçar commits grandes nem implantar um backend sem nova autorização.

Fontes: [arquivos grandes](https://docs.github.com/en/repositories/working-with-files/managing-large-files/about-large-files-on-github), [limites Pages](https://docs.github.com/en/pages/getting-started-with-github-pages/github-pages-limits), [planos e disponibilidade](https://docs.github.com/en/pages/getting-started-with-github-pages/about-github-pages).
