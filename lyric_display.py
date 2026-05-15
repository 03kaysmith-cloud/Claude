#!/usr/bin/env python3
"""
Pixelated Lyric Display (Minecraft-style)

Renders lyrics at a tiny internal resolution then scales up to the window,
giving a chunky pixel-font look like Minecraft text.
Designed for small displays with a normal (16:9) aspect ratio.

Controls:
  ENTER / SPACE  - Start playback
  ESC / Q        - Quit
"""

import sys
import time

import pygame

# ---------------------------------------------------------------------------
# Display settings — tune these for your physical display
# ---------------------------------------------------------------------------
# Internal "virtual" resolution (tiny, so everything looks pixelated)
INTERNAL_W = 256
INTERNAL_H = 144  # 16:9

# Window size (the internal surface gets scaled up to fill this)
WINDOW_W = 768
WINDOW_H = 432  # 16:9

# ---------------------------------------------------------------------------
# Colours
# ---------------------------------------------------------------------------
BG = (18, 18, 24)
TEXT_ACTIVE = (255, 255, 255)
TEXT_DIM = (80, 80, 100)
TEXT_ECHO = (50, 50, 65)
ACCENT = (90, 220, 255)
BAR_BG = (40, 40, 55)

# ---------------------------------------------------------------------------
# Lyrics with timestamps (seconds)
# ---------------------------------------------------------------------------
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


def make_pixel_font(size):
    """Create a pygame SysFont — small size + no antialiasing = pixel look."""
    # Try common monospace/pixel-friendly fonts, fall back to pygame default
    for name in ("monospace", "couriernew", "courier", "dejavusansmono", None):
        try:
            font = pygame.font.SysFont(name, size)
            return font
        except Exception:
            continue
    return pygame.font.Font(None, size)


def word_wrap(text, font, max_width):
    """Break text into lines that fit within max_width pixels."""
    words = text.split()
    lines = []
    current = ""
    for word in words:
        test = (current + " " + word).strip()
        if font.size(test)[0] <= max_width:
            current = test
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines if lines else [""]


def draw_text_centered(surface, font, text, y, color, max_width=None):
    """Render text centered on surface at y. Word-wraps if max_width given.
    Returns the total height used."""
    if max_width is None:
        max_width = surface.get_width() - 8
    lines = word_wrap(text, font, max_width)
    total_h = 0
    for line in lines:
        # antialias=False gives hard pixel edges
        rendered = font.render(line, False, color)
        x = (surface.get_width() - rendered.get_width()) // 2
        surface.blit(rendered, (x, y + total_h))
        total_h += rendered.get_height() + 1
    return total_h


def draw_progress_bar(surface, elapsed, total, y):
    """Draw a thin progress bar near the bottom."""
    bar_margin = 12
    bar_h = 3
    bar_w = surface.get_width() - bar_margin * 2
    # Background
    pygame.draw.rect(surface, BAR_BG, (bar_margin, y, bar_w, bar_h))
    # Filled portion
    if total > 0:
        fill_w = max(1, int((elapsed / total) * bar_w))
        fill_w = min(fill_w, bar_w)
        pygame.draw.rect(surface, ACCENT, (bar_margin, y, fill_w, bar_h))


def get_active_lyric(elapsed):
    """Return the index of the current lyric, or -1 if before first line."""
    active = -1
    for i, (ts, _) in enumerate(LYRICS):
        if elapsed >= ts:
            active = i
    return active


def main():
    pygame.init()
    screen = pygame.display.set_mode((WINDOW_W, WINDOW_H))
    pygame.display.set_caption("Lyric Display")

    # The tiny internal surface — everything draws here first
    canvas = pygame.Surface((INTERNAL_W, INTERNAL_H))

    # Pixel font at a small size (renders crisp at internal res, chunky when scaled)
    font_big = make_pixel_font(9)
    font_small = make_pixel_font(7)

    clock = pygame.time.Clock()
    total_duration = LYRICS[-1][0] + 6.0

    # --- Title screen ---
    waiting = True
    while waiting:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                return
            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_RETURN, pygame.K_SPACE):
                    waiting = False
                elif event.key in (pygame.K_ESCAPE, pygame.K_q):
                    pygame.quit()
                    return

        canvas.fill(BG)
        draw_text_centered(canvas, font_big, "LYRICS", INTERNAL_H // 2 - 14, ACCENT)
        draw_text_centered(canvas, font_small, "press ENTER to start", INTERNAL_H // 2 + 4, TEXT_DIM)

        scaled = pygame.transform.scale(canvas, (WINDOW_W, WINDOW_H))
        screen.blit(scaled, (0, 0))
        pygame.display.flip()
        clock.tick(30)

    # --- Playback ---
    start_time = time.time()
    prev_active = -2

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_ESCAPE, pygame.K_q):
                    running = False

        elapsed = time.time() - start_time
        if elapsed > total_duration:
            break

        active = get_active_lyric(elapsed)

        # Only redraw when the active lyric changes (saves cycles)
        if active != prev_active:
            prev_active = active
            canvas.fill(BG)

            if active < 0:
                # Before first lyric — show waiting dots
                draw_text_centered(canvas, font_small, ". . .", INTERNAL_H // 2 - 4, TEXT_DIM)
            else:
                # Layout: previous / current / next, vertically centred
                _, cur_text = LYRICS[active]
                cur_lines = word_wrap(cur_text, font_big, INTERNAL_W - 8)
                line_h = font_big.get_height() + 1
                cur_block_h = len(cur_lines) * line_h

                # Anchor current lyric at vertical centre
                cur_y = (INTERNAL_H - cur_block_h) // 2

                # Previous lyric (dimmed, above)
                if active > 0:
                    prev_text = LYRICS[active - 1][1]
                    prev_lines = word_wrap(prev_text, font_small, INTERNAL_W - 8)
                    prev_h = len(prev_lines) * (font_small.get_height() + 1)
                    prev_y = cur_y - prev_h - 8
                    if prev_y >= 0:
                        draw_text_centered(canvas, font_small, prev_text, prev_y, TEXT_ECHO, INTERNAL_W - 8)

                # Current lyric (bright)
                draw_text_centered(canvas, font_big, cur_text, cur_y, TEXT_ACTIVE, INTERNAL_W - 8)

                # Next lyric (dimmed, below)
                if active < len(LYRICS) - 1:
                    next_text = LYRICS[active + 1][1]
                    next_y = cur_y + cur_block_h + 8
                    draw_text_centered(canvas, font_small, next_text, next_y, TEXT_DIM, INTERNAL_W - 8)

            # Progress bar
            draw_progress_bar(canvas, elapsed, total_duration, INTERNAL_H - 6)

        # Scale up with nearest-neighbour (keeps pixels sharp)
        scaled = pygame.transform.scale(canvas, (WINDOW_W, WINDOW_H))
        screen.blit(scaled, (0, 0))
        pygame.display.flip()
        clock.tick(30)

    # --- End screen ---
    end_start = time.time()
    while time.time() - end_start < 3.0:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                return
            if event.type == pygame.KEYDOWN:
                pygame.quit()
                return
        canvas.fill(BG)
        draw_text_centered(canvas, font_big, "END", INTERNAL_H // 2 - 5, ACCENT)
        scaled = pygame.transform.scale(canvas, (WINDOW_W, WINDOW_H))
        screen.blit(scaled, (0, 0))
        pygame.display.flip()
        clock.tick(30)

    pygame.quit()


if __name__ == "__main__":
    main()
