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

## Converting HTML to a bitmap later

The real display does not render HTML directly. You can render your HTML in a headless browser and save a 250×122 screenshot, then convert it to a 1‑bit bitmap that the display driver accepts.

Example workflow:

1. Render the HTML to a PNG at 250×122 (via Playwright or Puppeteer).
2. Convert the PNG to a 1‑bit BMP/PNG using ImageMagick or Pillow.
3. Send the resulting bitmap to the Waveshare driver.

This keeps your HTML/CSS prototype as the source of truth while producing the exact pixels needed by the e‑ink display.

## Running on a Raspberry Pi

You do **not** need a separate computer once the display is attached to a Raspberry Pi. The Pi can run everything from its SD card and update the display directly over SPI.

Typical setup:

- Raspberry Pi boots from SD card and runs your display updater script/service.
- The Waveshare display is connected to the Pi via SPI/GPIO.
- Your script can fetch data over Wi‑Fi (APIs, MQTT, local server) and render/update the bitmap on a schedule.

So the display can be fully standalone: power the Pi, connect Wi‑Fi, and it updates without any external computer.
