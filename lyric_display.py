#!/usr/bin/env python3
"""
Pixelated Lyric Display
Displays synchronized lyrics with a chunky pixel-font look,
designed for small/tiny displays.
"""

import time
import sys
import os

# --- Pixel font data (5x7 grid per character) ---
# Each character is a list of 7 rows, each row a 5-bit pattern.
PIXEL_FONT = {
    'A': [0b01110, 0b10001, 0b10001, 0b11111, 0b10001, 0b10001, 0b10001],
    'B': [0b11110, 0b10001, 0b10001, 0b11110, 0b10001, 0b10001, 0b11110],
    'C': [0b01110, 0b10001, 0b10000, 0b10000, 0b10000, 0b10001, 0b01110],
    'D': [0b11110, 0b10001, 0b10001, 0b10001, 0b10001, 0b10001, 0b11110],
    'E': [0b11111, 0b10000, 0b10000, 0b11110, 0b10000, 0b10000, 0b11111],
    'F': [0b11111, 0b10000, 0b10000, 0b11110, 0b10000, 0b10000, 0b10000],
    'G': [0b01110, 0b10001, 0b10000, 0b10111, 0b10001, 0b10001, 0b01110],
    'H': [0b10001, 0b10001, 0b10001, 0b11111, 0b10001, 0b10001, 0b10001],
    'I': [0b01110, 0b00100, 0b00100, 0b00100, 0b00100, 0b00100, 0b01110],
    'J': [0b00111, 0b00010, 0b00010, 0b00010, 0b00010, 0b10010, 0b01100],
    'K': [0b10001, 0b10010, 0b10100, 0b11000, 0b10100, 0b10010, 0b10001],
    'L': [0b10000, 0b10000, 0b10000, 0b10000, 0b10000, 0b10000, 0b11111],
    'M': [0b10001, 0b11011, 0b10101, 0b10101, 0b10001, 0b10001, 0b10001],
    'N': [0b10001, 0b10001, 0b11001, 0b10101, 0b10011, 0b10001, 0b10001],
    'O': [0b01110, 0b10001, 0b10001, 0b10001, 0b10001, 0b10001, 0b01110],
    'P': [0b11110, 0b10001, 0b10001, 0b11110, 0b10000, 0b10000, 0b10000],
    'Q': [0b01110, 0b10001, 0b10001, 0b10001, 0b10101, 0b10010, 0b01101],
    'R': [0b11110, 0b10001, 0b10001, 0b11110, 0b10100, 0b10010, 0b10001],
    'S': [0b01110, 0b10001, 0b10000, 0b01110, 0b00001, 0b10001, 0b01110],
    'T': [0b11111, 0b00100, 0b00100, 0b00100, 0b00100, 0b00100, 0b00100],
    'U': [0b10001, 0b10001, 0b10001, 0b10001, 0b10001, 0b10001, 0b01110],
    'V': [0b10001, 0b10001, 0b10001, 0b10001, 0b10001, 0b01010, 0b00100],
    'W': [0b10001, 0b10001, 0b10001, 0b10101, 0b10101, 0b11011, 0b10001],
    'X': [0b10001, 0b10001, 0b01010, 0b00100, 0b01010, 0b10001, 0b10001],
    'Y': [0b10001, 0b10001, 0b01010, 0b00100, 0b00100, 0b00100, 0b00100],
    'Z': [0b11111, 0b00001, 0b00010, 0b00100, 0b01000, 0b10000, 0b11111],
    '0': [0b01110, 0b10001, 0b10011, 0b10101, 0b11001, 0b10001, 0b01110],
    '1': [0b00100, 0b01100, 0b00100, 0b00100, 0b00100, 0b00100, 0b01110],
    '2': [0b01110, 0b10001, 0b00001, 0b00110, 0b01000, 0b10000, 0b11111],
    '3': [0b01110, 0b10001, 0b00001, 0b00110, 0b00001, 0b10001, 0b01110],
    '4': [0b00010, 0b00110, 0b01010, 0b10010, 0b11111, 0b00010, 0b00010],
    '5': [0b11111, 0b10000, 0b11110, 0b00001, 0b00001, 0b10001, 0b01110],
    '6': [0b01110, 0b10000, 0b10000, 0b11110, 0b10001, 0b10001, 0b01110],
    '7': [0b11111, 0b00001, 0b00010, 0b00100, 0b01000, 0b01000, 0b01000],
    '8': [0b01110, 0b10001, 0b10001, 0b01110, 0b10001, 0b10001, 0b01110],
    '9': [0b01110, 0b10001, 0b10001, 0b01111, 0b00001, 0b00001, 0b01110],
    ' ': [0b00000, 0b00000, 0b00000, 0b00000, 0b00000, 0b00000, 0b00000],
    '.': [0b00000, 0b00000, 0b00000, 0b00000, 0b00000, 0b00000, 0b00100],
    ',': [0b00000, 0b00000, 0b00000, 0b00000, 0b00000, 0b00100, 0b01000],
    '!': [0b00100, 0b00100, 0b00100, 0b00100, 0b00100, 0b00000, 0b00100],
    '?': [0b01110, 0b10001, 0b00001, 0b00110, 0b00100, 0b00000, 0b00100],
    "'": [0b00100, 0b00100, 0b01000, 0b00000, 0b00000, 0b00000, 0b00000],
    '"': [0b01010, 0b01010, 0b00000, 0b00000, 0b00000, 0b00000, 0b00000],
    '-': [0b00000, 0b00000, 0b00000, 0b11111, 0b00000, 0b00000, 0b00000],
    '(': [0b00010, 0b00100, 0b01000, 0b01000, 0b01000, 0b00100, 0b00010],
    ')': [0b01000, 0b00100, 0b00010, 0b00010, 0b00010, 0b00100, 0b01000],
    ':': [0b00000, 0b00100, 0b00100, 0b00000, 0b00100, 0b00100, 0b00000],
    ';': [0b00000, 0b00100, 0b00100, 0b00000, 0b00100, 0b00100, 0b01000],
}

# Block characters for rendering pixels
BLOCK_FULL = "\u2588"  # Full block
BLOCK_EMPTY = " "

# ANSI color codes
CYAN = "\033[96m"
WHITE = "\033[97m"
DIM = "\033[2m"
BOLD = "\033[1m"
RESET = "\033[0m"
CLEAR_SCREEN = "\033[2J\033[H"
HIDE_CURSOR = "\033[?25l"
SHOW_CURSOR = "\033[?25h"


LYRICS = [
    (8.70,  "I found the street of the house in which you stay"),
    (12.30, "And my diary's full of your name on every page"),
    (15.80, "'Cause I read somewhere you'll fall in love with me"),
    (19.30, "I'll try and try again one day, you'll see"),
    (23.00, "Your hair's under my pillow so I sleep"),
    (26.60, "And I'm dreaming of you leaving roses at my feet"),
    (30.20, "I'm obsessed with you in a way I can't believe"),
    (33.90, "When you wipe your tears do you wipe them just for me?"),
    (38.50, "Do you wipe them just for me?"),
    (41.90, "I'm pleading on my knees"),
    (45.60, "It's your touch that I need"),
    (51.90, "I followed you today, I was in my car"),
    (55.60, "I wanted to come and see you from afar"),
    (59.10, "If you turned around and saw me I would die"),
    (62.60, "I'd pretend I was a person driving by"),
    (66.30, "Wrote you a song, do you wanna hear it now?"),
    (70.00, "Don't bring your friends along to form a crowd"),
    (73.60, "'Cause I need to prove I wrote it just for you"),
    (77.20, "What's the need for them when it could be just us two?"),
    (80.70, "I'm obsessed with you in a way I can't believe"),
    (84.40, "When you wipe your tears, do you wipe them just for me?"),
    (88.90, "Do you wipe them just for me?"),
    (92.40, "I'm pleading on my knees"),
    (96.00, "It's your touch that I need"),
]


def render_pixel_text(text, scale=1):
    """Render a string as pixel-art block text.

    Args:
        text: The string to render.
        scale: Pixel scale factor (1 = smallest, 2 = chunkier).

    Returns:
        List of strings, one per row of the rendered output.
    """
    text = text.upper()
    rows = []
    for row_idx in range(7):
        line = ""
        for ch in text:
            glyph = PIXEL_FONT.get(ch, PIXEL_FONT.get(' '))
            bits = glyph[row_idx]
            for col in range(4, -1, -1):
                pixel = BLOCK_FULL * scale if (bits >> col) & 1 else BLOCK_EMPTY * scale
                line += pixel
            line += BLOCK_EMPTY * scale  # spacing between characters
        # Duplicate row for vertical scale
        for _ in range(scale):
            rows.append(line)
    return rows


def get_terminal_width():
    """Get the terminal width, defaulting to 80."""
    try:
        return os.get_terminal_size().columns
    except OSError:
        return 80


def wrap_lyric(text, max_chars):
    """Split lyric text into lines that fit within max_chars pixel-columns.

    Each character takes 6 pixel-columns at scale=1 (5 wide + 1 spacing).
    """
    chars_per_line = max(1, max_chars // 6)
    words = text.split()
    lines = []
    current = ""
    for word in words:
        test = (current + " " + word).strip()
        if len(test) <= chars_per_line:
            current = test
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines if lines else [text]


def display_lyric(text, term_width):
    """Render and print a lyric line as pixelated text, centered."""
    lines = wrap_lyric(text, term_width)
    all_rows = []
    for line_text in lines:
        rendered = render_pixel_text(line_text, scale=1)
        all_rows.extend(rendered)
        all_rows.append("")  # blank line between wrapped segments

    # Center each row
    output = []
    for row in all_rows:
        padding = max(0, (term_width - len(row)) // 2)
        output.append(" " * padding + row)

    return "\n".join(output)


def draw_progress_bar(elapsed, total, width):
    """Draw a thin progress bar."""
    filled = int((elapsed / total) * width) if total > 0 else 0
    filled = min(filled, width)
    bar = CYAN + BLOCK_FULL * filled + DIM + "\u2591" * (width - filled) + RESET
    return bar


def format_time(seconds):
    """Format seconds as MM:SS."""
    m = int(seconds) // 60
    s = int(seconds) % 60
    return f"{m:02d}:{s:02d}"


def main():
    total_duration = LYRICS[-1][0] + 8.0  # a few seconds after last lyric
    term_width = get_terminal_width()
    bar_width = min(term_width - 14, 60)

    print(HIDE_CURSOR, end="", flush=True)

    try:
        # Title screen
        print(CLEAR_SCREEN, end="")
        title_rows = render_pixel_text("LYRICS", scale=2)
        for row in title_rows:
            padding = max(0, (term_width - len(row)) // 2)
            print(CYAN + " " * padding + row + RESET)
        print()
        subtitle = "[ press ENTER to start ]"
        print(" " * max(0, (term_width - len(subtitle)) // 2) + DIM + subtitle + RESET)
        input()

        start_time = time.time()
        current_idx = 0
        displayed_idx = -1

        while True:
            elapsed = time.time() - start_time
            if elapsed > total_duration:
                break

            # Check if we need to advance to the next lyric
            if current_idx < len(LYRICS) - 1 and elapsed >= LYRICS[current_idx + 1][0]:
                current_idx += 1

            # Find the correct lyric for the current time
            active = -1
            for i, (ts, _) in enumerate(LYRICS):
                if elapsed >= ts:
                    active = i

            if active != displayed_idx and active >= 0:
                displayed_idx = active
                ts, text = LYRICS[active]

                print(CLEAR_SCREEN, end="")

                # Show previous lyric dimmed
                if active > 0:
                    prev_text = LYRICS[active - 1][1]
                    prev_rendered = display_lyric(prev_text, term_width)
                    print(DIM + prev_rendered + RESET)
                    print()

                # Show current lyric bright
                cur_rendered = display_lyric(text, term_width)
                print(BOLD + WHITE + cur_rendered + RESET)
                print()

                # Show next lyric dimmed
                if active < len(LYRICS) - 1:
                    next_text = LYRICS[active + 1][1]
                    next_rendered = display_lyric(next_text, term_width)
                    print(DIM + next_rendered + RESET)

                # Progress bar at bottom
                print()
                time_str = f" {format_time(elapsed)} "
                end_str = f" {format_time(total_duration)} "
                bar = draw_progress_bar(elapsed, total_duration, bar_width)
                bar_line = time_str + bar + end_str
                print(" " * max(0, (term_width - len(time_str) - bar_width - len(end_str)) // 2) + bar_line)

                sys.stdout.flush()

            time.sleep(0.05)

        # End screen
        print(CLEAR_SCREEN, end="")
        end_rows = render_pixel_text("END", scale=2)
        print()
        for row in end_rows:
            padding = max(0, (term_width - len(row)) // 2)
            print(CYAN + " " * padding + row + RESET)
        print()

    except KeyboardInterrupt:
        pass
    finally:
        print(SHOW_CURSOR, end="", flush=True)


if __name__ == "__main__":
    main()
