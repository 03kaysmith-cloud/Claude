# Waveshare 2.13" e-ink emulator

## Quick start

From the repo root:

```bash
cd eink-emulator
python -m http.server 8000
```

Then open <http://127.0.0.1:8000/index.html> in your browser.

## Tips

- Use the **Scale** slider to zoom the 250×122 preview.
- Toggle **Grid overlay** to check alignment to the pixel grid.
- Toggle **Dither** to preview a higher-contrast, 1-bit feel.

## Customizing the layout

Edit the HTML inside `.dashboard` in `index.html` to mock your own UI while keeping content within the 250×122 px canvas.
