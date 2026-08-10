# Image Output Geometry

The plugin uses a shared aspect-ratio set so GPT and Gemini produce comparable
canvases for text-to-image generation and image editing.

## Official Sources

- OpenAI image generation guide:
  https://developers.openai.com/api/docs/guides/image-generation
- Google Gemini image generation guide:
  https://ai.google.dev/gemini-api/docs/generate-content/image-generation

## Default

- Text-to-image resolution class: `2K`
- Text-to-image aspect ratio: `16:9` landscape when the user does not specify a format
- Image edit resolution class: `2K`
- Image edit aspect ratio: nearest supported ratio to the EXIF-corrected primary image
- Explicit user-requested composition: pass `--aspect-ratio`

Supported aspect ratios:

`1:1`, `2:3`, `3:2`, `3:4`, `4:3`, `4:5`, `5:4`, `9:16`, `16:9`, `21:9`

`--list-formats` prints this shared GPT/Gemini-safe subset plus the official
Gemini `gemini-3.1-flash-image` table. Gemini also supports `512px`, `4K`,
`1:4`, `4:1`, `1:8`, and `8:1`, but those are not default dual-provider
formats because GPT size validation rejects some extreme ratios and large 4K
canvases.

Default models:

- GPT: `gpt-image-2-x`
- Gemini: `gemini-3.1-flash-image`

Default gateway for both generation and editing:

`https://api.iiiiitoken.com`

## Provider Mapping

Google's official Gemini REST endpoint receives:

```json
{
  "generationConfig": {
    "responseFormat": {
      "image": {
        "aspectRatio": "3:2",
        "imageSize": "2K"
      }
    }
  }
}
```

The plugin's default third-party Gemini gateway currently ignores
`responseFormat` without returning an error. In automatic mode, non-Google
gateways receive the equivalent official SDK-style `generationConfig.imageConfig`
shape instead:

```json
{
  "generationConfig": {
    "imageConfig": {
      "aspectRatio": "3:2",
      "imageSize": "2K"
    }
  }
}
```

Use `--gemini-geometry-mode response-format` or
`--gemini-geometry-mode image-config` only to override endpoint detection.
The script verifies the actual returned image ratio and reports an error when
the provider silently returns a different canvas.

GPT receives the corresponding pixel dimensions through `size`. The dimensions
are validated against the GPT image size rules: maximum edge `3840px`, both
edges divisible by `16`, maximum `3:1` edge ratio, and total pixels between
`655,360` and `8,294,400`.

At `2K`, examples include:

- `1:1` -> `2048x2048`
- `3:2` -> `2528x1696`
- `16:9` -> `2752x1536`
- `9:16` -> `1536x2752`
- `21:9` -> `3168x1344`
