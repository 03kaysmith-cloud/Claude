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

# ── 6. Remove old cron job if present ──────────────────────────────────
(crontab -l 2>/dev/null | grep -v "weather_dashboard.py" || true) | crontab -

# ── 7. Install systemd service ────────────────────────────────────────
echo "[6/6] Installing systemd service..."
sudo tee /etc/systemd/system/weather-dashboard.service > /dev/null <<UNIT
[Unit]
Description=Weather Dashboard e-Paper Server
After=network-online.target
Wants=network-online.target

[Service]
ExecStart=$VENV_DIR/bin/python $SCRIPT_DIR/server.py
WorkingDirectory=$SCRIPT_DIR
Restart=always
RestartSec=10
User=$(whoami)

[Install]
WantedBy=multi-user.target
UNIT

sudo systemctl daemon-reload
sudo systemctl enable weather-dashboard.service
sudo systemctl start weather-dashboard.service

echo ""
echo "=== Installation complete ==="
echo ""
echo "The web server is running on port 5000."
echo "Open http://$(hostname -I | awk '{print $1}'):5000 in your browser."
echo ""
echo "To run manually:"
echo "  source $VENV_DIR/bin/activate"
echo "  python $SCRIPT_DIR/server.py"
echo ""
echo "To view logs:"
echo "  sudo journalctl -u weather-dashboard -f"
echo ""
echo "To stop the service:"
echo "  sudo systemctl stop weather-dashboard"
