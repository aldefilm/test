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
    Use display_index "0" (left HDMI) or "1" (right HDMI).
    """
    # Choose a sensible default video driver.
    # If you boot to console only, change "x11" -> "kmsdrm".
    os.environ.setdefault("SDL_VIDEODRIVER", "x11")

    # Always set this so KeyError can't occur later.
    os.environ["SDL_VIDEO_FULLSCREEN_DISPLAY"] = str(display_index)

    pygame.init()
    screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
    clock  = pygame.time.Clock()
    return screen, clock

def load_font(size=48):
    try:
        return pygame.font.Font(FONT_PATH, size)
    except Exception:
        return pygame.font.SysFont(None, size)

# ----- OVERLAYS / EFFECTS -----
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

def blit_glow(surface, text_surface, center, layers=((1.35, 60), (1.7, 30))):
    cx, cy = center
    for scale, alpha in layers:
        g = pygame.transform.smoothscale(
            text_surface,
            (int(text_surface.get_width() * scale), int(text_surface.get_height() * scale)),
        )
        g.set_alpha(alpha)
        surface.blit(g, g.get_rect(center=(cx, cy)), special_flags=pygame.BLEND_ADD)

# ----- SPLASH (8s, no VLC UI/OSD) -----
def play_splash_8s():
    """
    Play the splash video up to 8 seconds without showing a VLC window/OSD.
    Returns after playback so the program can continue.
    """
    if not os.path.isfile(SPLASH_MP4):
        return

    if shutil.which("cvlc"):
        # Use command-line VLC with dummy interface; hide OSD/title; silence output.
        subprocess.run(
            [
                "cvlc",
                "--intf", "dummy",
                "--no-osd",
                "--no-video-title-show",
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
        # Fallback to omxplayer
        p = subprocess.Popen(
            ["omxplayer", "--no-osd", "--aspect-mode", "fill", SPLASH_MP4],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        try:
            p.wait(timeout=8)
        except subprocess.TimeoutExpired:
            p.terminate()
            try:
                p.wait(timeout=2)
            except subprocess.TimeoutExpired:
                pass
    else:
        print("[aurion] No cvlc/omxplayer found; skipping splash.")

# ----- SD / ALBUM HELPERS -----
MOUNT_GUESS = ["/media/pi/*", "/media/*/*", "/mnt/*"]

def find_album_json():
    """Look for album.json on mounted media."""
    for pat in MOUNT_GUESS:
        for mount in glob.glob(pat):
            jp = os.path.join(mount, "album.json")
            if os.path.isfile(jp):
                return jp
    return None

def load_album(json_path):
    """Load album.json into a dict."""
    with open(json_path, "r", encoding="utf-8") as f:
        return json.load(f)

def fmt_time(seconds: int) -> str:
    m = seconds // 60
    s = seconds % 60
    return f"{int(m):02d}:{int(s):02d}"
