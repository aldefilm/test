# /home/pi/aurion/aurion_left.py
import os, time, json, hashlib
import pygame
from aurion_ui import (
    open_fullscreen_on, load_font, make_scanlines, make_tint, make_noise_frames,
    blit_glow, play_splash_8s, find_album_json, load_album, fmt_time
)

# Which HDMI for the LEFT/TEXT screen
SCREEN_INDEX = "0"

# Colors
BLUE  = (150,200,255)
RED   = (220,40,40)
WHITE = (230,230,230)
BLACK = (0,0,0)

# Bookmark file
BOOKMARKS_PATH = "/home/pi/aurion/config/bookmarks.json"

# ---------- bookmarks ----------
def _load_bookmarks():
    try:
        with open(BOOKMARKS_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def _save_bookmarks(data):
    os.makedirs(os.path.dirname(BOOKMARKS_PATH), exist_ok=True)
    with open(BOOKMARKS_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

def _album_key(meta, album_folder):
    # Prefer a stable id from album.json; else hash the folder path
    if "album_id" in meta:
        return meta["album_id"]
    return hashlib.sha1(album_folder.encode("utf-8")).hexdigest()[:16]

# ---------- idle (splash -> welcome) until SD detected ----------
def run_idle_until_sd(greeting="Commander"):
    # 1) Open Pygame first (black background), so the splash returns cleanly to it
    screen, clock = open_fullscreen_on(SCREEN_INDEX)
    screen.fill((0,0,0)); pygame.display.flip()

    # 2) Play hidden splash ON TOP, then fade into text
    play_splash_8s()
    fade_from_black(screen, clock, ms=500)

    sw, sh = screen.get_size()
    font = load_font(48)

    full_text = f"Welcome {greeting}"
    renders = [font.render(full_text[:i], True, BLUE) for i in range(len(full_text)+1)]
    frames_per_letter = 2
    blink_frames      = 15

    scan  = make_scanlines((sw, sh))
    tint  = make_tint((sw, sh))
    noise = make_noise_frames((sw, sh))

    frame = 0
    letters = 0
    blink = True
    ni = 0
    last_poll = 0.0
    finished_welcome = False

    running = True
    while running:
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

        # poll for SD ...
        # (your existing poll code here)

        # draw
        screen.fill((0,0,0))
        t1 = renders[letters]
        c1 = (sw // 2, sh // 2 - 60)
        # halo glow (no bars), then main text
        blit_glow_halo(screen, t1, c1, radius=4, copies=24, alpha=40)
        screen.blit(t1, t1.get_rect(center=c1))

        # Only show red AFTER welcome is fully typed
        if finished_welcome and blink:
            t2 = font.render("Insert Cartridge", True, RED)
            c2 = (sw // 2, sh // 2 + 40)
            blit_glow_halo(screen, t2, c2, radius=4, copies=24, alpha=40)
            screen.blit(t2, t2.get_rect(center=c2))

        screen.blit(scan, (0,0))
        screen.blit(noise[ni], (0,0)); ni = (ni+1) % len(noise)
        screen.blit(tint, (0,0))
        pygame.display.flip()
        clock.tick(30)


# ---------- build track list from titles + numbered files ----------
def pair_titles_with_files(base, main_titles, bonus_titles):
    files = sorted([f for f in os.listdir(base) if f.lower().endswith(".mp3")])
    tracks = []
    # main
    for i, title in enumerate(main_titles):
        fn = files[i] if i < len(files) else ""
        tracks.append({"title": title, "filename": fn})
    # bonus
    off = len(main_titles)
    for i, title in enumerate(bonus_titles):
        idx = off + i
        fn = files[idx] if idx < len(files) else ""
        tracks.append({"title": title, "filename": fn})
    return tracks, len(main_titles)

# ---------- album UI + audio ----------
def run_album_ui(json_path):
    data   = load_album(json_path)
    artist = data.get("artist","")
    album  = data.get("album","")
    base   = os.path.dirname(json_path)

    main_titles  = data.get("tracks", [])
    bonus_titles = data.get("bonus",  [])
    tracks, main_count = pair_titles_with_files(base, main_titles, bonus_titles)
    if not tracks:
        tracks = [{"title":"(No tracks)","filename":""}]
        main_count = 0

    # screen
    screen, clock = open_fullscreen_on(SCREEN_INDEX)
    sw, sh = screen.get_size()
    font_big   = load_font(44)
    font_small = load_font(36)
    scan = make_scanlines((sw, sh))
    tint = make_tint((sw, sh), (0,255,200,10))
    noise = make_noise_frames((sw, sh), dots=500, alpha=18)
    ni = 0

    # audio
    pygame.mixer.init(frequency=44100, channels=2)

    def play_track(i, start_sec=0):
        fn = tracks[i].get("filename","")
        if not fn:
            return False
        path = os.path.join(base, fn)
        try:
            pygame.mixer.music.load(path)
            if start_sec > 0:
                try:
                    pygame.mixer.music.play(start=start_sec)
                except Exception:
                    pygame.mixer.music.play()
            else:
                pygame.mixer.music.play()
            return True
        except Exception as e:
            print("[aurion] audio load error:", e)
            return False

    # bookmarks (resume)
    bmarks = _load_bookmarks()
    key    = _album_key(data, base)
    idx = 0
    resume_sec = 0
    if key in bmarks:
        idx = min(max(0, bmarks[key].get("track", 0)), len(tracks)-1)
        resume_sec = max(0, int(bmarks[key].get("pos", 0)))
        print(f"[aurion] Resuming {key} at track {idx+1}, {resume_sec}s")

    play_track(idx, resume_sec)
    paused = False
    album_ended = False
    start_wall = time.time() - resume_sec  # wall-clock fallback for elapsed

    def current_elapsed():
        ms = pygame.mixer.music.get_pos()
        return int(ms/1000) if ms >= 0 else int(time.time() - start_wall)

    running = True
    while running:
        for e in pygame.event.get():
            if e.type == pygame.KEYDOWN:
                if e.key == pygame.K_ESCAPE:
                    running = False
                elif e.key == pygame.K_SPACE:
                    # Play/Pause, or kick into bonus after main end
                    if album_ended and paused and len(tracks) > main_count:
                        idx = main_count
                        play_track(idx, 0)
                        start_wall = time.time()
                        paused = False
                        album_ended = False
                    else:
                        if paused:
                            pygame.mixer.music.unpause()
                            paused = False
                            start_wall = time.time() - current_elapsed()
                        else:
                            pygame.mixer.music.pause()
                            paused = True
                elif e.key == pygame.K_s:
                    # STOP = save bookmark and stop
                    pos = current_elapsed()
                    bmarks[key] = {"track": idx, "pos": pos}
                    _save_bookmarks(bmarks)
                    pygame.mixer.music.stop()
                    paused = True
                elif e.key == pygame.K_RIGHT and idx < len(tracks)-1:
                    idx += 1
                    play_track(idx, 0); start_wall = time.time(); album_ended = False
                elif e.key == pygame.K_LEFT and idx > 0:
                    idx -= 1
                    play_track(idx, 0); start_wall = time.time(); album_ended = False

        # Track finished naturally?
        if not paused and not pygame.mixer.music.get_busy():
            if idx+1 < main_count:
                idx += 1; play_track(idx, 0); start_wall = time.time()
            elif idx+1 == main_count:
                # finished last MAIN track → stop & wait for PLAY to enter bonus
                if not album_ended:
                    album_ended = True
                    pygame.mixer.music.stop()
                    paused = True
            else:
                # in bonus: auto-advance
                if idx < len(tracks)-1:
                    idx += 1; play_track(idx, 0); start_wall = time.time()

        # draw UI
        elapsed = current_elapsed()
        title = tracks[idx].get("title", "(untitled)")
        line1 = f"{idx+1}. {title}  {fmt_time(elapsed)}"

        screen.fill(BLACK)
        t1 = font_big.render(line1, True, BLUE)
        c1 = (sw//2, sh//2 - 60)
        blit_glow(screen, t1, c1, layers=((1.3,50),(1.6,25)))
        screen.blit(t1, t1.get_rect(center=c1))

        t2 = font_small.render(album,  True, WHITE)
        screen.blit(t2, t2.get_rect(center=(sw//2, sh//2)))

        t3 = font_small.render(artist, True, WHITE)
        screen.blit(t3, t3.get_rect(center=(sw//2, sh//2 + 48)))

        if album_ended and paused and len(tracks) > main_count:
            hint = font_small.render("Main complete — press PLAY for bonus tracks", True, RED)
            screen.blit(hint, hint.get_rect(center=(sw//2, sh//2 + 110)))

        screen.blit(scan, (0,0))
        screen.blit(noise[ni], (0,0)); ni = (ni+1) % len(noise)
        screen.blit(tint, (0,0))
        pygame.display.flip()
        clock.tick(30)

    # save bookmark on exit
    pos = current_elapsed()
    bmarks[key] = {"track": idx, "pos": pos}
    _save_bookmarks(bmarks)
    pygame.mixer.music.stop()
    pygame.quit()

# ---------- main ----------
if __name__ == "__main__":
    jp = run_idle_until_sd(greeting="Commander")
    if jp:
        run_album_ui(jp)
