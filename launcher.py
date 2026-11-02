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
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from collections import Counter
from concurrent.futures import ThreadPoolExecutor


def folder_dialog():
    import tkinter as tk
    from tkinter import filedialog
    args = sys.argv
    at = args.index("--pick-folder")
    title = args[at + 1] if len(args) > at + 1 else "Choose the game folder"
    out_file = args[at + 2] if len(args) > at + 2 else None
    root = tk.Tk()
    root.withdraw()
    chosen = filedialog.askdirectory(title=title) or ""
    if out_file:                         
        with open(out_file, "w", encoding="utf-8") as f:
            f.write(chosen)
    elif sys.stdout is not None:
        sys.stdout.write(chosen)


if "--pick-folder" in sys.argv:
    folder_dialog()
    sys.exit(0)

import pygame

GB_GAME_ID = 8694
VERSION_LINES = ("Friday Night Funkin V-Slice", "PolyMod Launcher 0.2.5")
SETTINGS_FILE = os.path.join(os.path.expanduser("~"), ".fnf_launcher.json")
DEFAULT_CFG = {"game_dir": "", "bg_music": True, "sfx": True, "accent": "FDE871",
               "close_on_play": False, "lang": "en", "animations": True}
ACCENTS = [("FDE871", "acc_default"), ("31B0D1", "acc_cyan"), ("F9393F", "acc_red"),
           ("C24B99", "acc_purple"), ("12FA05", "acc_green")]
OPT_Y = {"head_launcher": 52, "folder": 118, "path": 166, "lang": 206, "close": 258,
         "head_sfx": 328, "bg_music": 394, "sounds": 446,
         "head_custom": 514, "color": 580, "anim": 632}
TOGGLES = [("tog_close", "close_on_play", OPT_Y["close"]),
           ("tog_bg_music", "bg_music", OPT_Y["bg_music"]), ("tog_sfx", "sfx", OPT_Y["sounds"]),
           ("tog_anim", "animations", OPT_Y["anim"])]
LANGUAGES = [("en", "English"), ("pt", "Português (BR)"), ("ru", "Русский"), ("es", "Español")]
SORT_KEYS = ["default", "newest", "liked", "viewed"]
SORT_FIELD = {"newest": "date", "liked": "likes", "viewed": "views"}

# ===== FONTS =====
LANG = "en"                              
FONT_FILE = {"en": "FunkinOptions.otf"} 
OTHER_FONT = "difficultyFont.ttf"    
OTHER_FONT_SCALE = 1.0              

W, H = 1280, 780
PER_PAGE = 15
DD_ROWS, DD_ROW = 9, 32                 

ASSETS = os.path.join(getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__))), "assets")
REQUIRED_ASSETS = ["FunkinOptions.otf", "menuDesat.png", "FNF_logo.png", "GameButton.png",
                   "GameButtonSelected.png", "ModsButton.png", "ModsButtonSelected.png",
                   "OptionsButton.png", "OptionsButtonSelected.png", "ButtonMods.png", "ButtonLaunch.png"]
BLACK, WHITE, GREY = (0, 0, 0), (255, 255, 255), (150, 150, 150)
GREEN, RED = (140, 255, 140), (255, 130, 130)
CARD_BG, CHIP_BG = (30, 24, 14), (20, 16, 10)
UA = {"User-Agent": "FNF-Launcher/1.0"}
MODS_DIR, OFF_DIR, META_FILE = "mods", "mods_disabled", "fnf_mod.json"
COVER_W, COVER_H = 96, 60
GRID_X, GRID_Y, CARD_W, CARD_H, GAP_X, GAP_Y = 445, 190, 252, 76, 12, 4

MENU = {"game": pygame.Rect(0, 0, 400, 130), "mods": pygame.Rect(0, 130, 400, 130),
        "opts": pygame.Rect(0, 260, 400, 130)}
MODS_BTN = pygame.Rect(518, 601, 230, 100)
LAUNCH_BTN = pygame.Rect(750, 586, 400, 130)
PANEL = (430, 40, 820, 560)
SEARCH_RECT = pygame.Rect(440, 92, 800, 44)
CHIP_CAT, CHIP_SORT = pygame.Rect(440, 142, 220, 36), pygame.Rect(670, 142, 220, 36)
CHIP_HIDE, CHIP_RESET = pygame.Rect(900, 142, 220, 36), pygame.Rect(1130, 142, 110, 36)
CAT_PREV, CAT_NEXT = pygame.Rect(440, 600, 120, 60), pygame.Rect(575, 600, 120, 60)
CAT_PICK, CAT_ALL = pygame.Rect(710, 600, 300, 60), pygame.Rect(1020, 600, 220, 60)
MAN_BACK, MAN_PREV = pygame.Rect(440, 600, 130, 60), pygame.Rect(585, 600, 110, 60)
MAN_NEXT, MAN_TOGGLE = pygame.Rect(705, 600, 110, 60), pygame.Rect(825, 600, 200, 60)
MAN_DELETE = pygame.Rect(1035, 600, 200, 60)
BROWSE_RECT = pygame.Rect(440, OPT_Y["folder"] - 6, 560, 50)
COLOR_RECT = pygame.Rect(440, OPT_Y["color"] - 4, 760, 46)
LANG_ROW = pygame.Rect(440, OPT_Y["lang"] - 4, 760, 46)
OPT_PANEL = (430, 40, 820, 660)
BEST_W, BEST_IMG_H = 368, 207     
BEST_RECT = pygame.Rect(16, 404, BEST_W, 296)
BEST_WINDOW = 24 * 3600               

STRINGS = {
    "dialog_title": dict(en="Choose the game folder", pt="Escolha a pasta do jogo",
                         ru="Выберите папку с игрой", es="Elige la carpeta del juego"),
    "st_choose_window": dict(en="Choose the folder in the window...", pt="Escolha a pasta na janela...",
                             ru="Выберите папку в открывшемся окне...", es="Elige la carpeta en la ventana..."),
    "st_game_found": dict(en="Game found", pt="Jogo encontrado", ru="Игра найдена", es="Juego encontrado"),
    "st_no_game_file": dict(en="No game file found in this folder", pt="Nenhum arquivo do jogo nesta pasta",
                            ru="В этой папке не найден файл игры", es="No se encontró el juego en esta carpeta"),
    "st_game_not_found": dict(en="Game not found: choose the game folder in OPTIONS",
                              pt="Jogo não encontrado: escolha a pasta do jogo em OPÇÕES",
                              ru="Игра не найдена: выберите папку с игрой в НАСТРОЙКАХ",
                              es="Juego no encontrado: elige la carpeta del juego en OPCIONES"),
    "st_choose_game_first": dict(en="Choose the game folder in OPTIONS first",
                                 pt="Antes, escolha a pasta do jogo em OPÇÕES",
                                 ru="Сначала выберите папку с игрой в НАСТРОЙКАХ",
                                 es="Primero elige la carpeta del juego en OPCIONES"),
    "st_searching": dict(en="Searching for: {q}", pt="Buscando: {q}", ru="Ищу: {q}", es="Buscando: {q}"),
    "st_no_connection": dict(en="No connection to GameBanana: {e}", pt="Sem conexão com o GameBanana: {e}",
                             ru="Нет связи с GameBanana: {e}", es="Sin conexión con GameBanana: {e}"),
    "st_loading_mod": dict(en="Loading mod {id}...", pt="Carregando o mod {id}...",
                           ru="Загружаю мод {id}...", es="Cargando el mod {id}..."),
    "st_mod_found": dict(en="Mod found, press Download selected",
                         pt="Mod encontrado, clique em Baixar selecionados",
                         ru="Мод найден, нажмите «Скачать выбранные»",
                         es="Mod encontrado, pulsa «Descargar seleccionados»"),
    "st_mod_unknown": dict(en="Mod added (name unknown), press Download selected",
                           pt="Mod adicionado (nome desconhecido), clique em Baixar selecionados",
                           ru="Мод добавлен (название неизвестно), нажмите «Скачать выбранные»",
                           es="Mod añadido (nombre desconocido), pulsa «Descargar seleccionados»"),
    "st_found": dict(en="Found {n} mods ({src})", pt="Encontrados {n} mods ({src})",
                     ru="Найдено модов: {n} ({src})", es="Encontrados {n} mods ({src})"),
    "src_search": dict(en="GameBanana search", pt="busca no GameBanana", ru="поиск на GameBanana",
                       es="búsqueda en GameBanana"),
    "src_list": dict(en="list of {n}", pt="lista de {n}", ru="список из {n}", es="lista de {n}"),
    "st_building": dict(en="Building the mod list: {n} mods so far", pt="Montando a lista de mods: {n} até agora",
                        ru="Собираю список модов: пока {n}", es="Creando la lista de mods: {n} hasta ahora"),
    "st_loading_list": dict(en="Loading the mod list...", pt="Carregando a lista de mods...",
                            ru="Загружаю список модов...", es="Cargando la lista de mods..."),
    "st_matches": dict(en="{n} mods match the filters", pt="{n} mods combinam com os filtros",
                       ru="Подходящих модов: {n}", es="{n} mods cumplen los filtros"),
    "st_loading_page": dict(en="Loading page {page}...", pt="Carregando a página {page}...",
                            ru="Загружаю страницу {page}...", es="Cargando la página {page}..."),
    "st_page": dict(en="Page {page}: {n} mods", pt="Página {page}: {n} mods",
                    ru="Страница {page}: модов {n}", es="Página {page}: {n} mods"),
    "st_nothing_selected": dict(en="Nothing selected", pt="Nada selecionado", ru="Ничего не выбрано",
                                es="Nada seleccionado"),
    "st_downloading": dict(en="Downloading {n} mod(s)...", pt="Baixando {n} mod(s)...",
                           ru="Скачиваю модов: {n}...", es="Descargando {n} mod(s)..."),
    "st_done": dict(en="Done. Mods are in the game's mods folder",
                    pt="Pronto. Os mods estão na pasta de mods do jogo",
                    ru="Готово. Моды лежат в папке mods игры",
                    es="Listo. Los mods están en la carpeta de mods del juego"),
    "st_no_zip": dict(en="No zip archive: {name}", pt="Nenhum arquivo zip: {name}",
                      ru="Нет zip-архива: {name}", es="No hay archivo zip: {name}"),
    "st_already": dict(en="Already installed: {name}", pt="Já instalado: {name}",
                       ru="Уже установлен: {name}", es="Ya instalado: {name}"),
    "st_installed": dict(en="Installed: {name}", pt="Instalado: {name}",
                         ru="Установлен: {name}", es="Instalado: {name}"),
    "st_error": dict(en="Error ({name}): {e}", pt="Erro ({name}): {e}",
                     ru="Ошибка ({name}): {e}", es="Error ({name}): {e}"),
    "st_mods_installed": dict(en="{n} mods installed", pt="{n} mods instalados",
                              ru="Установлено модов: {n}", es="{n} mods instalados"),
    "st_confirm_delete": dict(en="Press Confirm delete to remove {n} mod(s)",
                              pt="Clique em Confirmar exclusão para remover {n} mod(s)",
                              ru="Нажмите «Подтвердить», чтобы удалить модов: {n}",
                              es="Pulsa «Confirmar» para eliminar {n} mod(s)"),
    "st_deleted": dict(en="Deleted {n} mod(s)", pt="Excluído(s) {n} mod(s)",
                       ru="Удалено модов: {n}", es="Eliminado(s) {n} mod(s)"),
    "st_switched": dict(en="Switched {n} mod(s)", pt="Alterado(s) {n} mod(s)",
                        ru="Переключено модов: {n}", es="Cambiado(s) {n} mod(s)"),
    "st_errors": dict(en=", errors: {n}", pt=", erros: {n}", ru=", ошибок: {n}", es=", errores: {n}"),
    "st_starting": dict(en="Starting the game...", pt="Iniciando o jogo...", ru="Запускаю игру...",
                        es="Iniciando el juego..."),
    "st_no_match": dict(en="Nothing found. Try other words or filters",
                        pt="Nada encontrado. Tente outras palavras ou filtros",
                        ru="Ничего не найдено. Попробуйте другие слова или фильтры",
                        es="No se encontró nada. Prueba otras palabras o filtros"),
    "mods_search": dict(en="Search results", pt="Resultados da busca", ru="Результаты поиска",
                        es="Resultados de búsqueda"),
    "mods_browse": dict(en="GameBanana Mods", pt="Mods do GameBanana", ru="Моды GameBanana",
                        es="Mods de GameBanana"),
    "page_word": dict(en="page", pt="página", ru="страница", es="página"),
    "mods_empty": dict(en="Nothing to show. See the status line below",
                       pt="Nada para mostrar. Veja a linha de status abaixo",
                       ru="Пусто. Смотрите строку состояния внизу",
                       es="Nada que mostrar. Mira la línea de estado de abajo"),
    "search_hint": dict(en="Click here to search mods, then press Enter",
                        pt="Clique aqui para buscar mods e pressione Enter",
                        ru="Нажмите здесь, чтобы искать моды, и Enter",
                        es="Haz clic aquí para buscar mods y pulsa Enter"),
    "btn_back": dict(en="Back", pt="Voltar", ru="Назад", es="Atrás"),
    "btn_prev": dict(en="Prev", pt="Anterior", ru="Пред.", es="Anterior"),
    "btn_next": dict(en="Next", pt="Próxima", ru="След.", es="Siguiente"),
    "btn_download_selected": dict(en="Download selected ({n})", pt="Baixar selecionados ({n})",
                                  ru="Скачать выбранные ({n})", es="Descargar seleccionados ({n})"),
    "btn_download_page": dict(en="Download page", pt="Baixar página", ru="Скачать страницу",
                              es="Descargar página"),
    "btn_on_off": dict(en="On / Off", pt="Ligar / Desligar", ru="Вкл. / Выкл.", es="Activar / Desactivar"),
    "btn_delete": dict(en="Delete", pt="Excluir", ru="Удалить", es="Eliminar"),
    "btn_confirm_delete": dict(en="Confirm delete", pt="Confirmar exclusão", ru="Подтвердить", es="Confirmar"),
    "manage_title": dict(en="Installed mods: {n}", pt="Mods instalados: {n}",
                         ru="Установленные моды: {n}", es="Mods instalados: {n}"),
    "manage_empty": dict(en="No installed mods found in the game folder",
                         pt="Nenhum mod instalado na pasta do jogo",
                         ru="В папке игры нет установленных модов",
                         es="No hay mods instalados en la carpeta del juego"),
    "off_tag": dict(en="[OFF] ", pt="[DESLIG.] ", ru="[ВЫКЛ] ", es="[DESACT.] "),
    "flt_category": dict(en="Category", pt="Categoria", ru="Категория", es="Categoría"),
    "flt_all": dict(en="All", pt="Todas", ru="Все", es="Todas"),
    "flt_sort": dict(en="Sort", pt="Ordenar", ru="Сортировка", es="Orden"),
    "sort_default": dict(en="Default", pt="Padrão", ru="По умолчанию", es="Predeterminado"),
    "sort_newest": dict(en="Newest", pt="Mais recentes", ru="Новые", es="Más recientes"),
    "sort_liked": dict(en="Most liked", pt="Mais curtidos", ru="Больше лайков", es="Más gustados"),
    "sort_viewed": dict(en="Most viewed", pt="Mais vistos", ru="Больше просмотров", es="Más vistos"),
    "flt_hide": dict(en="Hide installed", pt="Ocultar instalados", ru="Скрыть установленные",
                     es="Ocultar instalados"),
    "flt_reset": dict(en="Reset", pt="Limpar", ru="Сбросить", es="Restablecer"),
    "opt_title": dict(en="Launcher", pt="Launcher", ru="Лаунчер", es="Launcher"),
    "opt_language": dict(en="Language", pt="Idioma", ru="Язык", es="Idioma"),
    "opt_game_folder": dict(en="Game Folder", pt="Pasta do jogo", ru="Папка игры", es="Carpeta del juego"),
    "opt_browse": dict(en="Browse...", pt="Procurar...", ru="Обзор...", es="Examinar..."),
    "opt_no_folder": dict(en="No folder chosen yet", pt="Nenhuma pasta escolhida ainda",
                          ru="Папка ещё не выбрана", es="Todavía no has elegido carpeta"),
    "opt_sound": dict(en="SFX", pt="Sons", ru="Звук", es="Sonido"),
    "opt_custom": dict(en="Customization", pt="Personalização", ru="Оформление", es="Personalización"),
    "opt_color": dict(en="Buttons Color", pt="Cor dos botões", ru="Цвет кнопок", es="Color de botones"),
    "tog_bg_music": dict(en="BG Music", pt="Música de fundo", ru="Фоновая музыка", es="Música de fondo"),
    "tog_sfx": dict(en="Sounds in launcher", pt="Sons do launcher", ru="Звуки в лаунчере",
                    es="Sonidos del launcher"),
    "tog_anim": dict(en="Smooth animations", pt="Animações suaves", ru="Плавные анимации",
                     es="Animaciones suaves"),
    "tog_close": dict(en="Close launcher on game start", pt="Fechar o launcher ao abrir o jogo",
                      ru="Закрывать лаунчер при запуске игры", es="Cerrar el launcher al abrir el juego"),
    "on": dict(en="ON", pt="LIGADO", ru="ВКЛ", es="SÍ"),
    "off": dict(en="OFF", pt="DESLIGADO", ru="ВЫКЛ", es="NO"),
    "acc_default": dict(en="Default", pt="Padrão", ru="По умолчанию", es="Predeterminado"),
    "acc_cyan": dict(en="Cyan", pt="Ciano", ru="Голубой", es="Cian"),
    "acc_red": dict(en="Red", pt="Vermelho", ru="Красный", es="Rojo"),
    "acc_purple": dict(en="Purple", pt="Roxo", ru="Фиолетовый", es="Morado"),
    "acc_green": dict(en="Green", pt="Verde", ru="Зелёный", es="Verde"),
    "acc_custom": dict(en="Custom", pt="Personalizado", ru="Свой", es="Personalizado"),
    "best_title": dict(en="Best of today", pt="Melhor de hoje", ru="Лучший мод дня", es="Lo mejor de hoy"),
    "best_loading": dict(en="Loading...", pt="Carregando...", ru="Загружаю...", es="Cargando..."),
    "best_none": dict(en="No mods added today yet", pt="Nenhum mod adicionado hoje ainda",
                      ru="Сегодня новых модов пока нет", es="Hoy aún no hay mods nuevos"),
    "best_error": dict(en="Could not load today's best mod", pt="Não foi possível carregar o destaque de hoje",
                       ru="Не удалось загрузить лучший мод дня", es="No se pudo cargar el mod destacado de hoy"),
    "best_likes": dict(en="Likes: {n}", pt="Curtidas: {n}", ru="Лайков: {n}", es="Me gusta: {n}"),
}

def tr(key, **kw):
    entry = STRINGS[key]
    text = entry.get(LANG) or entry["en"]
    return text.format(**kw) if kw else text


def set_language(code):
    global LANG
    LANG = code if code in dict(LANGUAGES) else "en"


def font_path():
    path = os.path.join(ASSETS, FONT_FILE.get(LANG, OTHER_FONT))
    if not os.path.isfile(path):                  
        path = os.path.join(ASSETS, FONT_FILE["en"])
    return path


def art_path(name):
    """assets/<lang>/<name> is used when you made a translated picture, otherwise the default one."""
    local = os.path.join(ASSETS, LANG, name)
    return local if os.path.isfile(local) else os.path.join(ASSETS, name)


def mix(a, b, t):
    return tuple(round(x + (y - x) * t) for x, y in zip(a, b))


def src_label(kind, total):
    return tr("src_search") if kind == "search" else tr("src_list", n=total)


def missing_assets():
    return [name for name in REQUIRED_ASSETS if not os.path.isfile(os.path.join(ASSETS, name))]


def later(key, **kw):
    """Text that is translated when it is drawn, so a status line follows a language change."""
    return lambda: tr(key, **kw)


def found_text(n, kind, total):
    return lambda: tr("st_found", n=n, src=src_label(kind, total))


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


def pick_folder(title):
    if getattr(sys, "frozen", False):
        cmd = [sys.executable]
    else:
        cmd = [sys.executable, os.path.abspath(__file__)]
    fd, out_file = tempfile.mkstemp(suffix=".txt")
    os.close(fd)
    try:
        subprocess.run(cmd + ["--pick-folder", title, out_file])
        with open(out_file, encoding="utf-8") as f:
            return f.read().strip()
    except OSError:
        return ""
    finally:
        try:
            os.remove(out_file)
        except OSError:
            pass


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

INDEX_FILE = os.path.join(os.path.expanduser("~"), ".fnf_mods_index.json")
INDEX_VERSION = 2     
INDEX_LOCK = threading.Lock()
MAX_INDEX_PAGES = 1000
COMMON_WORDS = {"fnf", "friday", "night", "funkin"}


def mod_item(r):
    """What the launcher keeps about a mod: id, name, cover and the fields the filters use."""
    cat = r.get("_aCategory")
    if isinstance(cat, list):
        cat = cat[0] if cat else None
    return {"_idRow": r.get("_idRow"), "_sName": r.get("_sName") or "", "cover": cover_url(r),
            "cat": (cat.get("_sName") if isinstance(cat, dict) else "") or "",
            "date": r.get("_tsDateAdded") or 0, "likes": r.get("_nLikeCount") or 0,
            "views": r.get("_nViewCount") or 0}


def fetch_mod_page(page):
    url = f"https://gamebanana.com/apiv11/Game/{GB_GAME_ID}/Subfeed?_nPage={page}&_sSort=default"
    records = get_json(url).get("_aRecords", [])
    return [mod_item(r) for r in records if r.get("_sModelName") == "Mod" and r.get("_idRow")]


def subfeed_url(page, perpage=None):
    url = (f"https://gamebanana.com/apiv11/Game/{GB_GAME_ID}/Subfeed?_nPage={page}"
           f"&_sSort=default&_csvModelInclusions=Mod")
    return url + (f"&_nPerpage={perpage}" if perpage else "")


def banner_url(rec):
    try:
        img = rec["_aPreviewMedia"]["_aImages"][0]
    except (KeyError, IndexError, TypeError):
        return None
    base = img.get("_sBaseUrl")
    file = img.get("_sFile530") or img.get("_sFile") or img.get("_sFile220")
    return f"{base}/{file}" if base and file else None


def fetch_best_today(max_pages=3):
    """The most liked mod added or updated in the last 24 hours, looked for in the newest pages of the feed."""
    cutoff = time.time() - BEST_WINDOW
    fresh = {}
    for page in range(1, max_pages + 1):
        records = get_json(subfeed_url(page)).get("_aRecords", [])
        found = 0
        for r in records:
            stamp = max(r.get("_tsDateAdded") or 0, r.get("_tsDateModified") or 0)
            if (r.get("_sModelName") == "Mod" and r.get("_idRow") and stamp >= cutoff
                    and not r.get("_bHasContentRatings")):
                fresh[r["_idRow"]] = r
                found += 1
        if not records or found == 0:
            break
    if not fresh:
        return None
    top = max(fresh.values(), key=lambda r: (r.get("_nLikeCount") or 0, r.get("_nViewCount") or 0))
    item = mod_item(top)
    item["banner"] = banner_url(top)
    return item


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
        hits += [mod_item(r) for r in records if r.get("_idRow") and name_matches(query, r.get("_sName"))]
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
    if old and old.get("version") == INDEX_VERSION and "next_page" in old and not old.get("complete"):
        mods, page, perpage = old["mods"], old["next_page"], old.get("perpage")
    else:
        mods, page, perpage = [], 1, pick_perpage()
    seen = {m["_idRow"] for m in mods}
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
                        mods.append(mod_item(r))
                        added += 1
            page += len(batch)
            complete = complete or page > MAX_INDEX_PAGES or added == 0
            save_index({"version": INDEX_VERSION, "time": time.time(), "complete": complete,
                        "next_page": page, "perpage": perpage, "mods": mods})
            progress(later("st_building", n=len(mods)))
            if complete:
                break
    return mods


def load_index(progress):
    data = read_index()
    if (data and data.get("version") == INDEX_VERSION and data.get("complete", "next_page" not in data)
            and time.time() - data["time"] < 7 * 24 * 3600):
        return data["mods"]
    return build_index(progress)


def search_mods(query, progress):
    """Returns (hits, kind, total). kind is 'search' for GameBanana's own search, 'list' for the index."""
    if not compact(query):
        return [], "search", 0
    try:
        hits = search_remote(query)
        if hits:
            return hits, "search", len(hits)
    except urllib.error.HTTPError:
        pass
    with INDEX_LOCK:
        mods = load_index(progress)
    return [dict(m) for m in mods if name_matches(query, m["_sName"])], "list", len(mods)


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
                              "name": meta.get("name") or name, "cover": meta.get("cover"),
                              "id": meta.get("id")})
    return items


def installed_keys(game):
    """Mod ids and folder names already in the game's mods folders (enabled or disabled)."""
    ids, names = set(), set()
    for it in scan_mods(game):
        names.add(it["folder"].lower())
        if it.get("id"):
            ids.add(it["id"])
    return ids, names


def is_installed(mod, ids, names):
    name = mod.get("_sName") or ""
    return mod.get("_idRow") in ids or (bool(name) and safe(name).lower() in names)


def filter_mods(mods, filters, ids, names):
    out = []
    for m in mods:
        if filters["cat"] and m.get("cat") != filters["cat"]:
            continue
        if filters["hide"] and is_installed(m, ids, names):
            continue
        out.append(m)
    field = SORT_FIELD.get(filters["sort"])
    if field:
        out.sort(key=lambda m: m.get(field) or 0, reverse=True)
    return out


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


def install_mod(mod, mods_dir, say):
    files = mod_files(mod["_idRow"])
    zips = [f for f in files if (f.get("_sFile") or "").lower().endswith(".zip")]
    if not zips:
        say(later("st_no_zip", name=mod["_sName"]))
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
        if os.path.exists(folder) or os.path.exists(off_folder):
            say(later("st_already", name=mod["_sName"]))
        else:
            z.extractall(mods_dir if single else folder)
            with open(os.path.join(folder, META_FILE), "w", encoding="utf-8") as f:
                json.dump({"id": mod["_idRow"], "name": mod["_sName"], "cover": cover_url(mod)},
                          f, ensure_ascii=False)
            say(later("st_installed", name=mod["_sName"]))
    os.remove(tmp)


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
        set_language(self.cfg["lang"])
        self.jobs = queue.Queue()
        self.tab, self.status, self.running = "game", "", True
        self.status_t0 = 0
        self.fullscreen = False
        self.games_running = 0
        self.exe = find_game(self.cfg["game_dir"])
        self.query, self.active_query, self.editing = "", "", False
        self.req = 0                     
        self.source, self.hits, self.listing = None, [], False
        self.page, self.mods, self.selected = 1, [], {}
        self.filters = {"cat": "", "sort": "default", "hide": False}
        self.dropdown = None
        self.catalog, self.catalog_busy, self.catalog_waiters = None, False, []
        self.man_items, self.man_sel, self.man_page, self.delete_armed = [], set(), 0, False
        self.covers, self.loading = {}, set()
        self.cover_known, self.cover_asked = {}, set()
        self.cover_slots = threading.Semaphore(4)
        self.anim, self.dt, self.reveal_t0 = {}, 0.016, 0
        self.font_cache = {}
        self.banners = {}
        self.best, self.best_state, self.best_t0 = None, "idle", 0
        self.load_assets()
        self.apply_music()
        self.load_page()

    def change_language(self):
        codes = [c for c, _ in LANGUAGES]
        cur = self.cfg["lang"] if self.cfg["lang"] in codes else "en"
        self.cfg["lang"] = codes[(codes.index(cur) + 1) % len(codes)]
        self.save()
        set_language(self.cfg["lang"])
        self.load_fonts()
        self.load_art()
        self.build_tints()
        self.play("select")

    def get_font(self, size):
        key = (font_path(), size)
        if key not in self.font_cache:
            self.font_cache[key] = pygame.font.Font(key[0], size)
        return self.font_cache[key]

    def sized(self, base):
        scale = 1.0 if LANG == "en" else OTHER_FONT_SCALE
        return self.get_font(round(base * scale))

    def fit_font(self, text, base, max_w):
        """The biggest font, starting from base, at which the text fits max_w pixels."""
        size = base
        while size > 12:
            font = self.sized(size)
            if font.size(text)[0] <= max_w:
                return font
            size -= 2
        return self.sized(12)

    def load_fonts(self):
        self.f_title, self.f_head = self.sized(70), self.sized(56)
        self.f_body, self.f_small, self.f_tiny = self.sized(38), self.sized(22), self.sized(16)

    def load_art(self):
        def png(path):
            return pygame.image.load(path).convert_alpha()

        self.raw_menu = {
            "game": (png(art_path("GameButton.png")), png(art_path("GameButtonSelected.png"))),
            "mods": (png(art_path("ModsButton.png")), png(art_path("ModsButtonSelected.png"))),
            "opts": (png(art_path("OptionsButton.png")), png(art_path("OptionsButtonSelected.png"))),
        }
        self.raw_launch = png(art_path("ButtonLaunch.png"))
        self.mods_img = png(art_path("ButtonMods.png"))
        logo = png(os.path.join(ASSETS, "FNF_logo.png"))
        self.logo = pygame.transform.smoothscale(logo, (690, round(690 * logo.get_height() / logo.get_width())))

    def load_assets(self):
        self.load_fonts()
        self.load_art()
        raw = pygame.image.load(os.path.join(ASSETS, "menuDesat.png")).convert()
        bw = round(raw.get_width() * H / raw.get_height())
        base = pygame.transform.smoothscale(raw, (bw, H))
        base = base.subsurface(pygame.Rect((bw - W) // 2, 0, W, H)).copy()
        avg = sum(pygame.transform.average_color(base, pygame.Rect(0, 0, 60, 60))[:3]) // 3
        base.fill((255 - avg,) * 3, special_flags=pygame.BLEND_RGB_ADD)
        self.bg_base = base
        self.sfx = {}
        if pygame.mixer.get_init():
            for key, name in (("select", "CS_select.ogg"), ("confirm", "CS_confirm.ogg")):
                try:
                    self.sfx[key] = pygame.mixer.Sound(os.path.join(ASSETS, name))
                except (pygame.error, OSError):
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
            except (pygame.error, OSError):
                pass
        else:
            pygame.mixer.music.stop()

    def play(self, key):
        if self.cfg["sfx"] and key in self.sfx:
            self.sfx[key].play()


    def ease(self, key, target, speed=14.0):
        """Moves a stored value toward target. With animations switched off it jumps there at once."""
        cur = self.anim.get(key, target)
        if self.cfg["animations"]:
            cur += (target - cur) * (1.0 - math.exp(-speed * self.dt))
            if abs(target - cur) < 0.003:
                cur = target
        else:
            cur = target
        self.anim[key] = cur
        return cur

    def restart_reveal(self):
        self.reveal_t0 = pygame.time.get_ticks()

    def reveal(self, index):
        """0..1 entrance progress of a card. Cards come in one after another."""
        if not self.cfg["animations"]:
            return 1.0
        age = (pygame.time.get_ticks() - self.reveal_t0) / 1000 - index * 0.03
        t = min(1.0, max(0.0, age / 0.25))
        return 1 - (1 - t) ** 3

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
        elif e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE and self.dropdown:
            self.dropdown = None
        elif e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE and self.fullscreen and not self.editing:
            self.toggle_fullscreen()
        elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            self.on_click(e.pos)
        elif e.type == pygame.MOUSEWHEEL and self.dropdown:
            self.scroll_dropdown(-e.y)
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
        if self.dropdown:
            if self.dropdown_click(pos):
                return
            self.dropdown = None
        if self.best_state == "ready" and BEST_RECT.collidepoint(pos):
            return self.best_click()
        if self.tab == "mods" and SEARCH_RECT.collidepoint(pos):
            self.editing = True
            return
        self.editing = False
        for name, rect in MENU.items():
            if rect.collidepoint(pos):
                self.play("select")
                self.go_tab(name)
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

    def go_tab(self, name):
        self.dropdown = None
        if name != self.tab:
            self.anim["tab"] = 0.0      
        self.tab = name

    def card_at(self, pos):
        for i in range(PER_PAGE):
            x = GRID_X + (i % 3) * (CARD_W + GAP_X)
            y = GRID_Y + (i // 3) * (CARD_H + GAP_Y)
            if pygame.Rect(x, y, CARD_W, CARD_H).collidepoint(pos):
                return i
        return None

    def opts_click(self, pos):
        if LANG_ROW.collidepoint(pos):
            return self.change_language()
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
        title = tr("dialog_title")

        def job():
            path = pick_folder(title)
            self.jobs.put(lambda: self.set_game_dir(path))

        self.set_status(later("st_choose_window"))
        threading.Thread(target=job, daemon=True).start()

    def set_game_dir(self, path):
        if path:
            self.cfg["game_dir"] = path
            self.save()
            self.exe = find_game(path)
            self.set_status(later("st_game_found") if self.exe else later("st_no_game_file"))

    def save(self):
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(self.cfg, f, ensure_ascii=False, indent=2)

    def set_status(self, text):
        """A string, or a function returning the text, so the line is translated when it is drawn."""
        self.status = text
        self.status_t0 = pygame.time.get_ticks()

    def status_text(self):
        return self.status() if callable(self.status) else (self.status or "")


    def mods_click(self, pos):
        if CHIP_CAT.collidepoint(pos):
            self.play("select")
            return self.open_dropdown("cat")
        if CHIP_SORT.collidepoint(pos):
            self.play("select")
            return self.open_dropdown("sort")
        if CHIP_HIDE.collidepoint(pos):
            self.play("select")
            self.filters["hide"] = not self.filters["hide"]
            return self.refresh_view()
        if CHIP_RESET.collidepoint(pos):
            self.play("select")
            self.filters = {"cat": "", "sort": "default", "hide": False}
            return self.refresh_view()
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
            self.go_tab("game")
        elif MAN_PREV.collidepoint(pos) and self.man_page > 0:
            self.man_page -= 1
            self.restart_reveal()
        elif MAN_NEXT.collidepoint(pos) and (self.man_page + 1) * PER_PAGE < len(self.man_items):
            self.man_page += 1
            self.restart_reveal()
        elif MAN_TOGGLE.collidepoint(pos):
            self.toggle_selected()
        elif MAN_DELETE.collidepoint(pos):
            self.delete_selected()

    def progress_for(self, rid):
        def progress(msg):
            self.jobs.put(lambda: self.set_status(msg) if rid == self.req else None)
        return progress

    def request_failed(self, rid, err):
        if rid == self.req:
            self.set_status(later("st_no_connection", e=err))

    def start_search(self):
        self.active_query = self.query.strip()
        self.page, self.selected = 1, {}
        if not self.active_query:
            return self.refresh_view()
        q = self.active_query
        by_id = re.search(r"/mods/(\d+)", q) or re.fullmatch(r"(\d{5,})", q)
        if by_id:
            return self.open_mod(int(by_id.group(1)))
        self.req += 1
        rid = self.req
        self.source, self.hits, self.mods, self.listing = None, [], [], True
        self.set_status(later("st_searching", q=q))

        def job():
            try:
                hits, kind, total = search_mods(q, self.progress_for(rid))
                self.jobs.put(lambda: self.show_hits(
                    rid, hits, lambda n: found_text(n, kind, total)))
            except Exception as e:
                err = e
                self.jobs.put(lambda: self.request_failed(rid, err))

        threading.Thread(target=job, daemon=True).start()

    def open_mod(self, mod_id):
        self.req += 1
        rid = self.req
        self.source, self.hits, self.mods, self.listing = None, [], [], True
        self.set_status(later("st_loading_mod", id=mod_id))

        def job():
            name = mod_name(mod_id)
            rec = {"_idRow": mod_id, "_sName": name or f"Mod {mod_id}", "cover": None,
                   "cat": "", "date": 0, "likes": 0, "views": 0}
            self.jobs.put(lambda: self.show_hits(
                rid, [rec], lambda n: later("st_mod_found") if name else later("st_mod_unknown")))

        threading.Thread(target=job, daemon=True).start()

    def show_hits(self, rid, hits, status):
        if rid != self.req:
            return
        self.source, self.page = hits, 1
        self.apply_view()
        self.set_status(status(len(self.hits)))

    def show_mods(self, rid, page, mods):
        if rid != self.req:
            return
        self.mods = mods
        self.restart_reveal()
        self.set_status(later("st_page", page=page, n=len(mods)))

    def load_page(self):
        """Browse mode: GameBanana's own pages, fast, no filters."""
        self.req += 1
        rid, page = self.req, self.page
        if page == 1:
            self.maybe_load_best()
        self.set_status(later("st_loading_page", page=page))

        def job():
            try:
                mods = fetch_mod_page(page)
                self.jobs.put(lambda: self.show_mods(rid, page, mods))
            except Exception as e:
                err = e
                self.jobs.put(lambda: self.request_failed(rid, err))

        threading.Thread(target=job, daemon=True).start()

    def filters_active(self):
        f = self.filters
        return bool(f["cat"]) or f["sort"] != "default" or f["hide"]

    def refresh_view(self):
        """Rebuilds the list after the query, the filters or the game folder changed."""
        self.page = 1
        if self.active_query:
            if self.source is not None:
                self.apply_view()
            return
        if self.filters_active():
            self.req += 1                    
            if self.catalog is None:
                self.set_status(later("st_loading_list"))
                return self.ensure_catalog(self.refresh_view)
            self.source = self.catalog
            return self.apply_view()
        self.listing, self.source = False, None
        self.load_page()

    def apply_view(self):
        ids, names = installed_keys(self.cfg["game_dir"]) if self.filters["hide"] else (set(), set())
        self.hits = filter_mods(self.source or [], self.filters, ids, names)
        self.listing = True
        self.show_hit_page()
        self.restart_reveal()
        self.set_status(later("st_matches", n=len(self.hits)))

    def show_hit_page(self):
        self.mods = self.hits[(self.page - 1) * PER_PAGE:self.page * PER_PAGE]
        self.request_covers(self.mods)

    def change_page(self, step):
        new = self.page + step
        if new < 1 or (self.listing and (new - 1) * PER_PAGE >= len(self.hits)):
            return
        self.page = new
        if self.listing:
            self.show_hit_page()
            self.restart_reveal()
        else:
            self.load_page()

    def ensure_catalog(self, then=None):
        """Loads the full mod index once (it is cached on disk), then runs the callbacks waiting for it."""
        if then is not None:
            self.catalog_waiters.append(then)
        if self.catalog is not None:
            waiters, self.catalog_waiters = self.catalog_waiters, []
            for fn in waiters:
                fn()
            return
        if self.catalog_busy:
            return
        self.catalog_busy = True

        def progress(msg):
            self.jobs.put(lambda: self.set_status(msg))

        def job():
            try:
                with INDEX_LOCK:
                    mods = load_index(progress)
                self.jobs.put(lambda: self.catalog_ready(mods))
            except Exception as e:
                err = e
                self.jobs.put(lambda: self.catalog_failed(err))

        threading.Thread(target=job, daemon=True).start()

    def catalog_ready(self, mods):
        self.catalog, self.catalog_busy = mods, False
        self.ensure_catalog()

    def catalog_failed(self, err):
        self.catalog_busy, self.catalog_waiters = False, []
        self.set_status(later("st_no_connection", e=err))

    def open_dropdown(self, key):
        if key == "cat":
            if self.catalog is None:
                self.set_status(later("st_loading_list"))
                return self.ensure_catalog(lambda: self.open_dropdown("cat"))
            counts = Counter(m.get("cat") for m in self.catalog if m.get("cat"))
            items = [("", tr("flt_all"))] + [(c, f"{c} ({n})") for c, n in counts.most_common()]
            rect = CHIP_CAT
        else:
            items = [(k, tr("sort_" + k)) for k in SORT_KEYS]
            rect = CHIP_SORT
        self.dropdown = {"key": key, "items": items, "rect": rect, "scroll": 0}

    def dd_box(self):
        dd = self.dropdown
        rows = min(len(dd["items"]), DD_ROWS)
        r = dd["rect"]
        return pygame.Rect(r.x, r.bottom + 4, max(r.w, 300), rows * DD_ROW + 4)

    def dropdown_click(self, pos):
        dd = self.dropdown
        box = self.dd_box()
        if not box.collidepoint(pos):
            return False
        visible = dd["items"][dd["scroll"]:dd["scroll"] + DD_ROWS]
        i = (pos[1] - box.y - 2) // DD_ROW
        if 0 <= i < len(visible):
            self.filters[dd["key"]] = visible[i][0]
            self.dropdown = None
            self.play("select")
            self.refresh_view()
        return True

    def scroll_dropdown(self, step):
        dd = self.dropdown
        dd["scroll"] = max(0, min(len(dd["items"]) - DD_ROWS, dd["scroll"] + step))

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

    def download(self, mods):
        folder = self.cfg["game_dir"]
        if not os.path.isdir(folder):
            return self.set_status(later("st_choose_game_first"))
        if not mods:
            return self.set_status(later("st_nothing_selected"))
        self.play("confirm")
        mods_dir = os.path.join(folder, MODS_DIR)

        def say(msg):
            self.jobs.put(lambda: self.set_status(msg))

        def job():
            os.makedirs(mods_dir, exist_ok=True)
            for m in mods:
                try:
                    install_mod(m, mods_dir, say)
                except Exception as e:
                    say(later("st_error", name=m.get("_sName", "?"), e=e))
            say(later("st_done"))

        self.set_status(later("st_downloading", n=len(mods)))
        threading.Thread(target=job, daemon=True).start()

    def open_manage(self):
        if not os.path.isdir(self.cfg["game_dir"]):
            return self.set_status(later("st_choose_game_first"))
        self.go_tab("manage")
        self.man_page, self.man_sel, self.delete_armed = 0, set(), False
        self.refresh_manage()
        self.restart_reveal()
        self.set_status(later("st_mods_installed", n=len(self.man_items)))

    def refresh_manage(self):
        self.man_items = scan_mods(self.cfg["game_dir"])
        self.man_page = min(self.man_page, max(0, (len(self.man_items) - 1) // PER_PAGE))

    def toggle_selected(self):
        if not self.man_sel:
            return self.set_status(later("st_nothing_selected"))
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
        self.set_status(lambda: tr("st_switched", n=done) + (tr("st_errors", n=errors) if errors else ""))

    def delete_selected(self):
        if not self.man_sel:
            return self.set_status(later("st_nothing_selected"))
        if not self.delete_armed:
            self.delete_armed = True
            return self.set_status(later("st_confirm_delete", n=len(self.man_sel)))
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
        self.set_status(later("st_deleted", n=done))

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
            return self.set_status(later("st_game_not_found"))
        cmd = ["open", "-W", self.exe] if self.exe.endswith(".app") else [self.exe]
        proc = subprocess.Popen(cmd, cwd=os.path.dirname(self.exe))
        self.set_status(later("st_starting"))
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
            h = self.ease(("menu", name), 1.0 if on else 0.0, 18.0)
            if h < 1:
                s.blit(normal, rect)
            if h > 0:                          
                selected.set_alpha(round(255 * h))
                s.blit(selected, rect)
                selected.set_alpha(255)
        if self.tab == "game":
            self.draw_game()
        elif self.tab == "mods":
            self.draw_mods()
        elif self.tab == "manage":
            self.draw_manage()
        else:
            self.draw_opts()
        self.draw_best()
        t = self.ease("tab", 1.0, 9.0)
        if t < 1:                         
            shade = pygame.Surface((W - 400, H))
            shade.fill(BLACK)
            shade.set_alpha(round(180 * (1 - t)))
            s.blit(shade, (400, 0))
        self.text(VERSION_LINES[0], self.f_small, GREY, 24, 716)
        self.text(VERSION_LINES[1], self.f_small, GREY, 24, 744)
        fade = 255
        if self.cfg["animations"]:
            fade = min(255, round((pygame.time.get_ticks() - self.status_t0) * 255 / 300))
        self.text(self.status_text(), self.f_small, self.accent, 440, 735, fade)

    def draw_game(self):
        k = 1 + 0.012 * math.sin(pygame.time.get_ticks() / 250) if self.cfg["animations"] else 1.0
        w, h = int(self.logo.get_width() * k), int(self.logo.get_height() * k)
        self.screen.blit(pygame.transform.smoothscale(self.logo, (w, h)), (855 - w // 2, 354 - h // 2))
        self.screen.blit(self.mods_img, MODS_BTN)
        self.screen.blit(self.launch_img, LAUNCH_BTN)

    def draw_mods(self):
        self.panel(*PANEL)
        title = tr("mods_search") if self.active_query else tr("mods_browse")
        self.text(f"{title} - {tr('page_word')} {self.page}", self.f_body, self.accent, 455, 44)
        self.draw_search()
        self.draw_filters()
        if not self.mods:
            empty = tr("st_no_match") if (self.listing and self.source is not None) else tr("mods_empty")
            self.text(empty, self.f_small, GREY, 455, 200)
        self.draw_cards(self.mods, lambda it: it.get("_idRow") in self.selected)
        self.button(CAT_PREV, tr("btn_prev"), BLACK, WHITE)
        self.button(CAT_NEXT, tr("btn_next"), BLACK, WHITE)
        self.button(CAT_PICK, tr("btn_download_selected", n=len(self.selected)), self.accent, BLACK)
        self.button(CAT_ALL, tr("btn_download_page"), BLACK, WHITE)
        self.draw_dropdown()

    def draw_filters(self):
        f = self.filters
        self.chip(CHIP_CAT, f"{tr('flt_category')}: {f['cat'] or tr('flt_all')}", bool(f["cat"]))
        self.chip(CHIP_SORT, f"{tr('flt_sort')}: {tr('sort_' + f['sort'])}", f["sort"] != "default")
        self.chip(CHIP_HIDE, f"{tr('flt_hide')}: {tr('on') if f['hide'] else tr('off')}", f["hide"])
        self.chip(CHIP_RESET, tr("flt_reset"), False)

    def chip(self, rect, label, active):
        pygame.draw.rect(self.screen, CHIP_BG, rect)
        pygame.draw.rect(self.screen, self.accent if active else GREY, rect, 2)
        color = self.accent if active else WHITE
        img = self.fit_font(label, 22, rect.w - 14).render(label, True, color)
        self.screen.blit(img, img.get_rect(center=rect.center))

    def draw_dropdown(self):
        dd = self.dropdown
        if not dd:
            return
        box = self.dd_box()
        pygame.draw.rect(self.screen, CHIP_BG, box)
        pygame.draw.rect(self.screen, self.accent, box, 2)
        mouse = pygame.mouse.get_pos()
        current = self.filters[dd["key"]]
        for i, (value, label) in enumerate(dd["items"][dd["scroll"]:dd["scroll"] + DD_ROWS]):
            row = pygame.Rect(box.x + 2, box.y + 2 + i * DD_ROW, box.w - 4, DD_ROW)
            hot = row.collidepoint(mouse)
            if hot:
                pygame.draw.rect(self.screen, self.accent, row)
            color = BLACK if hot else (self.accent if value == current else WHITE)
            img = self.fit_font(label, 22, row.w - 14).render(label, True, color)
            self.screen.blit(img, (row.x + 8, row.centery - img.get_height() // 2))

    def draw_manage(self):
        self.panel(*PANEL)
        self.text(tr("manage_title", n=len(self.man_items)), self.f_body, self.accent, 455, 44)
        if not self.man_items:
            self.text(tr("manage_empty"), self.f_small, GREY, 455, 200)
        start = self.man_page * PER_PAGE
        self.draw_cards(self.man_items[start:start + PER_PAGE], lambda it: it["path"] in self.man_sel,
                        picture=self.draw_installed_picture)
        self.button(MAN_BACK, tr("btn_back"), BLACK, WHITE)
        self.button(MAN_PREV, tr("btn_prev"), BLACK, WHITE)
        self.button(MAN_NEXT, tr("btn_next"), BLACK, WHITE)
        self.button(MAN_TOGGLE, tr("btn_on_off"), self.accent, BLACK)
        self.button(MAN_DELETE, tr("btn_confirm_delete") if self.delete_armed else tr("btn_delete"), RED, WHITE)

    def draw_cards(self, items, is_selected, picture=None):
        for i, it in enumerate(items):
            r = self.reveal(i)
            x = GRID_X + (i % 3) * (CARD_W + GAP_X)
            y = GRID_Y + (i // 3) * (CARD_H + GAP_Y) + round((1 - r) * 14)
            sel, off = is_selected(it), bool(it.get("off"))
            s = self.ease(("sel", it.get("_idRow") or it.get("path")), 1.0 if sel else 0.0, 14.0)
            pygame.draw.rect(self.screen, mix(CARD_BG, self.accent, s), (x, y, CARD_W, CARD_H))
            rect = pygame.Rect(x + 6, y + 8, COVER_W, COVER_H)
            if picture:
                picture(it, rect)
            else:
                self.draw_cover(cover_url(it), rect)
            name = it.get("name") or it.get("_sName") or "???"
            if off:
                name = tr("off_tag") + name
            color = mix(GREY if off else WHITE, BLACK, s)
            self.draw_wrapped(name[:70], self.f_tiny, color, x + 110, y + 8, CARD_W - 118, 3)
            if r < 1:                         
                shade = pygame.Surface((CARD_W, CARD_H))
                shade.fill(BLACK)
                shade.set_alpha(round((1 - r) * 255))
                self.screen.blit(shade, (x, y))

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

    def draw_wrapped(self, text, font, color, x, y, width, max_lines, line_h=20):
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
            self.text(ln, font, color, x, y + i * line_h)

    def draw_search(self):
        r = SEARCH_RECT
        pygame.draw.rect(self.screen, CHIP_BG, r)
        pygame.draw.rect(self.screen, self.accent if self.editing else GREY, r, 2)
        if self.query or self.editing:
            self.text((self.query + ("|" if self.editing else ""))[-60:], self.f_small, WHITE, r.x + 10, r.y + 11)
        else:
            self.text(tr("search_hint"), self.f_small, GREY, r.x + 10, r.y + 11)

    def draw_opts(self):
        self.panel(*OPT_PANEL)
        self.text(tr("opt_title"), self.f_head, WHITE, 455, OPT_Y["head_launcher"])
        self.text(tr("opt_game_folder"), self.f_body, WHITE, 444, OPT_Y["folder"])
        browse_x = 444 + self.f_body.size(tr("opt_game_folder") + " ")[0] + 20
        self.text(tr("opt_browse"), self.f_body, self.accent, browse_x, OPT_Y["folder"])
        path = self.cfg["game_dir"]
        if not path:
            self.text(tr("opt_no_folder"), self.f_small, GREY, 444, OPT_Y["path"])
        else:
            shown = path if len(path) <= 70 else "..." + path[-67:]
            self.text(shown, self.f_small, GREEN if self.exe else RED, 444, OPT_Y["path"])
        self.opt_row(OPT_Y["lang"], tr("opt_language"), dict(LANGUAGES)[LANG], self.accent)
        self.text(tr("opt_sound"), self.f_head, WHITE, 455, OPT_Y["head_sfx"])
        for label_key, key, y in TOGGLES:
            on = self.cfg[key]
            t = self.ease(("tog", key), 1.0 if on else 0.0, 14.0)
            self.opt_row(y, tr(label_key), tr("on") if on else tr("off"), mix(GREY, self.accent, t))
        self.text(tr("opt_custom"), self.f_head, WHITE, 455, OPT_Y["head_custom"])
        name = tr(dict(ACCENTS).get(self.cfg["accent"], "acc_custom"))
        self.opt_row(OPT_Y["color"], tr("opt_color"), f"#{self.cfg['accent']} ({name})", self.accent)

    def opt_row(self, y, label, value, value_color):
        label += ": "
        font = self.fit_font(label + value, 38, 740)
        self.text(label, font, WHITE, 452, y)
        self.text(value, font, value_color, 452 + font.size(label)[0], y)

    def best_click(self):
        """On MODS a click toggles the mod; on any other menu it opens MODS with the mod selected."""
        rec = self.best
        self.editing = False
        if self.tab == "mods":
            if rec["_idRow"] in self.selected:
                del self.selected[rec["_idRow"]]
            else:
                self.selected[rec["_idRow"]] = rec
        else:
            self.selected[rec["_idRow"]] = rec
            self.go_tab("mods")
        self.play("select")

    def maybe_load_best(self):
        """Loads the best mod of today; it is refreshed after 15 minutes."""
        fresh = time.time() - self.best_t0 < 15 * 60
        if self.best_state == "loading" or (fresh and self.best_state != "idle"):
            return
        self.best_state, self.best_t0 = "loading", time.time()

        def job():
            try:
                rec = fetch_best_today()
            except Exception:
                self.jobs.put(lambda: self.best_ready(None, failed=True))
                return
            self.jobs.put(lambda: self.best_ready(rec))

        threading.Thread(target=job, daemon=True).start()

    def best_ready(self, rec, failed=False):
        self.best = rec
        self.best_state = "error" if failed else ("ready" if rec else "empty")

    def fetch_banner(self, url):
        key = ("banner", url)
        if url in self.banners or key in self.loading:
            return
        self.loading.add(key)

        def job():
            try:
                data = get_bytes(url)
            except Exception:
                data = None
            self.jobs.put(lambda: self.banner_ready(url, data))

        threading.Thread(target=job, daemon=True).start()

    def banner_ready(self, url, data):
        self.loading.discard(("banner", url))
        try:
            ext = os.path.splitext(urllib.parse.urlparse(url).path)[1][1:].lower() or "jpg"
            img = pygame.image.load(io.BytesIO(data), "banner." + ext).convert()
            self.banners[url] = fit_cover(img, BEST_W, BEST_IMG_H)
        except Exception:
            self.banners[url] = False

    def draw_best(self):
        box = BEST_RECT
        pygame.draw.rect(self.screen, CHIP_BG, box)
        ready = self.best_state == "ready"
        sel = ready and self.best["_idRow"] in self.selected
        if ready:
            url = self.best.get("banner")
            img = self.banners.get(url) if url else None
            if img:
                self.screen.blit(img, box.topleft)
            else:
                pygame.draw.rect(self.screen, (40, 32, 18), (box.x, box.y, BEST_W, BEST_IMG_H))
                if url:
                    self.fetch_banner(url)
            tag = self.fit_font(tr("best_title"), 22, BEST_W - 40).render(tr("best_title"), True, BLACK)
            tag_box = pygame.Rect(box.x + 8, box.y + 8, tag.get_width() + 16, tag.get_height() + 6)
            pygame.draw.rect(self.screen, self.accent, tag_box)
            self.screen.blit(tag, tag.get_rect(center=tag_box.center))
            self.draw_wrapped(self.best["_sName"], self.f_small, WHITE, box.x + 10,
                              box.y + BEST_IMG_H + 8, BEST_W - 20, 2, line_h=26)
            self.text(tr("best_likes", n=self.best.get("likes", 0)), self.f_tiny, GREY,
                      box.x + 10, box.bottom - 24)
        else:
            key = {"idle": "best_loading", "loading": "best_loading", "error": "best_error"}.get(
                self.best_state, "best_none")
            self.text(tr(key), self.f_small, GREY, box.x + 10, box.y + 10)
        pygame.draw.rect(self.screen, self.accent if sel else GREY, box, 3 if sel else 1)

    def text(self, s, font, color, x, y, alpha=255):
        if s:
            img = font.render(s, True, color)
            if alpha < 255:
                img.set_alpha(alpha)
            self.screen.blit(img, (x, y))

    def panel(self, x, y, w, h):
        p = pygame.Surface((w, h), pygame.SRCALPHA)
        p.fill((0, 0, 0, 150))
        self.screen.blit(p, (x, y))

    def button(self, rect, label, bg, fg):
        pygame.draw.rect(self.screen, bg, rect)
        img = self.fit_font(label, 22, rect.w - 12).render(label, True, fg)
        self.screen.blit(img, img.get_rect(center=rect.center))

    def run(self):
        clock = pygame.time.Clock()
        while self.running:
            self.dt = min(clock.tick(60) / 1000, 0.05)
            self.maybe_load_best()
            for e in pygame.event.get():
                self.on_event(e)
            while not self.jobs.empty():
                self.jobs.get()()
            self.draw()
            pygame.display.flip()
        pygame.quit()


if __name__ == "__main__":
    missing = missing_assets()
    if missing:
        print("These files are missing from the assets folder (" + ASSETS + "):", file=sys.stderr)
        for name in missing:
            print("  " + name, file=sys.stderr)
        sys.exit(1)
    App().run()
