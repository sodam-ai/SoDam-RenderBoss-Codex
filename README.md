# Architectural Render Guard

[中文](#中文) | [English](#english)

## 中文

Architectural Render Guard 是一个 Codex 插件，用 GPT 与 Gemini 生成或修改建筑渲染图。
没有传入图片时走生图；传入图片时走修图，并严格保护建筑体量、层数、门窗、楼梯、
坡道、平台、入口和标识文字。

### 功能

- 首次使用运行初始化检查：插件 skill、Python 依赖、配置目录和 API key
- 缺少 `requests`、`pillow`、`urllib3` 时自动用 `pip --user` 安装
- 无图生图默认使用 `2K` 横图 `16:9`
- 有图修图会按主图尺寸选择最接近的官方支持宽高比
- 默认 GPT/Gemini 网关均为 `https://api.iiiiitoken.com`
- 默认 GPT 模型：`gpt-image-2-x`
- 默认 Gemini 模型：`gemini-3.1-flash-image`
- API key 保存在插件目录之外，不会提交到仓库

### 安装

添加 GitHub marketplace：

```powershell
codex plugin marketplace add m174460635/architectural-render-guard
```

安装插件：

```powershell
codex plugin add architectural-render-guard@architectural-render-guard
```

安装或更新后，请新建一个 Codex 任务，使插件 skill 重新加载。

### 首次初始化

```powershell
python scripts/render_guard.py --init --models both
```

如果缺少 key，保存共享 iiiiitoken key：

```powershell
$key | python scripts/render_guard.py --save-key-stdin
```

默认 key 路径：

```text
$CODEX_HOME/architectural-render-guard/api_key.txt
```

也兼容 provider 专属 key：

```text
$CODEX_HOME/architectural-render-guard/gpt_api_key.txt
$CODEX_HOME/architectural-render-guard/gemini_api_key.txt
```

可用环境变量：

```text
ARCH_RENDER_GUARD_API_KEY
IIIII_TOKEN_API_KEY
ARCH_RENDER_GUARD_GPT_API_KEY
ARCH_RENDER_GUARD_GEMINI_API_KEY
```

### 支持的生图格式

查看完整格式：

```powershell
python scripts/render_guard.py --list-formats
```

共享 GPT/Gemini 安全格式：

```text
1:1  2:3  3:2  3:4  4:3  4:5  5:4  9:16  16:9  21:9
```

共享分辨率：

```text
1K  2K
```

`--list-formats` 也会列出 Gemini `gemini-3.1-flash-image` 官方格式，包括
`512px`、`1K`、`2K`、`4K` 以及更极端的 `1:4`、`4:1`、`1:8`、`8:1`。
插件双模型默认仍使用 GPT/Gemini 都安全的子集。

默认无图生图为 `2K`、`16:9` 横图。有图修图默认 `--aspect-ratio auto`，
自动读取主图 EXIF 修正后的尺寸并选择最近格式。

### 示例

无图生图：

```powershell
python scripts/render_guard.py `
  --prompt "Photorealistic 2K landscape render of a calm modern community clinic, warm off-white facade, clear glass entrance, accessible ramp, trees and clean pavement" `
  --out-dir "C:\path\outputs"
```

有图修图：

```powershell
python scripts/render_guard.py `
  --image "C:\path\building.png" `
  --locked-subject "Keep the building massing, floor count, openings, entrance, stairs, ramp, and signage unchanged" `
  --style "Warm off-white modern facade, gray stone steps, clear glass, realistic daylight" `
  --out-dir "C:\path\outputs"
```

### 开发与发布

```powershell
python -m unittest discover -s tests -v
powershell -ExecutionPolicy Bypass -File scripts/publish.ps1 `
  -Message "Describe the plugin update"
```

`publish.ps1` 会验证插件、刷新版本 cachebuster、同步本机 Codex 缓存、提交并推送到 GitHub。

## English

Architectural Render Guard is a Codex plugin for GPT and Gemini architectural
image generation and image editing. If no image is supplied, it uses
text-to-image generation. If image(s) are supplied, it uses image editing and
preserves building massing, floor count, doors, windows, stairs, ramps,
platforms, entrances, and signage.

### Install

```powershell
codex plugin marketplace add m174460635/architectural-render-guard
codex plugin add architectural-render-guard@architectural-render-guard
```

Start a new Codex task after installation or updates so the plugin skill is
loaded from the new version.

### First Use

```powershell
python scripts/render_guard.py --init --models both
```

Save one shared iiiiitoken key when prompted:

```powershell
$key | python scripts/render_guard.py --save-key-stdin
```

The default key path is:

```text
$CODEX_HOME/architectural-render-guard/api_key.txt
```

### Defaults

- GPT/Gemini base URL: `https://api.iiiiitoken.com`
- GPT model: `gpt-image-2-x`
- Gemini model: `gemini-3.1-flash-image`
- Text-to-image default: `2K` landscape `16:9`
- Image edit default: nearest supported aspect ratio to the primary image

### Test

```powershell
python -m unittest discover -s tests -v
```

## License

MIT
