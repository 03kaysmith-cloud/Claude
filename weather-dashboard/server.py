#!/usr/bin/env python3
"""
Web server for controlling the e-Paper display.

Serves a web UI for switching between display modes (weather, clock, facts)
and provides a live preview of the current display content.

Run: python server.py
Then open http://localhost:5000 (or http://<pi-ip>:5000 from another device)
"""

import io
import logging
import random
import textwrap
import threading
import time
from datetime import datetime

from flask import Flask, jsonify, render_template, request, send_file
from PIL import Image, ImageDraw

from weather_dashboard import (
    display_image,
    get_font,
    get_font_bold,
    get_weather,
    load_config,
    render_dashboard,
)

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger("epaper_server")

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------
app = Flask(__name__)

# ---------------------------------------------------------------------------
# State
# ---------------------------------------------------------------------------
state_lock = threading.Lock()
current_mode = "weather"
last_image: Image.Image | None = None

VALID_MODES = {"weather", "clock", "facts"}

UPDATE_INTERVALS = {
    "weather": 60,
    "clock": 30,
    "facts": 300,
}

# ---------------------------------------------------------------------------
# Facts
# ---------------------------------------------------------------------------
FACTS = [
    "Honey never spoils. Archaeologists have found 3000-year-old honey in Egyptian tombs that was still edible.",
    "An octopus has three hearts and blue blood.",
    "Bananas are berries, but strawberries are not.",
    "A group of flamingos is called a 'flamboyance'.",
    "The Eiffel Tower can be 15cm taller during the summer due to thermal expansion.",
    "Wombat droppings are cube-shaped to stop them rolling away.",
    "The shortest war in history lasted 38 to 45 minutes, between Britain and Zanzibar in 1896.",
    "A day on Venus is longer than a year on Venus.",
    "Sharks have been around longer than trees.",
    "The heart of a shrimp is located in its head.",
    "Cows have best friends and get stressed when separated.",
    "Scotland's national animal is the unicorn.",
    "There are more possible iterations of a game of chess than atoms in the observable universe.",
    "Hot water freezes faster than cold water under certain conditions. This is called the Mpemba effect.",
    "A jiffy is an actual unit of time: 1/100th of a second.",
    "The inventor of the Pringles can is buried in one.",
    "Cleopatra lived closer in time to the Moon landing than to the construction of the Great Pyramid.",
    "Astronauts grow up to 5cm taller in space due to spinal decompression.",
    "The total weight of all ants on Earth roughly equals the total weight of all humans.",
    "A bolt of lightning is five times hotter than the surface of the Sun.",
    "Glaciers and ice sheets hold about 69% of the world's freshwater.",
    "The average person walks the equivalent of five times around the world in a lifetime.",
    "Octopuses have been observed using coconut shells as portable shelters.",
    "The tongue of a blue whale weighs as much as an elephant.",
    "Sloths can hold their breath longer than dolphins can — up to 40 minutes.",
    "There are more stars in the universe than grains of sand on all Earth's beaches.",
    "A single strand of spider silk is thinner than a human hair but stronger than steel of the same weight.",
    "The Great Wall of China is not visible from space with the naked eye, but many highways are.",
    "Tardigrades can survive in the vacuum of space.",
    "Humans share about 60% of their DNA with bananas.",
    "Oxford University is older than the Aztec Empire.",
    "A photon takes about 8 minutes to travel from the Sun to Earth.",
    "The longest hiccupping spree lasted 68 years.",
    "Butterflies taste with their feet.",
    "Rain has a smell because of a molecule called geosmin, produced by soil bacteria.",
]

# ---------------------------------------------------------------------------
# Renderers
# ---------------------------------------------------------------------------

def render_clock(cfg: dict) -> Image.Image:
    """Render a large centered clock display."""
    W = cfg.get("display_width", 250)
    H = cfg.get("display_height", 122)

    img = Image.new("1", (W, H), 255)
    draw = ImageDraw.Draw(img)

    now = datetime.now()
    time_str = now.strftime("%H:%M")
    date_str = now.strftime("%A, %d %b")

    font_big = get_font_bold(36)
    font_sm = get_font(12)

    # Center the time
    tb = draw.textbbox((0, 0), time_str, font=font_big)
    tw = tb[2] - tb[0]
    draw.text(((W - tw) // 2, 20), time_str, font=font_big, fill=0)

    # Separator line
    draw.line([(W // 2 - 40, 68), (W // 2 + 40, 68)], fill=0, width=1)

    # Center the date
    db = draw.textbbox((0, 0), date_str, font=font_sm)
    dw = db[2] - db[0]
    draw.text(((W - dw) // 2, 78), date_str, font=font_sm, fill=0)

    return img


def render_facts(cfg: dict) -> Image.Image:
    """Render a random fact with word wrapping."""
    W = cfg.get("display_width", 250)
    H = cfg.get("display_height", 122)

    img = Image.new("1", (W, H), 255)
    draw = ImageDraw.Draw(img)

    font_title = get_font_bold(11)
    font_body = get_font(10)

    draw.text((4, 4), "Did you know?", font=font_title, fill=0)
    draw.line([(4, 18), (W - 4, 18)], fill=0)

    fact = random.choice(FACTS)
    lines = textwrap.wrap(fact, width=38)
    y = 24
    for line in lines[:7]:
        draw.text((4, y), line, font=font_body, fill=0)
        y += 14

    return img


def render_error(message: str) -> Image.Image:
    """Render an error/status message on the display."""
    img = Image.new("1", (250, 122), 255)
    draw = ImageDraw.Draw(img)
    font = get_font(10)
    lines = textwrap.wrap(message, width=38)
    y = 30
    for line in lines[:5]:
        draw.text((10, y), line, font=font, fill=0)
        y += 14
    return img


# ---------------------------------------------------------------------------
# Core render + display
# ---------------------------------------------------------------------------

def do_render() -> Image.Image:
    """Render the current mode and return the image."""
    cfg = load_config()
    mode = current_mode

    if mode == "weather":
        weather = get_weather(cfg)
        if weather:
            return render_dashboard(cfg, weather)
        return render_error("No weather data. Check API key in config.json.")
    elif mode == "clock":
        return render_clock(cfg)
    elif mode == "facts":
        return render_facts(cfg)

    return render_error(f"Unknown mode: {mode}")


def do_render_and_display():
    """Render, store the image, and push to the e-Paper display."""
    global last_image
    img = do_render()
    with state_lock:
        last_image = img
    try:
        display_image(img)
    except Exception:
        log.exception("Display error (non-fatal)")


# ---------------------------------------------------------------------------
# Background update loop
# ---------------------------------------------------------------------------

def update_loop():
    """Periodically re-render the active mode."""
    while True:
        try:
            do_render_and_display()
        except Exception:
            log.exception("Error in update loop")

        interval = UPDATE_INTERVALS.get(current_mode, 60)
        time.sleep(interval)


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/status")
def api_status():
    return jsonify({"mode": current_mode})


@app.route("/api/mode", methods=["POST"])
def api_set_mode():
    global current_mode
    data = request.get_json(silent=True) or {}
    mode = data.get("mode", "")

    if mode not in VALID_MODES:
        return jsonify({"error": f"Invalid mode. Choose from: {sorted(VALID_MODES)}"}), 400

    current_mode = mode
    log.info("Mode switched to: %s", mode)

    # Render immediately so the preview updates right away
    try:
        do_render_and_display()
    except Exception:
        log.exception("Error rendering after mode switch")

    return jsonify({"mode": current_mode})


@app.route("/api/preview.bmp")
def api_preview():
    with state_lock:
        img = last_image
    if img is None:
        return "No image yet", 503
    buf = io.BytesIO()
    img.save(buf, format="BMP")
    buf.seek(0)
    return send_file(buf, mimetype="image/bmp", download_name="preview.bmp")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    cfg = load_config()
    port = cfg.get("server_port", 5000)

    # Initial render
    log.info("Performing initial render...")
    try:
        do_render_and_display()
    except Exception:
        log.exception("Initial render failed (will retry in background)")

    # Start background update thread
    thread = threading.Thread(target=update_loop, daemon=True)
    thread.start()

    log.info("Starting web server on port %d", port)
    app.run(host="0.0.0.0", port=port, debug=False)


if __name__ == "__main__":
    main()
