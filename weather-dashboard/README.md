# Weather Dashboard for Raspberry Pi e-Paper Display

A minimal weather dashboard for the **Waveshare 2.13inch e-Paper Display HAT** (250x122, black & white) running on a **Raspberry Pi Zero 2 WH**.

## What it displays

```
+------------------------------------------+
| Mon 10 Feb 14:30     Acton Town  [icon]  |
| 12°C                                     |
| Overcast clouds          | Tomorrow (Tue)|
| Feels 9°                 | 06:00 3° Cloud|
| Wind: 5 m/s              | 18:00 8° Rain |
| ^ 07:15  v 17:02                         |
+------------------------------------------+
```

- **Top left**: Date & time (updates every minute)
- **Top right**: Weather icon + location name
- **Centre left**: Current temperature (large), description, feels-like, wind
- **Bottom left**: Sunrise & sunset times
- **Bottom right**: Tomorrow's forecast at 06:00 and 18:00

## Requirements

- Raspberry Pi Zero 2 WH (or any Pi with GPIO header)
- Waveshare 2.13inch e-Paper Display HAT (250x122, V4 recommended)
- Raspberry Pi OS Lite
- OpenWeatherMap API key (free tier works)

## Quick install

```bash
# Clone or copy this directory to your Pi, then:
cd weather-dashboard
chmod +x install.sh
sudo ./install.sh
```

The install script will:
1. Enable the SPI interface
2. Install system packages (python3-pip, python3-pil, fonts, etc.)
3. Create a Python virtual environment with dependencies
4. Clone and install the Waveshare e-Paper library
5. Prompt you to set your API key
6. Install a cron job that runs every minute

## Manual install

### 1. Enable SPI

```bash
sudo raspi-config nonint do_spi 0
# Reboot if this is the first time enabling SPI
sudo reboot
```

### 2. Install system packages

```bash
sudo apt-get update
sudo apt-get install -y python3-pip python3-pil python3-numpy \
    python3-venv python3-gpiozero fonts-dejavu-core git
```

### 3. Set up Python environment

```bash
python3 -m venv --system-site-packages venv
source venv/bin/activate
pip install -r requirements.txt
pip install spidev RPi.GPIO
```

### 4. Install Waveshare library

```bash
git clone --depth 1 https://github.com/waveshare/e-Paper.git /tmp/e-Paper
pip install /tmp/e-Paper/RaspberryPi_JetsonNano/python/
```

### 5. Configure

Edit `config.json` and set your OpenWeatherMap API key:

```json
{
    "api_key": "your_actual_api_key_here",
    "latitude": 51.5033,
    "longitude": -0.2804,
    "location_name": "Acton Town",
    "units": "metric",
    "cache_file": "/tmp/weather_cache.json",
    "cache_max_age_minutes": 15,
    "display_width": 250,
    "display_height": 122
}
```

Get a free API key at https://openweathermap.org/api

### 6. Run

```bash
source venv/bin/activate
python weather_dashboard.py
```

### 7. Set up cron job

```bash
crontab -e
```

Add this line (adjust the path):

```
* * * * * /home/pi/weather-dashboard/venv/bin/python /home/pi/weather-dashboard/weather_dashboard.py >> /tmp/weather_dashboard.log 2>&1
```

## Configuration options

| Key | Description | Default |
|-----|-------------|---------|
| `api_key` | OpenWeatherMap API key | (required) |
| `latitude` | Location latitude | 51.5033 (Acton Town) |
| `longitude` | Location longitude | -0.2804 (Acton Town) |
| `location_name` | Display name for location | Acton Town |
| `units` | `metric` or `imperial` | metric |
| `cache_file` | Path for weather data cache | /tmp/weather_cache.json |
| `cache_max_age_minutes` | Minutes before refreshing weather | 15 |
| `display_width` | Display width in pixels | 250 |
| `display_height` | Display height in pixels | 122 |

## How caching works

- The script runs every minute via cron
- On each run it checks the cached weather data age
- If the cache is less than 15 minutes old, it reuses it (only the time display changes)
- If the cache is stale, it fetches fresh data from OpenWeatherMap
- If the API call fails, it falls back to the stale cache
- This keeps API usage well within the free tier (96 calls/day max)

## Development / testing without hardware

When the Waveshare library is not installed (e.g. on a laptop), the script saves a BMP preview to `dashboard_preview.bmp` in the project directory instead of writing to the display.

## Logs

```bash
tail -f /tmp/weather_dashboard.log
```

## Troubleshooting

- **SPI not enabled**: Run `sudo raspi-config` and enable SPI under Interface Options
- **Display not updating**: Check wiring connections and ensure the HAT is seated properly
- **API errors**: Verify your API key in config.json; check `/tmp/weather_dashboard.log`
- **Font issues**: Install `fonts-dejavu-core` (`sudo apt install fonts-dejavu-core`)
