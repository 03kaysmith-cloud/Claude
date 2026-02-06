/*
 * Lyric Display - ESP32 + SSD1306 OLED
 *
 * Receives lyric text from a Windows PC over USB serial and displays
 * it on a 0.96" SSD1306 OLED (128x64, I2C).
 *
 * Protocol (newline-delimited):
 *   PC -> ESP32:  CLR | TXT|<text> | PING | FONT|<1-3>
 *   ESP32 -> PC:  PONG | BTN|PRESS | BTN|LONG
 *
 * Hardware:
 *   - SSD1306 OLED: SDA=GPIO21, SCL=GPIO22, addr 0x3C
 *   - Button: GPIO4 with internal pull-up (active LOW)
 */

#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>

// ── Display configuration ───────────────────────────────────────────
#define SCREEN_WIDTH    128
#define SCREEN_HEIGHT   64
#define OLED_RESET      -1
#define SCREEN_ADDRESS  0x3C
#define SDA_PIN         21
#define SCL_PIN         22

// ── Button configuration ────────────────────────────────────────────
#define BUTTON_PIN      4
#define DEBOUNCE_MS     50
#define LONG_PRESS_MS   700

// ── Serial configuration ────────────────────────────────────────────
#define BAUD_RATE       115200
#define SERIAL_BUF_SIZE 512

// ── Scrolling configuration ─────────────────────────────────────────
#define SCROLL_INTERVAL_MS 2000
#define SCROLL_STEP        16     // pixels per scroll step

// ── Connection timeout ──────────────────────────────────────────────
#define CONNECTION_TIMEOUT_MS 10000

// ── Objects ─────────────────────────────────────────────────────────
Adafruit_SSD1306 display(SCREEN_WIDTH, SCREEN_HEIGHT, &Wire, OLED_RESET);

// ── Text / display state ────────────────────────────────────────────
String currentText     = "";
uint8_t textSize       = 2;       // Adafruit GFX text size (1-3)
int  scrollOffset      = 0;
int  totalTextHeight   = 0;
unsigned long lastScrollTime = 0;

// ── Button state ────────────────────────────────────────────────────
bool  lastButtonReading = HIGH;
bool  buttonState       = HIGH;
unsigned long lastDebounceTime = 0;
unsigned long buttonPressTime  = 0;
bool  buttonHeld      = false;
bool  longPressSent   = false;

// ── Connection state ────────────────────────────────────────────────
bool connected = false;
unsigned long lastActivityTime = 0;   // last time we heard from PC

// ── Serial buffer ───────────────────────────────────────────────────
char serialBuffer[SERIAL_BUF_SIZE];
int  bufferPos = 0;

// ═══════════════════════════════════════════════════════════════════
//  SETUP
// ═══════════════════════════════════════════════════════════════════
void setup() {
    Serial.begin(BAUD_RATE);

    Wire.begin(SDA_PIN, SCL_PIN);

    if (!display.begin(SSD1306_SWITCHCAPVCC, SCREEN_ADDRESS)) {
        // If display init fails, blink onboard LED forever
        pinMode(2, OUTPUT);
        while (true) {
            digitalWrite(2, !digitalRead(2));
            delay(300);
        }
    }

    display.clearDisplay();
    display.setTextColor(SSD1306_WHITE);
    display.setTextWrap(false);   // we handle wrapping manually
    showStatus("Waiting for", "connection...");

    pinMode(BUTTON_PIN, INPUT_PULLUP);

    lastActivityTime = millis();
}

// ═══════════════════════════════════════════════════════════════════
//  LOOP
// ═══════════════════════════════════════════════════════════════════
void loop() {
    handleSerial();
    handleButton();
    handleScrolling();
    handleConnectionTimeout();
}

// ═══════════════════════════════════════════════════════════════════
//  SERIAL HANDLING
// ═══════════════════════════════════════════════════════════════════
void handleSerial() {
    while (Serial.available()) {
        char c = (char)Serial.read();
        if (c == '\n' || c == '\r') {
            if (bufferPos > 0) {
                serialBuffer[bufferPos] = '\0';
                processCommand(String(serialBuffer));
                bufferPos = 0;
            }
        } else if (bufferPos < SERIAL_BUF_SIZE - 1) {
            serialBuffer[bufferPos++] = c;
        }
    }
}

void processCommand(String cmd) {
    cmd.trim();
    if (cmd.length() == 0) return;

    lastActivityTime = millis();

    if (cmd == "PING") {
        Serial.println("PONG");
        if (!connected) {
            connected = true;
            // If no text to show, display connected status
            if (currentText.length() == 0) {
                showStatus("Connected", "");
            }
        }
    }
    else if (cmd == "CLR") {
        currentText = "";
        scrollOffset = 0;
        display.clearDisplay();
        display.display();
        if (!connected) connected = true;
    }
    else if (cmd.startsWith("TXT|")) {
        String text = cmd.substring(4);
        if (!connected) connected = true;
        if (text != currentText) {
            currentText = text;
            scrollOffset = 0;
            lastScrollTime = millis();
            renderText();
        }
    }
    else if (cmd.startsWith("FONT|")) {
        int size = cmd.substring(5).toInt();
        if (size >= 1 && size <= 3) {
            if (size != textSize) {
                textSize = (uint8_t)size;
                scrollOffset = 0;
                lastScrollTime = millis();
                renderText();
            }
        }
        if (!connected) connected = true;
    }
}

// ═══════════════════════════════════════════════════════════════════
//  TEXT RENDERING  (word-wrap + vertical scroll)
// ═══════════════════════════════════════════════════════════════════
void renderText() {
    display.clearDisplay();

    if (currentText.length() == 0) {
        display.display();
        return;
    }

    display.setTextSize(textSize);

    int charW = 6 * textSize;          // pixel width of one character
    int charH = 8 * textSize;          // pixel height of one character
    int charsPerLine = SCREEN_WIDTH / charW;

    if (charsPerLine < 1) charsPerLine = 1;

    // ── Word-wrap into lines ────────────────────────────────────
    #define MAX_WRAP_LINES 32
    String lines[MAX_WRAP_LINES];
    int lineCount = 0;
    int len = currentText.length();
    int pos = 0;

    while (pos < len && lineCount < MAX_WRAP_LINES) {
        int remaining = len - pos;
        if (remaining <= charsPerLine) {
            lines[lineCount++] = currentText.substring(pos);
            break;
        }

        int breakAt = pos + charsPerLine;
        // Try to break at a space
        int lastSpace = -1;
        for (int i = pos; i < breakAt && i < len; i++) {
            if (currentText.charAt(i) == ' ') {
                lastSpace = i;
            }
        }

        if (lastSpace > pos) {
            lines[lineCount++] = currentText.substring(pos, lastSpace);
            pos = lastSpace + 1;
        } else {
            // No space found – hard break
            lines[lineCount++] = currentText.substring(pos, breakAt);
            pos = breakAt;
        }
    }

    totalTextHeight = lineCount * charH;

    // ── Draw visible lines ──────────────────────────────────────
    int startY = -scrollOffset;
    for (int i = 0; i < lineCount; i++) {
        int y = startY + i * charH;
        if (y + charH > 0 && y < SCREEN_HEIGHT) {
            display.setCursor(0, y);
            display.print(lines[i]);
        }
    }

    // ── Connection indicator (top-right dot) ────────────────────
    if (connected) {
        display.fillCircle(SCREEN_WIDTH - 4, 3, 2, SSD1306_WHITE);
    }

    display.display();
}

// ═══════════════════════════════════════════════════════════════════
//  SCROLLING
// ═══════════════════════════════════════════════════════════════════
void handleScrolling() {
    if (totalTextHeight <= SCREEN_HEIGHT) return;
    if (currentText.length() == 0) return;

    unsigned long now = millis();
    if (now - lastScrollTime < SCROLL_INTERVAL_MS) return;

    lastScrollTime = now;

    int maxScroll = totalTextHeight - SCREEN_HEIGHT;
    scrollOffset += SCROLL_STEP;

    if (scrollOffset > maxScroll) {
        scrollOffset = 0;            // wrap back to top
    }

    renderText();
}

// ═══════════════════════════════════════════════════════════════════
//  BUTTON HANDLING  (debounce + short/long press)
// ═══════════════════════════════════════════════════════════════════
void handleButton() {
    bool reading = digitalRead(BUTTON_PIN);

    if (reading != lastButtonReading) {
        lastDebounceTime = millis();
    }

    if ((millis() - lastDebounceTime) > DEBOUNCE_MS) {
        if (reading != buttonState) {
            buttonState = reading;

            if (buttonState == LOW) {
                // Pressed
                buttonPressTime = millis();
                buttonHeld    = true;
                longPressSent = false;
            } else {
                // Released
                if (buttonHeld && !longPressSent) {
                    Serial.println("BTN|PRESS");
                }
                buttonHeld = false;
            }
        }
    }

    // Long-press detection while held
    if (buttonHeld && !longPressSent && buttonState == LOW) {
        if (millis() - buttonPressTime >= LONG_PRESS_MS) {
            Serial.println("BTN|LONG");
            longPressSent = true;
        }
    }

    lastButtonReading = reading;
}

// ═══════════════════════════════════════════════════════════════════
//  CONNECTION TIMEOUT
// ═══════════════════════════════════════════════════════════════════
void handleConnectionTimeout() {
    if (!connected) return;

    if (millis() - lastActivityTime > CONNECTION_TIMEOUT_MS) {
        connected = false;
        currentText = "";
        scrollOffset = 0;
        totalTextHeight = 0;
        showStatus("Disconnected", "");
    }
}

// ═══════════════════════════════════════════════════════════════════
//  STATUS SCREEN  (small font, two lines)
// ═══════════════════════════════════════════════════════════════════
void showStatus(const char* line1, const char* line2) {
    display.clearDisplay();
    display.setTextSize(1);
    display.setCursor(0, 24);
    display.print(line1);
    if (line2 && strlen(line2) > 0) {
        display.setCursor(0, 36);
        display.print(line2);
    }
    display.display();
}
