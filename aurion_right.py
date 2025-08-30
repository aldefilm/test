import os, time
import pygame
from queue import Empty
from aurion_ui import (
    open_fullscreen_on, load_font, make_scanlines, make_tint, make_noise_frames,
    fade_from_black, play_splash_embedded, play_splash_8s, load_album
)

SCREEN_INDEX = "1"  # Right HDMI
BLUE  = (150,200,255)
RED   = (220,40,40)
BLACK = (0,0,0)

def idle_until_queue(album_q, greeting="Commander"):
    """Splash → welcome/insert loop until we receive an album.json path on the queue."""
    screen, clock = open_fullscreen_on(SCREEN_INDEX)
    screen.fill(BLACK); pygame.display.flip()

    try:
        play_splash_embedded(screen, clock, stop_seconds=8)
    except Exception:
        play_splash_8s()

    fade_from_black(screen, clock, ms=300)

    sw, sh = screen.get_size()
    font = load_font(48)

    full_text = f"Welcome {greeting}"
    renders = [font.render(full_text[:i], True, BLUE) for i in range(len(full_text)+1)]
    frames_per_letter = 2
    blink_frames      = 15

    scan  = make_scanlines((sw, sh))
    tint  = make_tint((sw, sh))
    noise = make_noise_frames((sw, sh))

    frame = 0; letters = 0; blink = True; ni = 0
    finished_welcome = False

    while True:
        # Check for a message from master/left
        if album_q is not None:
            try:
                jp = album_q.get_nowait()
                pygame.quit()
                return jp
            except Empty:
                pass

        for e in pygame.event.get():
            if e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE:
                pygame.quit(); return None

        frame += 1
        if letters < len(full_text) and frame % frames_per_letter == 0:
            letters += 1
            if letters == len(full_text):
                finished_welcome = True
        if frame % blink_frames == 0:
            blink = not blink

        screen.fill(BLACK)
        t1 = renders[letters]
        screen.blit(t1, t1.get_rect(center=(sw // 2, sh // 2 - 60)))

        if finished_welcome and blink:
            t2 = font.render("Insert Cartridge", True, RED)
            screen.blit(t2, t2.get_rect(center=(sw // 2, sh // 2 + 40)))

        screen.blit(scan, (0,0))
        screen.blit(noise[ni], (0,0)); ni = (ni+1) % len(noise)
        screen.blit(tint, (0,0))
        pygame.display.flip()
        pygame.time.Clock().tick(30)

def run_cover_ui(json_path):
    """Display cover art scaled to fit (letterboxed)."""
    meta = load_album(json_path)
    base = os.path.dirname(json_path)
    cover_name = meta.get("cover", "cover.png")

    screen, clock = open_fullscreen_on(SCREEN_INDEX)
    sw, sh = screen.get_size()

    cover_path = os.path.join(base, cover_name)
    cover_img = None
    error_msg = None
    try:
        cover_img = pygame.image.load(cover_path).convert()
    except Exception:
        error_msg = f"Cover not found: {cover_name}"

    scan  = make_scanlines((sw, sh))
    tint  = make_tint((sw, sh))
    noise = make_noise_frames((sw, sh), dots=500, alpha=18)
    ni = 0

    running = True
    while running:
        for e in pygame.event.get():
            if e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE:
                running = False

        screen.fill(BLACK)

        if cover_img:
            iw, ih = cover_img.get_size()
            scale = min(sw/iw, sh/ih)
            tw, th = int(iw*scale), int(ih*scale)
            frame = pygame.transform.smoothscale(cover_img, (tw, th))
            screen.blit(frame, frame.get_rect(center=(sw//2, sh//2)))
        else:
            font = load_font(40)
            t = font.render(error_msg or "No cover image", True, BLUE)
            screen.blit(t, t.get_rect(center=(sw//2, sh//2)))

        screen.blit(scan, (0,0))
        screen.blit(noise[ni], (0,0)); ni = (ni+1) % len(noise)
        screen.blit(tint, (0,0))
        pygame.display.flip()
        clock.tick(30)

    pygame.quit()

# Worker used by the master
def run_right_worker(album_q, greeting="Commander"):
    jp = idle_until_queue(album_q, greeting=greeting)
    if jp:
        run_cover_ui(jp)

if __name__ == "__main__":
    # Standalone right screen (no master): falls back to idle forever
    from multiprocessing import Queue
    q = Queue()
    jp = idle_until_queue(q, greeting="Commander")
    if jp:
        run_cover_ui(jp)
