# Image Output Geometry

The plugin uses a shared, official aspect-ratio set so GPT and Gemini produce
comparable canvases.

## Official Sources

- OpenAI image generation guide:
  https://developers.openai.com/api/docs/guides/image-generation
- Google Gemini image generation guide:
  https://ai.google.dev/gemini-api/docs/generate-content/image-generation

## Default

- Resolution class: `2K`
- Aspect ratio: nearest supported ratio to the EXIF-corrected primary image
- Explicit user-requested composition: pass `--aspect-ratio`

Supported aspect ratios:

`1:1`, `2:3`, `3:2`, `3:4`, `4:3`, `4:5`, `5:4`, `9:16`, `16:9`, `21:9`

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
are validated against the `gpt-image-2` rules: maximum edge `3840px`, both
edges divisible by `16`, maximum `3:1` edge ratio, and total pixels between
`655,360` and `8,294,400`.

At `2K`, examples include:

- `1:1` -> `2048x2048`
- `3:2` -> `2528x1696`
- `16:9` -> `2752x1536`
- `9:16` -> `1536x2752`
- `21:9` -> `3168x1344`
