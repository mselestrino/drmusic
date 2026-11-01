# DrMusic

Aplicativo desktop para organizar downloads de áudio de conteúdos que você tem autorização para baixar.

## Como usar

No Windows, abra o PowerShell e execute:

```powershell
irm https://raw.githubusercontent.com/mselestrino/drmusic/main/install.ps1 | iex
```

O instalador baixa a versão publicada em Releases e abre o aplicativo. Não é necessário instalar Python ou FFmpeg manualmente.

> **Uso responsável:** use o DrMusic somente para conteúdos próprios, em domínio público ou cujo titular tenha autorizado o download. Respeite os direitos autorais e os termos da plataforma. O aplicativo não contorna DRM, paywalls ou outras proteções de acesso.

## Desenvolvimento

- Interface: Python / Tkinter
- Downloads: yt-dlp
- Conversão de áudio: FFmpeg fornecido pelo pacote imageio-ffmpeg
- Distribuição Windows: PyInstaller + GitHub Releases

## Publicação

Cada push na branch `main` executa o workflow do Windows, gera o executável e atualiza o release `latest`.

## Licença

MIT para o código deste projeto. As ferramentas e bibliotecas incluídas mantêm suas próprias licenças.
