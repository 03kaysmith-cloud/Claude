#!/usr/bin/env python3
"""
Weather Dashboard for Waveshare 2.13inch e-Paper Display HAT (250x122)
Designed for Raspberry Pi Zero 2 WH.

Displays:
- Date/time (top left, 12px)
- Current temperature (24px) with weather description
- Weather icon (top right)
- Wind speed
- Sunrise/sunset (bottom left)
- Tomorrow's forecast at 06:00 and 18:00 (bottom right, 8px)

Weather data is cached and refreshed every 15 minutes.
Time is refreshed every minute via partial display update.
"""

import json
import logging
import math
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

import requests
from PIL import Image, ImageDraw, ImageFont

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
SCRIPT_DIR = Path(__file__).resolve().parent
CONFIG_PATH = SCRIPT_DIR / "config.json"
FONT_DIR = SCRIPT_DIR / "fonts"

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger("weather_dashboard")

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

def load_config() -> dict:
    with open(CONFIG_PATH) as f:
        return json.load(f)

# ---------------------------------------------------------------------------
# Weather data helpers
# ---------------------------------------------------------------------------

WEATHER_ICONS = {
    # (main condition) -> simple monochrome ASCII art / symbol drawing function
    "Clear": "sun",
    "Clouds": "cloud",
    "Rain": "rain",
    "Drizzle": "rain",
    "Thunderstorm": "storm",
    "Snow": "snow",
    "Mist": "fog",
    "Fog": "fog",
    "Haze": "fog",
    "Smoke": "fog",
    "Dust": "fog",
}


def draw_icon(draw: ImageDraw.ImageDraw, x: int, y: int, icon_type: str, size: int = 30):
    """Draw a simple monochrome weather icon at (x, y)."""
    cx, cy = x + size // 2, y + size // 2
    r = size // 3

    if icon_type == "sun":
        # Circle with rays
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=0)
        for angle in range(0, 360, 45):
            rad = math.radians(angle)
            x1 = cx + int((r + 3) * math.cos(rad))
            y1 = cy + int((r + 3) * math.sin(rad))
            x2 = cx + int((r + 6) * math.cos(rad))
            y2 = cy + int((r + 6) * math.sin(rad))
            draw.line([x1, y1, x2, y2], fill=0, width=1)

    elif icon_type == "cloud":
        # Two overlapping ellipses
        draw.ellipse([cx - r - 4, cy - 2, cx + 4, cy + r], fill=0)
        draw.ellipse([cx - 4, cy - r + 2, cx + r + 4, cy + r - 2], fill=0)

    elif icon_type == "rain":
        # Cloud with rain drops
        cr = r - 2
        draw.ellipse([cx - cr - 3, cy - cr, cx + 3, cy + 2], fill=0)
        draw.ellipse([cx - 3, cy - cr - 2, cx + cr + 3, cy], fill=0)
        for dx in [-4, 2, 8]:
            draw.line([cx + dx, cy + 5, cx + dx - 2, cy + 11], fill=0, width=1)

    elif icon_type == "storm":
        # Cloud with lightning bolt
        cr = r - 2
        draw.ellipse([cx - cr - 3, cy - cr, cx + 3, cy + 2], fill=0)
        draw.ellipse([cx - 3, cy - cr - 2, cx + cr + 3, cy], fill=0)
        # Lightning bolt
        bolt = [
            (cx, cy + 3), (cx - 3, cy + 9),
            (cx + 1, cy + 9), (cx - 2, cy + 15),
            (cx + 4, cy + 7), (cx + 1, cy + 7), (cx + 3, cy + 3),
        ]
        draw.polygon(bolt, fill=0)

    elif icon_type == "snow":
        # Cloud with snowflakes (dots)
        cr = r - 2
        draw.ellipse([cx - cr - 3, cy - cr, cx + 3, cy + 2], fill=0)
        draw.ellipse([cx - 3, cy - cr - 2, cx + cr + 3, cy], fill=0)
        for dx, dy in [(-5, 6), (0, 10), (5, 6), (-2, 13), (4, 12)]:
            draw.ellipse([cx + dx - 1, cy + dy - 1, cx + dx + 1, cy + dy + 1], fill=0)

    elif icon_type == "fog":
        # Horizontal lines
        for i in range(4):
            yy = cy - 6 + i * 5
            draw.line([cx - r - 2, yy, cx + r + 2, yy], fill=0, width=1)

    else:
        # Fallback: question mark
        draw.text((cx - 4, cy - 6), "?", fill=0)


def fetch_weather(cfg: dict) -> dict | None:
    """Fetch current weather and forecast from OpenWeatherMap."""
    api_key = cfg["api_key"]
    lat = cfg["latitude"]
    lon = cfg["longitude"]
    units = cfg.get("units", "metric")

    current_url = (
        f"https://api.openweathermap.org/data/2.5/weather"
        f"?lat={lat}&lon={lon}&units={units}&appid={api_key}"
    )
    forecast_url = (
        f"https://api.openweathermap.org/data/2.5/forecast"
        f"?lat={lat}&lon={lon}&units={units}&appid={api_key}"
    )

    try:
        cur_resp = requests.get(current_url, timeout=10)
        cur_resp.raise_for_status()
        current = cur_resp.json()

        fc_resp = requests.get(forecast_url, timeout=10)
        fc_resp.raise_for_status()
        forecast = fc_resp.json()

        return {"current": current, "forecast": forecast, "fetched_at": time.time()}

    except requests.RequestException as e:
        log.error("Failed to fetch weather data: %s", e)
        return None


def load_cache(path: str) -> dict | None:
    try:
        with open(path) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def save_cache(path: str, data: dict):
    with open(path, "w") as f:
        json.dump(data, f)


def get_weather(cfg: dict) -> dict | None:
    """Return weather data, using cache if fresh enough."""
    cache_path = cfg.get("cache_file", "/tmp/weather_cache.json")
    max_age = cfg.get("cache_max_age_minutes", 15) * 60

    cached = load_cache(cache_path)
    if cached and (time.time() - cached.get("fetched_at", 0)) < max_age:
        log.info("Using cached weather data (age %.0fs)", time.time() - cached["fetched_at"])
        return cached

    fresh = fetch_weather(cfg)
    if fresh:
        save_cache(cache_path, fresh)
        return fresh

    # Fall back to stale cache if API fails
    if cached:
        log.warning("API failed; falling back to stale cache")
        return cached

    return None


def find_tomorrow_forecasts(forecast_list: list, tz_offset: int) -> dict:
    """Find forecast entries closest to 06:00 and 18:00 tomorrow (local time)."""
    tz = timezone(timedelta(seconds=tz_offset))
    now_local = datetime.now(tz)
    tomorrow = (now_local + timedelta(days=1)).date()

    target_hours = {6: None, 18: None}
    best_diff = {6: 999999, 18: 999999}

    for entry in forecast_list:
        dt_utc = datetime.fromtimestamp(entry["dt"], tz=timezone.utc)
        dt_local = dt_utc.astimezone(tz)
        if dt_local.date() != tomorrow:
            continue
        for target_h in target_hours:
            diff = abs(dt_local.hour - target_h)
            if diff < best_diff[target_h]:
                best_diff[target_h] = diff
                target_hours[target_h] = entry

    return target_hours


# ---------------------------------------------------------------------------
# Font helpers
# ---------------------------------------------------------------------------

def get_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    """Load DejaVu Sans at the requested pixel size, fall back to default."""
    candidates = [
        FONT_DIR / "DejaVuSans.ttf",
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
        Path("/usr/share/fonts/TTF/DejaVuSans.ttf"),
    ]
    for p in candidates:
        if p.exists():
            return ImageFont.truetype(str(p), size)
    return ImageFont.load_default()


def get_font_bold(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = [
        FONT_DIR / "DejaVuSans-Bold.ttf",
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
        Path("/usr/share/fonts/TTF/DejaVuSans-Bold.ttf"),
    ]
    for p in candidates:
        if p.exists():
            return ImageFont.truetype(str(p), size)
    return get_font(size)


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------

def render_dashboard(cfg: dict, weather: dict) -> Image.Image:
    """Render the full dashboard to a 1-bit PIL Image (250x122)."""
    W = cfg.get("display_width", 250)
    H = cfg.get("display_height", 122)

    img = Image.new("1", (W, H), 255)  # white background
    draw = ImageDraw.Draw(img)

    font8 = get_font(8)
    font10 = get_font(10)
    font12 = get_font(12)
    font24 = get_font_bold(24)

    cur = weather.get("current", {})
    tz_offset = cur.get("timezone", 0)
    tz = timezone(timedelta(seconds=tz_offset))
    now_local = datetime.now(tz)

    # ── Date & time (top left, 12px) ──────────────────────────────────
    date_str = now_local.strftime("%a %d %b %H:%M")
    draw.text((2, 2), date_str, font=font12, fill=0)

    # ── Weather icon (top right corner) ───────────────────────────────
    main_cond = ""
    if cur.get("weather"):
        main_cond = cur["weather"][0].get("main", "")
    icon_type = WEATHER_ICONS.get(main_cond, "cloud")
    icon_size = 32
    draw_icon(draw, W - icon_size - 4, 2, icon_type, size=icon_size)

    # ── Current temperature (large, below date) ──────────────────────
    temp = cur.get("main", {}).get("temp")
    if temp is not None:
        temp_str = f"{temp:.0f}°C"
    else:
        temp_str = "--°C"
    draw.text((2, 20), temp_str, font=font24, fill=0)

    # ── Weather description + feels-like (next to temp) ──────────────
    desc = ""
    if cur.get("weather"):
        desc = cur["weather"][0].get("description", "").capitalize()
    feels = cur.get("main", {}).get("feels_like")
    feels_str = f"Feels {feels:.0f}°" if feels is not None else ""

    desc_x = 2
    desc_y = 48
    draw.text((desc_x, desc_y), desc, font=font10, fill=0)
    if feels_str:
        draw.text((desc_x, desc_y + 13), feels_str, font=font10, fill=0)

    # ── Wind speed ────────────────────────────────────────────────────
    wind = cur.get("wind", {}).get("speed")
    if wind is not None:
        unit = "m/s" if cfg.get("units", "metric") == "metric" else "mph"
        wind_str = f"Wind: {wind:.0f} {unit}"
    else:
        wind_str = ""
    if wind_str:
        draw.text((desc_x, desc_y + 26), wind_str, font=font10, fill=0)

    # ── Sunrise / sunset (bottom left) ────────────────────────────────
    sys_data = cur.get("sys", {})
    sr = sys_data.get("sunrise")
    ss = sys_data.get("sunset")
    if sr and ss:
        sr_local = datetime.fromtimestamp(sr, tz=tz).strftime("%H:%M")
        ss_local = datetime.fromtimestamp(ss, tz=tz).strftime("%H:%M")
        sun_line = f"^ {sr_local}  v {ss_local}"
        draw.text((2, H - 12), sun_line, font=font10, fill=0)

    # ── Separator line ────────────────────────────────────────────────
    mid_x = W // 2 + 20
    draw.line([(mid_x, 50), (mid_x, H - 2)], fill=0, width=1)

    # ── Tomorrow's forecast (bottom right, 8px) ──────────────────────
    forecast_list = weather.get("forecast", {}).get("list", [])
    tomorrow = find_tomorrow_forecasts(forecast_list, tz_offset)

    tomorrow_local = (now_local + timedelta(days=1)).date()
    header = f"Tomorrow ({tomorrow_local.strftime('%a')})"

    rx = mid_x + 6
    ry = 50
    draw.text((rx, ry), header, font=font10, fill=0)

    for i, (hour, entry) in enumerate(sorted(tomorrow.items())):
        if entry is None:
            continue
        t = entry["main"]["temp"]
        cond = entry["weather"][0]["description"].capitalize() if entry.get("weather") else ""
        # Truncate long descriptions
        if len(cond) > 12:
            cond = cond[:11] + "."
        line = f"{hour:02d}:00 {t:.0f}° {cond}"
        draw.text((rx, ry + 16 + i * 14), line, font=font8, fill=0)

    # ── Location label (top, right of date) ───────────────────────────
    loc = cfg.get("location_name", "")
    if loc:
        # Place it after the date string but before the icon
        loc_bbox = draw.textbbox((0, 0), loc, font=font8)
        loc_w = loc_bbox[2] - loc_bbox[0]
        loc_x = W - icon_size - loc_w - 10
        draw.text((loc_x, 5), loc, font=font8, fill=0)

    return img


# ---------------------------------------------------------------------------
# Display driver
# ---------------------------------------------------------------------------

def display_image(img: Image.Image):
    """Send the rendered image to the e-Paper display."""
    try:
        from waveshare_epd import epd2in13_V4
    except ImportError:
        log.error(
            "waveshare_epd library not found. "
            "Install it from https://github.com/waveshare/e-Paper"
        )
        # Save to file as fallback for development/testing
        out = SCRIPT_DIR / "dashboard_preview.bmp"
        img.save(str(out))
        log.info("Saved preview to %s", out)
        return

    epd = epd2in13_V4.EPD()
    try:
        epd.init()
        epd.display(epd.getbuffer(img))
        epd.sleep()
    except Exception as e:
        log.error("Display error: %s", e)
        raise
    finally:
        try:
            import waveshare_epd.epdconfig as epdconfig
            epdconfig.module_exit(cleanup=True)
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    log.info("Weather dashboard starting")

    cfg = load_config()

    if cfg.get("api_key", "").startswith("YOUR_"):
        log.error("Please set your OpenWeatherMap API key in %s", CONFIG_PATH)
        sys.exit(1)

    weather = get_weather(cfg)
    if weather is None:
        log.error("No weather data available (API failed and no cache)")
        sys.exit(1)

    img = render_dashboard(cfg, weather)
    display_image(img)

    log.info("Dashboard updated successfully")


if __name__ == "__main__":
    main()
