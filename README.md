# Architectural Render Guard

[中文](#中文) | [English](#english)

## 中文

Architectural Render Guard 是一个 Codex 插件，用 GPT 和 Gemini 对建筑图片
进行局部修改、风格渲染和多参考图合成，同时严格保护建筑体量、层数、门窗、
楼梯、坡道、平台、入口和标识文字。

### 功能

- 同时调用 GPT 与 Gemini，并通过轻量预览筛选结果
- 根据原图自动选择官方支持的最近宽高比
- 默认输出 2K
- 支持局部遮罩编辑和多张参考图
- 校验模型实际返回的宽高比，避免静默生成方图
- API 密钥保存在插件目录之外，不会提交到仓库

### 安装

添加 GitHub marketplace：

```powershell
codex plugin marketplace add m174460635/architectural-render-guard
```

安装插件：

```powershell
codex plugin add architectural-render-guard@architectural-render-guard
```

安装或更新后，请新建一个 Codex 任务，使插件技能重新加载。

### API 密钥

插件首次使用前需要配置 GPT 和 Gemini 密钥：

```powershell
$gptKey | python scripts/render_guard.py --save-gpt-key-stdin
$geminiKey | python scripts/render_guard.py --save-gemini-key-stdin
```

密钥默认保存在：

```text
$CODEX_HOME/architectural-render-guard/gpt_api_key.txt
$CODEX_HOME/architectural-render-guard/gemini_api_key.txt
```

也可以使用环境变量：

```text
ARCH_RENDER_GUARD_GPT_API_KEY
ARCH_RENDER_GUARD_GEMINI_API_KEY
```

### 宽高比和分辨率

默认使用 `--aspect-ratio auto --resolution 2K`。自动模式读取主图尺寸并匹配：

```text
1:1  2:3  3:2  3:4  4:3  4:5  5:4  9:16  16:9  21:9
```

明确需要横幅、竖幅或方图时，可以传入：

```powershell
python scripts/render_guard.py `
  --image "C:\path\building.png" `
  --aspect-ratio 16:9 `
  --resolution 2K `
  --locked-subject "Preserve the building body and openings." `
  --style "Photorealistic architectural visualization."
```

### 开发与发布

```powershell
python -m unittest discover -s tests -v
powershell -ExecutionPolicy Bypass -File scripts/publish.ps1 `
  -Message "Describe the plugin update"
```

`publish.ps1` 会验证插件、刷新版本 cachebuster、同步本机 Codex 缓存、提交并
推送到 GitHub。

## English

Architectural Render Guard is a Codex plugin for guarded architectural
image-to-image rendering with GPT and Gemini. It supports local edits,
multi-reference rendering, automatic official aspect-ratio selection, 2K
output, preview inspection, and strict preservation of building geometry,
openings, entrances, stairs, ramps, platforms, and signage.

### Install

```powershell
codex plugin marketplace add m174460635/architectural-render-guard
codex plugin add architectural-render-guard@architectural-render-guard
```

Start a new Codex task after installation or updates so the plugin skill is
loaded from the new version.

### Test

```powershell
python -m unittest discover -s tests -v
```

## License

MIT
