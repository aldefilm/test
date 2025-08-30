# /home/pi/aurion/aurion_ui.py
import os, json, glob, random, shutil, subprocess
import pygame

# ----- PATHS -----
AURION_ROOT = "/home/pi/aurion"
ASSETS      = os.path.join(AURION_ROOT, "assets")
FONT_PATH   = os.path.join(ASSETS, "fonts", "AurionFont.ttf")
SPLASH_MP4  = os.path.join(ASSETS, "splash.mp4")

# ----- DISPLAY HELPERS -----
def open_fullscreen_on(display_index="0"):
    """
    Open a fullscreen Pygame window on a specific display.
    Use "0" (left HDMI) or "1" (right HDMI).
    """
    os.environ.setdefault("SDL_VIDEODRIVER", "x11")  # use "kmsdrm" if you run no desktop
    os.environ["SDL_VIDEO_FULLSCREEN_DISPLAY"] = str(display_index)

    pygame.init()
    screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
    clock  = pygame.time.Clock()
    pygame.mouse.set_visible(False)
    return screen, clock

def load_font(size=48):
    try:
        return pygame.font.Font(FONT_PATH, size)
    except Exception:
        return pygame.font.SysFont(None, size)

# ----- VISUAL OVERLAYS -----
def make_scanlines(size):
    w, h = size
    surf = pygame.Surface((w, h), pygame.SRCALPHA)
    for y in range(0, h, 4):
        pygame.draw.line(surf, (0, 0, 0, 40), (0, y), (w, y))
    return surf

def make_tint(size, rgba=(0, 255, 200, 14)):
    surf = pygame.Surface(size, pygame.SRCALPHA)
    surf.fill(rgba)
    return surf

def make_noise_frames(size, frames=3, dots=600, alpha=22):
    w, h = size
    out = []
    for _ in range(frames):
        n = pygame.Surface((w, h), pygame.SRCALPHA)
        set_at = n.set_at
        for _ in range(dots):
            set_at((random.randrange(w), random.randrange(h)), (255, 255, 255, alpha))
        out.append(n)
    return out

def blit_glow_halo(surface, text_surface, center, radius=4, copies=24, alpha=40):
    """
    Halo glow with small offsets (no big rectangle bars).
    Draws many faint copies around the text perimeter.
    """
    cx, cy = center
    glow = text_surface.copy().convert_alpha()
    glow.set_alpha(alpha)
    for i in range(copies):
        angle = (i / copies) * 6.28318530718  # 2π
        ox = int(radius * 1.0 * pygame.math.Vector2(1, 0).rotate_rad(angle).x)
        oy = int(radius * 1.0 * pygame.math.Vector2(1, 0).rotate_rad(angle).y)
        surface.blit(glow, glow.get_rect(center=(cx + ox, cy + oy)), special_flags=pygame.BLEND_ADD)
    # main text on top (caller renders it)

# ----- FADE UTILS -----
def fade_from_black(screen, clock, ms=500):
    """Quick fade from black to scene for a smooth post-splash transition."""
    w, h = screen.get_size()
    cover = pygame.Surface((w, h))
    cover.fill((0, 0, 0))
    steps = max(1, int(ms / 33))  # ~30fps
    for i in range(steps, -1, -1):
        cover.set_alpha(int(255 * (i / steps)))
        screen.blit(cover, (0, 0))
        pygame.display.flip()
        clock.tick(30)

# ----- SPLASH (8s, no VLC UI/OSD) -----
def play_splash_8s():
    """
    Plays splash up to 8s using cvlc/omxplayer with no visible UI.
    Tip: For a seamless look, open your Pygame screen *first* (black),
    then call this so VLC draws on top and returns to your already-open window.
    """
    if not os.path.isfile(SPLASH_MP4):
        return

    if shutil.which("cvlc"):
        subprocess.run(
            [
                "cvlc",
                "--intf", "dummy",           # no VLC UI
                "--no-osd",
                "--no-video-title-show",
                "--video-on-top",            # keeps on top of your black Pygame screen
                "--fullscreen",
                "--start-time=0",
                "--stop-time=8",
                "--play-and-exit",
                SPLASH_MP4,
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
    elif shutil.which("omxplayer"):
        p = subprocess.Popen(
            ["omxplayer", "--no-osd", "--aspect-mode", "fill", SPLASH_MP4],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
        try:
            p.wait(timeout=8)
        except subprocess.TimeoutExpired:
            p.terminate()
            try: p.wait(timeout=2)
            except subprocess.TimeoutExpired: pass
    else:
        print("[aurion] No cvlc/omxplayer found; skipping splash.")

# ----- SD / ALBUM HELPERS -----
MOUNT_GUESS = ["/media/pi/*", "/media/*/*", "/mnt/*"]

def find_album_json():
    for pat in MOUNT_GUESS:
        for mount in glob.glob(pat):
            jp = os.path.join(mount, "album.json")
            if os.path.isfile(jp):
                return jp
    return None

def load_album(json_path):
    with open(json_path, "r", encoding="utf-8") as f:
        return json.load(f)

def fmt_time(seconds: int) -> str:
    m = seconds // 60
    s = seconds % 60
    return f"{int(m):02d}:{int(s):02d}"
