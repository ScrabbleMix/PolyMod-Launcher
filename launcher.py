
import io
import json
import math
import os
import queue
import re
import shutil
import subprocess
import sys
import tempfile
import time
import threading
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
import zipfile

def folder_dialog():
    import tkinter as tk
    from tkinter import filedialog
    root = tk.Tk()
    root.withdraw()
    chosen = filedialog.askdirectory(title="Choose the game folder") or ""
    if sys.stdout is not None:                       
        sys.stdout.write(chosen)


if "--pick-folder" in sys.argv:                    
    folder_dialog()
    sys.exit(0)

import pygame

#  opti 
GB_GAME_ID = 8694                                  
VERSION_LINES = ("Friday Night Funkin V-Slice", "PolyMod Launcher 0.2.3")
SETTINGS_FILE = os.path.join(os.path.expanduser("~"), ".fnf_launcher.json")
DEFAULT_CFG = {"game_dir": "", "bg_music": True, "sfx": True, "accent": "FDE871",
               "close_on_play": False, "skip_existing": True}
ACCENTS = [("FDE871", "Default"), ("31B0D1", "Cyan"), ("F9393F", "Red"),
           ("C24B99", "Purple"), ("12FA05", "Green")]
TOGGLES = [("BG Music", "bg_music", 300), ("Sounds in launcher", "sfx", 352),
           ("Close launcher on game start", "close_on_play", 600),
           ("Skip installed mods", "skip_existing", 652)]

W, H = 1280, 780                                  
PER_PAGE = 15                                     

ASSETS = os.path.join(getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__))), "assets")
BLACK, WHITE, GREY = (0, 0, 0), (255, 255, 255), (150, 150, 150)
GREEN, RED = (140, 255, 140), (255, 130, 130)
UA = {"User-Agent": "FNF-Launcher/1.0"}
MODS_DIR, OFF_DIR, META_FILE = "mods", "mods_disabled", "fnf_mod.json"
COVER_W, COVER_H = 96, 60
GRID_X, GRID_Y, CARD_W, CARD_H, GAP_X, GAP_Y = 445, 150, 252, 76, 12, 6


MENU = {"game": pygame.Rect(0, 0, 400, 130), "mods": pygame.Rect(0, 130, 400, 130),
        "opts": pygame.Rect(0, 260, 400, 130)}
MODS_BTN = pygame.Rect(518, 601, 230, 100)
LAUNCH_BTN = pygame.Rect(750, 586, 400, 130)
PANEL = (430, 40, 820, 535)
SEARCH_RECT = pygame.Rect(440, 92, 800, 44)
CAT_PREV, CAT_NEXT = pygame.Rect(440, 600, 120, 60), pygame.Rect(575, 600, 120, 60)
CAT_PICK, CAT_ALL = pygame.Rect(710, 600, 300, 60), pygame.Rect(1020, 600, 220, 60)
MAN_BACK, MAN_PREV = pygame.Rect(440, 600, 130, 60), pygame.Rect(585, 600, 110, 60)
MAN_NEXT, MAN_TOGGLE = pygame.Rect(705, 600, 110, 60), pygame.Rect(825, 600, 200, 60)
MAN_DELETE = pygame.Rect(1035, 600, 200, 60)
BROWSE_RECT = pygame.Rect(440, 110, 460, 50)
COLOR_RECT = pygame.Rect(440, 494, 760, 46)



def hex_rgb(h):
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def tint(img, color):                            
    img = img.copy()
    img.fill(color, special_flags=pygame.BLEND_RGB_MULT)
    return img


def fit_cover(img, w, h):
    iw, ih = img.get_size()
    s = max(w / iw, h / ih)
    big = pygame.transform.smoothscale(img, (max(1, round(iw * s)), max(1, round(ih * s))))
    area = pygame.Rect(0, 0, w, h)
    area.center = big.get_rect().center
    out = pygame.Surface((w, h))
    out.blit(big, (0, 0), area)
    return out


def pick_folder():
   
    if getattr(sys, "frozen", False):
        cmd = [sys.executable, "--pick-folder"]         
    else:
        cmd = [sys.executable, os.path.abspath(__file__), "--pick-folder"]
    out = subprocess.run(cmd, capture_output=True, text=True)
    return out.stdout.strip()


def load_cfg():
    cfg = dict(DEFAULT_CFG)
    try:
        with open(SETTINGS_FILE, encoding="utf-8") as f:
            cfg.update(json.load(f))
    except (OSError, ValueError):
        pass
    return cfg


def get_json(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def get_bytes(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=20) as r:
        return r.read(3_000_000)


def download(url, path):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=120) as r, open(path, "wb") as f:
        while chunk := r.read(65536):
            f.write(chunk)


def safe(name):
    return re.sub(r'[\\/:*?"<>|]+', "_", name).strip() or "mod"


def find_game(folder):
    if not folder or not os.path.isdir(folder):
        return None
    for root, dirs, files in os.walk(folder):
        for name in files:
            low = name.lower()
            if low.startswith("funkin") and (low.endswith(".exe") or low == "funkin"):
                return os.path.join(root, name)
        for name in dirs:
            if name.lower().startswith("funkin") and name.lower().endswith(".app"):
                return os.path.join(root, name)
    return None


def fetch_mod_page(page):
    url = f"https://gamebanana.com/apiv11/Game/{GB_GAME_ID}/Subfeed?_nPage={page}&_sSort=default"
    records = get_json(url).get("_aRecords", [])
    return [r for r in records if r.get("_sModelName") == "Mod"]


INDEX_FILE = os.path.join(os.path.expanduser("~"), ".fnf_mods_index.json")
INDEX_LOCK = threading.Lock()
MAX_INDEX_PAGES = 1000                            
COMMON_WORDS = {"fnf", "friday", "night", "funkin"}   


def subfeed_url(page, perpage=None):
    url = f"https://gamebanana.com/apiv11/Game/{GB_GAME_ID}/Subfeed?_nPage={page}&_sSort=default&_csvModelInclusions=Mod"
    return url + (f"&_nPerpage={perpage}" if perpage else "")


def words(text):
    return re.sub(r"[\W_]+", " ", (text or "").lower()).split()


def compact(text):
    return re.sub(r"[\W_]+", "", (text or "").lower())


def name_matches(query, name):
    q_words = [w for w in words(query) if w not in COMMON_WORDS] or words(query)
    n_words = words(name)
    if all(any(w.startswith(q) for w in n_words) for q in q_words):
        return True
    return compact("".join(q_words)) in compact(name)


def search_remote(query):
    q_words = [w for w in words(query) if w not in COMMON_WORDS] or words(query)
    word = max(q_words, key=len, default="")
    hits = []
    if not word:
        return hits
    for page in (1, 2, 3):
        url = (f"https://gamebanana.com/apiv11/Mod/Index?_aFilters[Generic_Game]={GB_GAME_ID}"
               f"&_aFilters[Generic_Name]={urllib.parse.quote(word)}&_nPage={page}&_nPerpage=50")
        records = get_json(url).get("_aRecords", [])
        if not records:
            break
        hits += [{"_idRow": r["_idRow"], "_sName": r.get("_sName") or "", "cover": cover_url(r)}
                 for r in records if r.get("_idRow") and name_matches(query, r.get("_sName"))]
    return hits


def list_url(page, perpage):
    if perpage:
        return (f"https://gamebanana.com/apiv11/Mod/Index?_aFilters[Generic_Game]={GB_GAME_ID}"
                f"&_nPage={page}&_nPerpage={perpage}")
    return subfeed_url(page)


def pick_perpage():
    for perpage in (50, 20):
        try:
            if get_json(list_url(1, perpage)).get("_aRecords"):
                return perpage
        except urllib.error.HTTPError:
            pass
    return None


def fetch_page(page, perpage):
    for attempt in range(4):
        try:
            return get_json(list_url(page, perpage)).get("_aRecords", [])
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt < 3:
                time.sleep(3 * (attempt + 1))
                continue
            if e.code in (400, 404):        
                return []
            raise


def read_index():
    try:
        with open(INDEX_FILE, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def save_index(data):
    with open(INDEX_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)


def build_index(progress):
    old = read_index()
    if old and "next_page" in old and not old.get("complete"):
        mods, page, perpage = old["mods"], old["next_page"], old.get("perpage")
    else:
        mods, page, perpage = [], 1, pick_perpage()
    seen = {m["id"] for m in mods}
    with ThreadPoolExecutor(max_workers=6) as pool:
        while page <= MAX_INDEX_PAGES:
            batch = list(range(page, page + 24))
            complete, added = False, 0
            for records in pool.map(lambda p: fetch_page(p, perpage), batch):
                if not records:
                    complete = True
                    break
                for r in records:
                    if r.get("_sModelName", "Mod") == "Mod" and r.get("_idRow") and r["_idRow"] not in seen:
                        seen.add(r["_idRow"])
                        mods.append({"id": r["_idRow"], "name": r.get("_sName") or "", "cover": cover_url(r)})
                        added += 1
            page += len(batch)
            complete = complete or page > MAX_INDEX_PAGES or added == 0
            save_index({"time": time.time(), "complete": complete, "next_page": page,
                        "perpage": perpage, "mods": mods})
            progress(f"Building the mod list: {len(mods)} mods so far")
            if complete:
                break
    return mods


def load_index(progress):
    data = read_index()
    if data and data.get("complete", "next_page" not in data) and time.time() - data["time"] < 7 * 24 * 3600:
        return data["mods"]
    return build_index(progress)


def search_mods(query, progress):
    if not compact(query):
        return [], ""
    try:
        hits = search_remote(query)
        if hits:
            return hits, "GameBanana search"
    except urllib.error.HTTPError:
        pass                                      
    with INDEX_LOCK:
        mods = load_index(progress)
    hits = [{"_idRow": m["id"], "_sName": m["name"], "cover": m.get("cover")}
            for m in mods if name_matches(query, m["name"])]
    return hits, f"list of {len(mods)}"


def mod_name(mod_id):
    for url in (f"https://gamebanana.com/apiv11/Mod/{mod_id}/ProfilePage",
                f"https://gamebanana.com/apiv11/Mod/{mod_id}?_csvProperties=_sName"):
        try:
            name = get_json(url).get("_sName")
            if name:
                return name
        except Exception:
            pass
    return None


def mod_files(mod_id):
    error = None
    for url in (f"https://gamebanana.com/apiv11/Mod/{mod_id}?_csvProperties=_aFiles",
                f"https://gamebanana.com/apiv11/Mod/{mod_id}/ProfilePage"):
        try:
            return get_json(url).get("_aFiles") or []
        except Exception as e:
            error = e
    raise error


def cover_url(rec):
    if rec.get("cover"):
        return rec["cover"]
    try:
        img = rec["_aPreviewMedia"]["_aImages"][0]
    except (KeyError, IndexError, TypeError):
        return None
    file = img.get("_sFile220") or img.get("_sFile")
    base = img.get("_sBaseUrl")
    return f"{base}/{file}" if base and file else None


def fit_inside(img, w, h):
    iw, ih = img.get_size()
    s = min(w / iw, h / ih)
    return pygame.transform.smoothscale(img, (max(1, round(iw * s)), max(1, round(ih * s))))


def load_icon(path):
    if not os.path.isfile(path):
        return False
    try:
        return fit_inside(pygame.image.load(path).convert_alpha(), COVER_W, COVER_H)
    except Exception:
        return False


def make_app_icon(path, size=256):
    img = pygame.image.load(path)                       
    box = img.get_bounding_rect()                     
    content = img.subsurface(box).copy()
    s = min(size / box.w, size / box.h)
    scaled = pygame.transform.smoothscale(content, (max(1, round(box.w * s)), max(1, round(box.h * s))))
    icon = pygame.Surface((size, size), pygame.SRCALPHA)
    icon.blit(scaled, scaled.get_rect(center=(size // 2, size // 2)))
    return icon


def read_meta(folder):
    try:
        with open(os.path.join(folder, META_FILE), encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def scan_mods(game):
    items = []
    if not game or not os.path.isdir(game):
        return items
    for folder, off in ((MODS_DIR, False), (OFF_DIR, True)):
        base = os.path.join(game, folder)
        if not os.path.isdir(base):
            continue
        for name in sorted(os.listdir(base), key=str.lower):
            path = os.path.join(base, name)
            if os.path.isdir(path):
                meta = read_meta(path)
                items.append({"path": path, "folder": name, "off": off,
                              "name": meta.get("name") or name, "cover": meta.get("cover")})
    return items


def set_enabled(game, item, enable):
    base = os.path.join(game, MODS_DIR if enable else OFF_DIR)
    os.makedirs(base, exist_ok=True)
    dest = os.path.join(base, item["folder"])
    if os.path.exists(dest):
        raise FileExistsError(f"Folder already exists: {item['folder']}")
    shutil.move(item["path"], dest)


def mod_cover(mod_id):
    failed = False
    for url in (f"https://gamebanana.com/apiv11/Mod/{mod_id}?_csvProperties=_aPreviewMedia",
                f"https://gamebanana.com/apiv11/Mod/{mod_id}/ProfilePage"):
        for attempt in range(3):
            try:
                cover = cover_url(get_json(url))
            except urllib.error.HTTPError as e:
                if e.code == 429 and attempt < 2:    
                    time.sleep(2 * (attempt + 1))
                    continue
                failed = True
                break
            except Exception:
                failed = True
                break
            if cover:
                return cover
            break                                
    return None if failed else False


def install_mod(mod, mods_dir, skip_existing, say):
    files = mod_files(mod["_idRow"])
    zips = [f for f in files if (f.get("_sFile") or "").lower().endswith(".zip")]
    if not zips:
        say(f"No zip archive: {mod['_sName']}")
        return
    tmp = os.path.join(tempfile.gettempdir(), safe(zips[0]["_sFile"]))
    download(zips[0]["_sDownloadUrl"], tmp)
    with zipfile.ZipFile(tmp) as z:
        names = z.namelist()
        tops = {n.split("/")[0] for n in names}
        single = len(tops) == 1 and all("/" in n for n in names)   
        target = tops.pop() if single else safe(mod["_sName"])
        folder = os.path.join(mods_dir, target)
        off_folder = os.path.join(os.path.dirname(mods_dir), OFF_DIR, target)
        if skip_existing and (os.path.exists(folder) or os.path.exists(off_folder)):
            say(f"Already installed: {mod['_sName']}")
        else:
            z.extractall(mods_dir if single else folder)
            with open(os.path.join(folder, META_FILE), "w", encoding="utf-8") as f:
                json.dump({"id": mod["_idRow"], "name": mod["_sName"], "cover": cover_url(mod)},
                          f, ensure_ascii=False)
            say(f"Installed: {mod['_sName']}")
    os.remove(tmp)


# ===== ОКНО =====
class App:
    def __init__(self):
        pygame.init()
        logo = os.path.join(ASSETS, "LauncherLogo.png")
        if os.path.isfile(logo):                       
            try:
                pygame.display.set_icon(make_app_icon(logo))
            except Exception:
                pass
        self.screen = pygame.display.set_mode((W, H), pygame.RESIZABLE | pygame.SCALED)   
        pygame.display.set_caption("PolyMod Launcher (FNF Launcher)")
        pygame.key.start_text_input()
        self.cfg = load_cfg()
        self.jobs = queue.Queue()                  
        self.tab, self.status, self.running = "game", "", True
        self.fullscreen = False                    
        self.games_running = 0                     
        self.exe = find_game(self.cfg["game_dir"])
        self.query, self.active_query, self.editing = "", "", False
        self.hits, self.page, self.mods, self.selected = [], 1, [], {}
        self.man_items, self.man_sel, self.man_page, self.delete_armed = [], set(), 0, False
        self.covers, self.loading = {}, set()
        self.cover_known, self.cover_asked = {}, set()   
        self.cover_slots = threading.Semaphore(4)       
        self.load_assets()
        self.apply_music()
        self.load_page()


    def load_assets(self):
        def pic(name):
            return pygame.image.load(os.path.join(ASSETS, name)).convert_alpha()

        def font(size):
            return pygame.font.Font(os.path.join(ASSETS, "FunkinOptions.otf"), size)

        self.raw_menu = {"game": (pic("GameButton.png"), pic("GameButtonSelected.png")),
                         "mods": (pic("ModsButton.png"), pic("ModsButtonSelected.png")),
                         "opts": (pic("OptionsButton.png"), pic("OptionsButtonSelected.png"))}
        self.raw_launch = pic("ButtonLaunch.png")
        self.mods_img = pic("ButtonMods.png")
        logo = pic("FNF_logo.png")
        self.logo = pygame.transform.smoothscale(logo, (690, round(690 * logo.get_height() / logo.get_width())))
        raw = pygame.image.load(os.path.join(ASSETS, "menuDesat.png")).convert()
        bw = round(raw.get_width() * H / raw.get_height())
        base = pygame.transform.smoothscale(raw, (bw, H))
        base = base.subsurface(pygame.Rect((bw - W) // 2, 0, W, H)).copy()
        avg = sum(pygame.transform.average_color(base, pygame.Rect(0, 0, 60, 60))[:3]) // 3
        base.fill((255 - avg,) * 3, special_flags=pygame.BLEND_RGB_ADD)  
        self.bg_base = base
        self.f_title, self.f_head = font(70), font(56)
        self.f_body, self.f_small, self.f_tiny = font(38), font(22), font(16)
        self.sfx = {}
        if pygame.mixer.get_init():
            for key, name in (("select", "CS_select.ogg"), ("confirm", "CS_confirm.ogg")):
                try:
                    self.sfx[key] = pygame.mixer.Sound(os.path.join(ASSETS, name))
                except pygame.error:
                    pass
        self.build_tints()

    def build_tints(self):                        
        self.accent = hex_rgb(self.cfg["accent"])
        self.menu = {k: (n, tint(s, self.accent)) for k, (n, s) in self.raw_menu.items()}
        self.launch_img = tint(self.raw_launch, self.accent)
        img = tint(self.bg_base, self.accent)      
        shade = pygame.Surface((W - 400, H), pygame.SRCALPHA)
        shade.fill((0, 0, 0, 77))
        img.blit(shade, (400, 0))
        dark = pygame.Surface((400, H - 390), pygame.SRCALPHA)
        dark.fill((0, 0, 0, 217))
        img.blit(dark, (0, 390))
        self.bg = img

    def apply_music(self):
        if not pygame.mixer.get_init():
            return
        if self.cfg["bg_music"] and self.games_running == 0:      
            try:
                pygame.mixer.music.load(os.path.join(ASSETS, "BGMusic.mp3"))
                pygame.mixer.music.set_volume(0.5)
                pygame.mixer.music.play(-1)
            except pygame.error:
                pass
        else:
            pygame.mixer.music.stop()

    def play(self, key):
        if self.cfg["sfx"] and key in self.sfx:
            self.sfx[key].play()


    def toggle_fullscreen(self):
        self.fullscreen = not self.fullscreen
        try:
            ok = pygame.display.toggle_fullscreen()
        except pygame.error:
            ok = False
        if not ok:                                 
            flags = pygame.SCALED | (pygame.FULLSCREEN if self.fullscreen else pygame.RESIZABLE)
            pygame.display.set_mode((W, H), flags)
        self.screen = pygame.display.get_surface()
        pygame.key.start_text_input()             

    def on_event(self, e):
        if e.type == pygame.QUIT:
            self.running = False
        elif e.type == pygame.KEYDOWN and e.key == pygame.K_F11:
            self.toggle_fullscreen()
        elif e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE and self.fullscreen and not self.editing:
            self.toggle_fullscreen()
        elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            self.on_click(e.pos)
        elif e.type == pygame.TEXTINPUT and self.editing:
            self.query += e.text
        elif e.type == pygame.KEYDOWN and self.editing:
            if e.key == pygame.K_BACKSPACE:
                self.query = self.query[:-1]
            elif e.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                self.editing = False
                self.start_search()
            elif e.key == pygame.K_ESCAPE:
                self.editing = False

    def on_click(self, pos):
        if self.tab == "mods" and SEARCH_RECT.collidepoint(pos):
            self.editing = True
            return
        self.editing = False
        for name, rect in MENU.items():
            if rect.collidepoint(pos):
                self.play("select")
                self.tab = name
                return
        if self.tab == "game":
            if MODS_BTN.collidepoint(pos):
                self.play("select")
                self.open_manage()
            elif LAUNCH_BTN.collidepoint(pos):
                self.play("confirm")
                self.launch()
        elif self.tab == "mods":
            self.mods_click(pos)
        elif self.tab == "manage":
            self.manage_click(pos)
        else:
            self.opts_click(pos)

    def card_at(self, pos):
        for i in range(PER_PAGE):
            x = GRID_X + (i % 3) * (CARD_W + GAP_X)
            y = GRID_Y + (i // 3) * (CARD_H + GAP_Y)
            if pygame.Rect(x, y, CARD_W, CARD_H).collidepoint(pos):
                return i
        return None

    def mods_click(self, pos):
        i = self.card_at(pos)
        if i is not None and i < len(self.mods):
            rec = self.mods[i]
            if rec.get("_idRow") in self.selected:
                del self.selected[rec["_idRow"]]
            else:
                self.selected[rec["_idRow"]] = rec
            self.play("select")
        elif CAT_PREV.collidepoint(pos):
            self.change_page(-1)
        elif CAT_NEXT.collidepoint(pos):
            self.change_page(1)
        elif CAT_PICK.collidepoint(pos):
            self.download(list(self.selected.values()))
        elif CAT_ALL.collidepoint(pos):
            self.download(list(self.mods))

    def manage_click(self, pos):
        if not MAN_DELETE.collidepoint(pos):
            self.delete_armed = False
        i = self.card_at(pos)
        start = self.man_page * PER_PAGE
        if i is not None and start + i < len(self.man_items):
            self.man_sel ^= {self.man_items[start + i]["path"]}
        elif MAN_BACK.collidepoint(pos):
            self.tab = "game"
        elif MAN_PREV.collidepoint(pos) and self.man_page > 0:
            self.man_page -= 1
        elif MAN_NEXT.collidepoint(pos) and (self.man_page + 1) * PER_PAGE < len(self.man_items):
            self.man_page += 1
        elif MAN_TOGGLE.collidepoint(pos):
            self.toggle_selected()
        elif MAN_DELETE.collidepoint(pos):
            self.delete_selected()

    def opts_click(self, pos):
        if BROWSE_RECT.collidepoint(pos):
            self.play("select")
            self.browse()
        elif COLOR_RECT.collidepoint(pos):
            self.play("select")
            self.cycle_accent()
        else:
            for _, key, y in TOGGLES:
                if pygame.Rect(440, y - 4, 760, 46).collidepoint(pos):
                    self.play("select")
                    self.toggle(key)
                    return


    def toggle(self, key):
        self.cfg[key] = not self.cfg[key]
        self.save()
        if key == "bg_music":
            self.apply_music()

    def cycle_accent(self):
        codes = [c for c, _ in ACCENTS]
        i = codes.index(self.cfg["accent"]) if self.cfg["accent"] in codes else 0
        self.cfg["accent"] = codes[(i + 1) % len(codes)]
        self.save()
        self.build_tints()

    def browse(self):
        def job():
            path = pick_folder()
            self.jobs.put(lambda: self.set_game_dir(path))

        self.set_status("Choose the folder in the window...")
        threading.Thread(target=job, daemon=True).start()

    def set_game_dir(self, path):
        if path:
            self.cfg["game_dir"] = path
            self.save()
            self.exe = find_game(path)
            self.set_status("Game found" if self.exe else "No game file found in this folder")

    def save(self):
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(self.cfg, f, ensure_ascii=False, indent=2)

    def set_status(self, msg):
        self.status = msg


    def start_search(self):
        self.active_query = self.query.strip()
        self.page, self.selected = 1, {}
        self.hits, self.mods = [], []
        if not self.active_query:               
            return self.load_page()
        q = self.active_query
        by_id = re.search(r"/mods/(\d+)", q) or re.fullmatch(r"(\d{5,})", q)
        if by_id:                                
            return self.open_mod(int(by_id.group(1)), q)
        self.set_status(f"Searching for: {q}")

        def job():
            try:
                hits, source = search_mods(q, lambda msg: self.jobs.put(lambda: self.set_status(msg)))
                self.jobs.put(lambda: self.show_hits(q, hits, f"Found {len(hits)} mods ({source})"))
            except Exception as e:
                msg = f"No connection to GameBanana: {e}"
                self.jobs.put(lambda: self.set_status(msg))

        threading.Thread(target=job, daemon=True).start()

    def open_mod(self, mod_id, query):
        self.set_status(f"Loading mod {mod_id}...")

        def job():
            name = mod_name(mod_id)
            rec = {"_idRow": mod_id, "_sName": name or f"Mod {mod_id}"}
            note = "Mod found, press Download selected" if name else "Mod added (name unknown), press Download selected"
            self.jobs.put(lambda: self.show_hits(query, [rec], note))

        threading.Thread(target=job, daemon=True).start()

    def show_hits(self, query, hits, note):
        if query == self.active_query:           
            self.hits = hits
            self.page = 1
            self.show_hit_page()
            self.set_status(note)

    def show_hit_page(self):
        self.mods = self.hits[(self.page - 1) * PER_PAGE:self.page * PER_PAGE]
        self.request_covers(self.mods)

    def request_covers(self, items):
        for it in items:
            mid = it.get("_idRow")
            if not mid or it.get("cover"):
                continue
            if mid in self.cover_known:
                it["cover"] = self.cover_known[mid]
            elif mid not in self.cover_asked:
                self.cover_asked.add(mid)
                threading.Thread(target=self.cover_job, args=(mid,), daemon=True).start()

    def cover_job(self, mid):
        with self.cover_slots:                      
            url = mod_cover(mid)
        self.jobs.put(lambda: self.cover_found(mid, url))

    def cover_found(self, mid, url):
        if url is None:                              
            self.cover_asked.discard(mid)
            return
        if not url:                             
            return
        self.cover_known[mid] = url
        for it in self.hits:                       
            if it.get("_idRow") == mid:
                it["cover"] = url

    def load_page(self):
        page = self.page
        self.set_status(f"Loading page {page}...")

        def job():
            try:
                mods = fetch_mod_page(page)
                self.jobs.put(lambda: self.show_mods(page, mods))
            except Exception as e:
                msg = f"No connection to GameBanana: {e}"
                self.jobs.put(lambda: self.set_status(msg))

        threading.Thread(target=job, daemon=True).start()

    def show_mods(self, page, mods):
        if page == self.page and not self.active_query:
            self.mods = mods
            self.set_status(f"Page {page}: {len(mods)} mods")

    def change_page(self, step):
        new = self.page + step
        if new < 1 or (self.active_query and (new - 1) * PER_PAGE >= len(self.hits)):
            return
        self.page = new
        if self.active_query:
            self.show_hit_page()
        else:
            self.load_page()

    def download(self, mods):
        folder = self.cfg["game_dir"]
        if not os.path.isdir(folder):
            return self.set_status("Choose the game folder in OPTIONS first")
        if not mods:
            return self.set_status("Nothing selected")
        self.play("confirm")
        mods_dir = os.path.join(folder, MODS_DIR)
        skip = self.cfg["skip_existing"]

        def say(msg):                          
            self.jobs.put(lambda: self.set_status(msg))

        def job():
            os.makedirs(mods_dir, exist_ok=True)
            for m in mods:
                try:
                    install_mod(m, mods_dir, skip, say)
                except Exception as e:
                    say(f"Error ({m.get('_sName', '?')}): {e}")
            say("Done. Mods are in the game's mods folder")

        self.set_status(f"Downloading {len(mods)} mod(s)...")
        threading.Thread(target=job, daemon=True).start()

    def open_manage(self):
        if not os.path.isdir(self.cfg["game_dir"]):
            return self.set_status("Choose the game folder in OPTIONS first")
        self.tab, self.man_page, self.man_sel, self.delete_armed = "manage", 0, set(), False
        self.refresh_manage()
        self.set_status(f"{len(self.man_items)} mods installed")

    def refresh_manage(self):
        self.man_items = scan_mods(self.cfg["game_dir"])
        self.man_page = min(self.man_page, max(0, (len(self.man_items) - 1) // PER_PAGE))

    def toggle_selected(self):
        if not self.man_sel:
            return self.set_status("Nothing selected")
        done, errors = 0, 0
        for it in self.man_items:
            if it["path"] in self.man_sel:
                try:
                    set_enabled(self.cfg["game_dir"], it, enable=it["off"])
                    done += 1
                except OSError:
                    errors += 1
        self.man_sel = set()
        self.refresh_manage()
        self.set_status(f"Switched {done} mod(s)" + (f", errors: {errors}" if errors else ""))

    def delete_selected(self):
        if not self.man_sel:
            return self.set_status("Nothing selected")
        if not self.delete_armed:
            self.delete_armed = True
            return self.set_status(f"Press Confirm delete to remove {len(self.man_sel)} mod(s)")
        self.delete_armed = False
        done = 0
        for it in self.man_items:
            if it["path"] in self.man_sel:
                try:
                    shutil.rmtree(it["path"])
                    done += 1
                except OSError:
                    pass
        self.man_sel = set()
        self.refresh_manage()
        self.set_status(f"Deleted {done} mod(s)")


    def fetch_cover(self, url):
        if url in self.covers or url in self.loading:
            return
        self.loading.add(url)

        def job():
            try:
                data = get_bytes(url)
            except Exception:
                data = None
            self.jobs.put(lambda: self.cover_ready(url, data))

        threading.Thread(target=job, daemon=True).start()

    def cover_ready(self, url, data):
        self.loading.discard(url)
        try:
            ext = os.path.splitext(urllib.parse.urlparse(url).path)[1][1:].lower() or "jpg"
            img = pygame.image.load(io.BytesIO(data), "cover." + ext).convert()
            self.covers[url] = fit_cover(img, COVER_W, COVER_H)
        except Exception:
            self.covers[url] = False


    def launch(self):
        if not self.exe:
            return self.set_status("Game not found: choose the game folder in OPTIONS")
        cmd = ["open", "-W", self.exe] if self.exe.endswith(".app") else [self.exe]  
        proc = subprocess.Popen(cmd, cwd=os.path.dirname(self.exe))
        self.set_status("Starting the game...")
        if self.cfg["close_on_play"]:
            self.running = False
        else:
            self.games_running += 1
            self.apply_music()                      
            threading.Thread(target=self.wait_game, args=(proc,), daemon=True).start()

    def wait_game(self, proc):
        proc.wait()
        self.jobs.put(self.game_closed)          

    def game_closed(self):
        self.games_running = max(0, self.games_running - 1)
        self.apply_music()                          


    def draw(self):
        s = self.screen
        s.blit(self.bg, (0, 0))
        mouse = pygame.mouse.get_pos()
        active = "mods" if self.tab == "manage" else self.tab
        for name, rect in MENU.items():
            normal, selected = self.menu[name]
            on = active == name or rect.collidepoint(mouse)
            s.blit(selected if on else normal, rect)
        if self.tab == "game":
            self.draw_game()
        elif self.tab == "mods":
            self.draw_mods()
        elif self.tab == "manage":
            self.draw_manage()
        else:
            self.draw_opts()
        self.text(VERSION_LINES[0], self.f_small, GREY, 24, 716)
        self.text(VERSION_LINES[1], self.f_small, GREY, 24, 744)
        self.text(self.status, self.f_small, self.accent, 440, 735)

    def draw_game(self):
        k = 1 + 0.012 * math.sin(pygame.time.get_ticks() / 250)   
        w, h = int(self.logo.get_width() * k), int(self.logo.get_height() * k)
        self.screen.blit(pygame.transform.smoothscale(self.logo, (w, h)), (855 - w // 2, 354 - h // 2))
        self.screen.blit(self.mods_img, MODS_BTN)
        self.screen.blit(self.launch_img, LAUNCH_BTN)

    def draw_mods(self):
        self.panel(*PANEL)
        title = ("Search results" if self.active_query else "GameBanana Mods") + f" - page {self.page}"
        self.text(title, self.f_body, self.accent, 455, 44)
        self.draw_search()
        if not self.mods:
            self.text("Nothing to show. See the status line below", self.f_small, GREY, 455, 160)
        self.draw_cards(self.mods, lambda it: it.get("_idRow") in self.selected)
        self.button(CAT_PREV, "Back", BLACK, WHITE)
        self.button(CAT_NEXT, "Next", BLACK, WHITE)
        self.button(CAT_PICK, f"Download selected ({len(self.selected)})", self.accent, BLACK)
        self.button(CAT_ALL, "Download page", BLACK, WHITE)

    def draw_manage(self):
        self.panel(*PANEL)
        self.text(f"Installed mods: {len(self.man_items)}", self.f_body, self.accent, 455, 44)
        if not self.man_items:
            self.text("No installed mods found in the game folder", self.f_small, GREY, 455, 160)
        start = self.man_page * PER_PAGE
        self.draw_cards(self.man_items[start:start + PER_PAGE], lambda it: it["path"] in self.man_sel,
                        picture=self.draw_installed_picture)
        self.button(MAN_BACK, "Back", BLACK, WHITE)
        self.button(MAN_PREV, "Prev", BLACK, WHITE)
        self.button(MAN_NEXT, "Next", BLACK, WHITE)
        self.button(MAN_TOGGLE, "On / Off", self.accent, BLACK)
        self.button(MAN_DELETE, "Confirm delete" if self.delete_armed else "Delete", RED, WHITE)

    def draw_cards(self, items, is_selected, picture=None):
        for i, it in enumerate(items):
            x = GRID_X + (i % 3) * (CARD_W + GAP_X)
            y = GRID_Y + (i // 3) * (CARD_H + GAP_Y)
            sel, off = is_selected(it), bool(it.get("off"))
            pygame.draw.rect(self.screen, self.accent if sel else (30, 24, 14), (x, y, CARD_W, CARD_H))
            rect = pygame.Rect(x + 6, y + 8, COVER_W, COVER_H)
            if picture:
                picture(it, rect)
            else:
                self.draw_cover(cover_url(it), rect)
            name = it.get("name") or it.get("_sName") or "???"
            if off:
                name = "[OFF] " + name
            color = BLACK if sel else (GREY if off else WHITE)
            self.draw_wrapped(name[:70], self.f_tiny, color, x + 110, y + 8, CARD_W - 118, 3)

    def draw_installed_picture(self, it, rect):
        icon = os.path.join(it["path"], "_polymod_icon.png")
        if icon not in self.covers:                
            self.covers[icon] = load_icon(icon)
        img = self.covers[icon]
        if img:
            self.screen.blit(img, img.get_rect(center=rect.center))
        else:
            self.draw_cover(cover_url(it), rect)

    def draw_cover(self, url, rect):
        img = self.covers.get(url) if url else None
        if img:
            self.screen.blit(img, rect)
            return
        if url:
            self.fetch_cover(url)
        pygame.draw.rect(self.screen, (40, 32, 18), rect)

    def draw_wrapped(self, text, font, color, x, y, width, max_lines):
        lines, line = [], ""
        for word in text.split():
            trial = f"{line} {word}".strip()
            if font.size(trial)[0] <= width or not line:
                line = trial
            else:
                lines.append(line)
                line = word
        if line:
            lines.append(line)
        for i, ln in enumerate(lines[:max_lines]):
            self.text(ln, font, color, x, y + i * 20)

    def draw_search(self):
        r = SEARCH_RECT
        pygame.draw.rect(self.screen, (20, 16, 10), r)
        pygame.draw.rect(self.screen, self.accent if self.editing else GREY, r, 2)
        if self.query or self.editing:
            self.text((self.query + ("|" if self.editing else ""))[-60:], self.f_small, WHITE, r.x + 10, r.y + 11)
        else:
            self.text("Click here to search mods, then press Enter", self.f_small, GREY, r.x + 10, r.y + 11)

    def draw_opts(self):
        self.panel(*PANEL)
        self.text("Launcher", self.f_title, WHITE, 455, 4)
        self.text("Game Folder", self.f_body, WHITE, 444, 118)
        self.text("Browse...", self.f_body, self.accent, 444 + self.f_body.size("Game Folder ")[0] + 20, 118)
        path = self.cfg["game_dir"]
        if not path:
            self.text("No folder chosen yet", self.f_small, GREY, 444, 166)
        else:
            shown = path if len(path) <= 70 else "..." + path[-67:]
            self.text(shown, self.f_small, GREEN if self.exe else RED, 444, 166)
        self.text("SFX", self.f_head, WHITE, 455, 196)
        for label, key, y in TOGGLES:
            self.text(label + ": ", self.f_body, WHITE, 452, y)
            on = self.cfg[key]
            self.text("ON" if on else "OFF", self.f_body, self.accent if on else GREY,
                      452 + self.f_body.size(label + ": ")[0], y)
        self.text("Customization", self.f_head, WHITE, 455, 406)
        self.text("Buttons Color: ", self.f_body, WHITE, 452, 500)
        name = dict(ACCENTS).get(self.cfg["accent"], "Custom")
        self.text(f"#{self.cfg['accent']} ({name})", self.f_body, self.accent,
                  452 + self.f_body.size("Buttons Color: ")[0], 500)

    def text(self, s, font, color, x, y):
        if s:
            self.screen.blit(font.render(s, True, color), (x, y))

    def panel(self, x, y, w, h):
        p = pygame.Surface((w, h), pygame.SRCALPHA)
        p.fill((0, 0, 0, 150))
        self.screen.blit(p, (x, y))

    def button(self, rect, label, bg, fg):
        pygame.draw.rect(self.screen, bg, rect)
        img = self.f_small.render(label, True, fg)
        self.screen.blit(img, img.get_rect(center=rect.center))

    def run(self):
        clock = pygame.time.Clock()
        while self.running:
            for e in pygame.event.get():
                self.on_event(e)
            while not self.jobs.empty():
                self.jobs.get()()
            self.draw()
            pygame.display.flip()
            clock.tick(60)
        pygame.quit()


if __name__ == "__main__":
    App().run()
