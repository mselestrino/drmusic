# DrMusic

Aplicativo desktop para organizar downloads de áudio de conteúdos que você tem autorização para baixar.

## Como usar

No Windows, abra o PowerShell e execute:

```powershell
irm https://raw.githubusercontent.com/mselestrino/drmusic/main/install.ps1 | iex
```

O instalador baixa a versão publicada em Releases e abre o aplicativo. Não é necessário instalar Python ou FFmpeg manualmente: o pacote para Windows inclui o executável do DrMusic, FFmpeg e FFprobe.

> **Uso responsável:** use o DrMusic somente para conteúdos próprios, em domínio público ou cujo titular tenha autorizado o download. Respeite os direitos autorais e os termos da plataforma. O aplicativo não contorna DRM, paywalls ou outras proteções de acesso.

## Desenvolvimento

- Interface: Python / Tkinter
- Downloads: yt-dlp
- Conversão de áudio: FFmpeg
- Distribuição Windows: PyInstaller + GitHub Releases

## Publicação

Cada push na branch `main` executa o workflow do Windows, baixa o pacote FFmpeg Essentials, gera o executável e publica um ZIP com DrMusic, FFmpeg e FFprobe no release `latest`.

## Licença

MIT para o código deste projeto. FFmpeg e as demais ferramentas incluídas mantêm suas próprias licenças.
