#!/usr/bin/env bash
# install.sh - Set up the weather dashboard on Raspberry Pi OS Lite
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "=== Weather Dashboard Installer ==="
echo ""

# ── 1. Enable SPI interface ──────────────────────────────────────────────
echo "[1/6] Checking SPI interface..."
if ! grep -q "^dtparam=spi=on" /boot/config.txt 2>/dev/null && \
   ! grep -q "^dtparam=spi=on" /boot/firmware/config.txt 2>/dev/null; then
    echo "  Enabling SPI interface..."
    sudo raspi-config nonint do_spi 0
    echo "  SPI enabled. A reboot may be required."
else
    echo "  SPI already enabled."
fi

# ── 2. Install system dependencies ───────────────────────────────────────
echo "[2/6] Installing system packages..."
sudo apt-get update -qq
sudo apt-get install -y -qq \
    python3-pip \
    python3-pil \
    python3-numpy \
    python3-venv \
    python3-gpiozero \
    fonts-dejavu-core \
    git

# ── 3. Create virtual environment ────────────────────────────────────────
echo "[3/6] Setting up Python virtual environment..."
VENV_DIR="$SCRIPT_DIR/venv"
if [ ! -d "$VENV_DIR" ]; then
    python3 -m venv --system-site-packages "$VENV_DIR"
fi
source "$VENV_DIR/bin/activate"

pip install --quiet -r "$SCRIPT_DIR/requirements.txt"
pip install --quiet spidev RPi.GPIO

# ── 4. Install Waveshare e-Paper library ─────────────────────────────────
echo "[4/6] Installing Waveshare e-Paper library..."
WAVESHARE_DIR="/tmp/e-Paper"
if [ -d "$WAVESHARE_DIR" ]; then
    rm -rf "$WAVESHARE_DIR"
fi
git clone --depth 1 https://github.com/waveshare/e-Paper.git "$WAVESHARE_DIR"
pip install --quiet "$WAVESHARE_DIR/RaspberryPi_JetsonNano/python/"

# ── 5. Set up configuration ─────────────────────────────────────────────
echo "[5/6] Checking configuration..."
if grep -q "YOUR_OPENWEATHERMAP_API_KEY" "$SCRIPT_DIR/config.json"; then
    echo ""
    echo "  *** ACTION REQUIRED ***"
    echo "  Edit $SCRIPT_DIR/config.json and set your OpenWeatherMap API key."
    echo "  Get a free key at: https://openweathermap.org/api"
    echo ""
fi

# ── 6. Install cron job ─────────────────────────────────────────────────
echo "[6/6] Installing cron job (runs every minute)..."
CRON_CMD="* * * * * $VENV_DIR/bin/python $SCRIPT_DIR/weather_dashboard.py >> /tmp/weather_dashboard.log 2>&1"
# Remove old entry if present, then add new one
(crontab -l 2>/dev/null | grep -v "weather_dashboard.py" || true; echo "$CRON_CMD") | crontab -

echo ""
echo "=== Installation complete ==="
echo ""
echo "The dashboard will run every minute via cron."
echo "Weather data is cached and only refreshed every 15 minutes."
echo ""
echo "To run manually:"
echo "  source $VENV_DIR/bin/activate"
echo "  python $SCRIPT_DIR/weather_dashboard.py"
echo ""
echo "To view logs:"
echo "  tail -f /tmp/weather_dashboard.log"
echo ""
echo "To remove the cron job:"
echo "  crontab -l | grep -v weather_dashboard.py | crontab -"
