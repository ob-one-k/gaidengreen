#!/usr/bin/env python3
"""
fateful_encounter.py — Hoenn Location & Encounter Navigator

Browse every map in the game organized by story chapter.
For each location view:
  - Wild encounter tables (Land / Surf / Fishing / Rock Smash)
  - Trainer cards with full party — click a card to open a party_god-style team popup
  - Items on the ground (balls, hidden items, NPC gifts, in-game trades)
  - Sub-locations: gyms, buildings, caves, multi-floor dungeons

Includes a global search bar that searches across all data types.

Usage:
    python fateful_encounter.py
"""

import os
import re
import sys
import json

_HERE = os.path.dirname(os.path.abspath(__file__))
_LIB  = os.path.join(_HERE, "lib")
if _LIB not in sys.path:
    sys.path.insert(0, _LIB)

from decomp_data import (
    ROOT, DARK_STYLE, TYPE_HEX, GEN_HEX, ITEM_ICONS, TRAINER_PICS,
    find_sprite_for_key, make_transparent_pixmap, make_shiny_pixmap,
    load_all_pokemon, load_map_encounters, load_wild_encounters,
    load_learnsets, load_ability_info, species_to_learnset_key, move_lookup,
    load_items, item_lookup, _map_name_to_label, parse_trainers_party,
    PARTY_FILE, MAPS_DATA_DIR,
)

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QDialog,
    QVBoxLayout, QHBoxLayout, QGridLayout, QSplitter,
    QTreeWidget, QTreeWidgetItem, QTabWidget,
    QLabel, QPushButton, QFrame, QScrollArea,
    QSizePolicy, QLineEdit, QStackedWidget, QProgressBar,
)
from PyQt5.QtCore import Qt, QSize, QPoint, QTimer
from PyQt5.QtGui  import (
    QPixmap, QColor, QPainter, QFont, QBrush, QPen, QIcon,
)

# ══════════════════════════════════════════════════════════════════════════════
# ROUTING — all towns + dungeons by chapter
# ══════════════════════════════════════════════════════════════════════════════
ROUTING = [
    ("Ch. 1 — First Steps", [
        "MAP_LITTLEROOT_TOWN",
        "MAP_ROUTE101",
        "MAP_OLDALE_TOWN",
        "MAP_ROUTE103",
        "MAP_ROUTE102",
        "MAP_PETALBURG_CITY",
        "MAP_ROUTE104",
        "MAP_PETALBURG_WOODS",
    ]),
    ("Ch. 2 — Rustboro  (Gym 1)", [
        "MAP_RUSTBORO_CITY",
        "MAP_ROUTE116",
        "MAP_RUSTURF_TUNNEL",
    ]),
    ("Ch. 3 — Dewford  (Gym 2)", [
        "MAP_ROUTE105",
        "MAP_ROUTE106",
        "MAP_ROUTE107",
        "MAP_ROUTE108",
        "MAP_ROUTE109",
        "MAP_DEWFORD_TOWN",
        "MAP_GRANITE_CAVE_1F",
        "MAP_GRANITE_CAVE_B1F",
        "MAP_GRANITE_CAVE_B2F",
        "MAP_GRANITE_CAVE_STEVENS_ROOM",
    ]),
    ("Ch. 4 — Mauville  (Gym 3)", [
        "MAP_SLATEPORT_CITY",
        "MAP_ROUTE110",
        "MAP_MAUVILLE_CITY",
        "MAP_ROUTE117",
        "MAP_VERDANTURF_TOWN",
        "MAP_NEW_MAUVILLE_ENTRANCE",
        "MAP_NEW_MAUVILLE_INSIDE",
    ]),
    ("Ch. 5 — Fallarbor / Lavaridge  (Gym 4)", [
        "MAP_ROUTE111",
        "MAP_ROUTE112",
        "MAP_FIERY_PATH",
        "MAP_JAGGED_PASS",
        "MAP_ROUTE113",
        "MAP_FALLARBOR_TOWN",
        "MAP_ROUTE114",
        "MAP_METEOR_FALLS_1F_1R",
        "MAP_METEOR_FALLS_1F_2R",
        "MAP_METEOR_FALLS_B1F_1R",
        "MAP_METEOR_FALLS_B1F_2R",
        "MAP_MAGMA_HIDEOUT_1F",
        "MAP_MAGMA_HIDEOUT_2F_1R",
        "MAP_MAGMA_HIDEOUT_2F_2R",
        "MAP_MAGMA_HIDEOUT_2F_3R",
        "MAP_MAGMA_HIDEOUT_3F_1R",
        "MAP_MAGMA_HIDEOUT_3F_2R",
        "MAP_MAGMA_HIDEOUT_3F_3R",
        "MAP_MAGMA_HIDEOUT_4F",
        "MAP_ROUTE115",
        "MAP_LAVARIDGE_TOWN",
        "MAP_MIRAGE_TOWER_1F",
        "MAP_MIRAGE_TOWER_2F",
        "MAP_MIRAGE_TOWER_3F",
        "MAP_MIRAGE_TOWER_4F",
    ]),
    ("Ch. 6 — Petalburg Revisited  (Gym 5)", [
        "MAP_PETALBURG_CITY",
    ]),
    ("Ch. 7 — Fortree  (Gym 6)", [
        "MAP_ROUTE118",
        "MAP_ROUTE119",
        "MAP_FORTREE_CITY",
        "MAP_ROUTE120",
        "MAP_ROUTE121",
    ]),
    ("Ch. 8 — Lilycove & Mt. Pyre", [
        "MAP_LILYCOVE_CITY",
        "MAP_ROUTE122",
        "MAP_MT_PYRE_1F",
        "MAP_MT_PYRE_2F",
        "MAP_MT_PYRE_3F",
        "MAP_MT_PYRE_4F",
        "MAP_MT_PYRE_5F",
        "MAP_MT_PYRE_6F",
        "MAP_MT_PYRE_EXTERIOR",
        "MAP_MT_PYRE_SUMMIT",
        "MAP_ROUTE123",
        "MAP_ABANDONED_SHIP_ROOMS_B1F",
        "MAP_ABANDONED_SHIP_HIDDEN_FLOOR_CORRIDORS",
    ]),
    ("Ch. 9 — Mossdeep  (Gym 7)", [
        "MAP_ROUTE124",
        "MAP_MOSSDEEP_CITY",
        "MAP_SHOAL_CAVE_LOW_TIDE_ENTRANCE_ROOM",
        "MAP_SHOAL_CAVE_LOW_TIDE_INNER_ROOM",
        "MAP_SHOAL_CAVE_LOW_TIDE_STAIRS_ROOM",
        "MAP_SHOAL_CAVE_LOW_TIDE_LOWER_ROOM",
        "MAP_SHOAL_CAVE_LOW_TIDE_ICE_ROOM",
        "MAP_ROUTE125",
    ]),
    ("Ch. 10 — Sootopolis  (Gym 8)", [
        "MAP_ROUTE126",
        "MAP_SOOTOPOLIS_CITY",
        "MAP_UNDERWATER_ROUTE124",
        "MAP_UNDERWATER_ROUTE126",
        "MAP_SEAFLOOR_CAVERN_ENTRANCE",
        "MAP_SEAFLOOR_CAVERN_ROOM1",
        "MAP_SEAFLOOR_CAVERN_ROOM2",
        "MAP_SEAFLOOR_CAVERN_ROOM3",
        "MAP_SEAFLOOR_CAVERN_ROOM4",
        "MAP_SEAFLOOR_CAVERN_ROOM5",
        "MAP_SEAFLOOR_CAVERN_ROOM6",
        "MAP_SEAFLOOR_CAVERN_ROOM7",
        "MAP_SEAFLOOR_CAVERN_ROOM8",
        "MAP_CAVE_OF_ORIGIN_ENTRANCE",
        "MAP_CAVE_OF_ORIGIN_1F",
        "MAP_CAVE_OF_ORIGIN_UNUSED_RUBY_SAPPHIRE_MAP1",
        "MAP_CAVE_OF_ORIGIN_UNUSED_RUBY_SAPPHIRE_MAP2",
        "MAP_CAVE_OF_ORIGIN_UNUSED_RUBY_SAPPHIRE_MAP3",
    ]),
    ("Ch. 11 — Sea Routes", [
        "MAP_ROUTE127",
        "MAP_ROUTE128",
        "MAP_ROUTE129",
        "MAP_ROUTE130",
        "MAP_ROUTE131",
        "MAP_ROUTE132",
        "MAP_ROUTE133",
        "MAP_ROUTE134",
        "MAP_PACIFIDLOG_TOWN",
        "MAP_EVER_GRANDE_CITY",
    ]),
    ("Ch. 12 — Victory Road", [
        "MAP_VICTORY_ROAD_1F",
        "MAP_VICTORY_ROAD_B1F",
        "MAP_VICTORY_ROAD_B2F",
    ]),
    ("Post-Game", [
        "MAP_SAFARI_ZONE_SOUTH",
        "MAP_SAFARI_ZONE_SOUTHWEST",
        "MAP_SAFARI_ZONE_NORTH",
        "MAP_SAFARI_ZONE_NORTHWEST",
        "MAP_SAFARI_ZONE_SOUTHEAST",
        "MAP_SAFARI_ZONE_NORTHEAST",
        "MAP_SKY_PILLAR_1F",
        "MAP_SKY_PILLAR_3F",
        "MAP_SKY_PILLAR_5F",
        "MAP_ARTISAN_CAVE_B1F",
        "MAP_ARTISAN_CAVE_1F",
        "MAP_DESERT_UNDERPASS",
        "MAP_ALTERING_CAVE",
        "MAP_METEOR_FALLS_STEVENS_CAVE",
    ]),
]

# ══════════════════════════════════════════════════════════════════════════════
# Encounter table constants
# ══════════════════════════════════════════════════════════════════════════════
TABLE_ORDER = [
    ("land_mons",        "Land"),
    ("water_mons",       "Surf"),
    ("rock_smash_mons",  "Rock Smash"),
    ("fishing_mons",     "Fishing"),
]

ROD_ORDER = [
    ("old_rod_mons",    "Old Rod"),
    ("good_rod_mons",   "Good Rod"),
    ("super_rod_mons",  "Super Rod"),
]

TABLE_COLOR = {
    "land_mons":        "#a6e3a1",
    "water_mons":       "#89b4fa",
    "rock_smash_mons":  "#fab387",
    "fishing_mons":     "#89dceb",
}

# ══════════════════════════════════════════════════════════════════════════════
# Path constants
# ══════════════════════════════════════════════════════════════════════════════
MAPS_DIR        = MAPS_DATA_DIR
MAP_GROUPS_FILE = os.path.join(ROOT, 'data', 'maps', 'map_groups.json')
TRADE_H_FILE    = os.path.join(ROOT, 'src', 'data', 'trade.h')

# ══════════════════════════════════════════════════════════════════════════════
# Module caches
# ══════════════════════════════════════════════════════════════════════════════
_DIR_BY_KEY:     dict = {}
_KEY_BY_DIR:     dict = {}
_MAP_JSON_CACHE: dict = {}
_SUB_MAPS:       dict = {}
_MAP_GROUPS:     dict = {}
_TRAINER_DB:     dict = {}
_TRADE_DETAILS:  dict = {}
_SEARCH_INDEX:   dict = {}
_data_loaded = False

# ══════════════════════════════════════════════════════════════════════════════
# Data loaders
# ══════════════════════════════════════════════════════════════════════════════

def _safe_read(path: str) -> str:
    """Read a file, returning empty string on any error."""
    try:
        with open(path, 'r', encoding='utf-8', errors='replace') as f:
            return f.read()
    except OSError:
        return ''


def _init_map_index():
    """Populate _DIR_BY_KEY, _KEY_BY_DIR, and _MAP_JSON_CACHE."""
    global _DIR_BY_KEY, _KEY_BY_DIR, _MAP_JSON_CACHE
    if _DIR_BY_KEY:
        return
    if not os.path.isdir(MAPS_DIR):
        return
    for entry in sorted(os.listdir(MAPS_DIR)):
        map_json_path = os.path.join(MAPS_DIR, entry, 'map.json')
        if not os.path.isfile(map_json_path):
            continue
        try:
            with open(map_json_path, 'r', encoding='utf-8', errors='replace') as f:
                data = json.load(f)
        except Exception:
            continue
        map_id = data.get('id', '')
        if not map_id:
            continue
        _DIR_BY_KEY[map_id]    = entry
        _KEY_BY_DIR[entry]     = map_id
        _MAP_JSON_CACHE[entry] = data


def _load_map_groups():
    """Populate _MAP_GROUPS and _SUB_MAPS."""
    global _MAP_GROUPS, _SUB_MAPS
    if _MAP_GROUPS:
        return
    if not os.path.isfile(MAP_GROUPS_FILE):
        return
    try:
        with open(MAP_GROUPS_FILE, 'r', encoding='utf-8', errors='replace') as f:
            raw = json.load(f)
    except Exception:
        return

    for group_name, members in raw.items():
        if group_name == 'group_order':
            continue
        _MAP_GROUPS[group_name] = members

        # Determine parent short_name for indoor groups
        parent = None
        if group_name.startswith('gMapGroup_Indoor'):
            suffix = group_name[len('gMapGroup_Indoor'):]
            if suffix:
                candidate = suffix
                for short in _DIR_BY_KEY.values():
                    if short.lower().startswith(suffix.lower()):
                        if short == suffix or (len(short) > len(suffix) and
                                               short[len(suffix):][0].isupper()):
                            parent = short
                            break
                if not parent:
                    for short in _DIR_BY_KEY.values():
                        if short.lower() == suffix.lower():
                            parent = short
                            break
                if not parent:
                    for short in _DIR_BY_KEY.values():
                        if short == suffix:
                            parent = short
                            break
        elif group_name == 'gMapGroup_Dungeons':
            for member in members:
                m = re.match(r'^([A-Za-z]+(?:[A-Z][a-z]+)*)', member)
                prefix = m.group(1) if m else member
                for short in _DIR_BY_KEY.values():
                    if short == prefix or short.startswith(prefix + '_'):
                        parent = prefix
                        break
                if parent:
                    if parent not in _SUB_MAPS:
                        _SUB_MAPS[parent] = []
                    if member not in _SUB_MAPS[parent]:
                        _SUB_MAPS[parent].append(member)
            continue

        if parent:
            if parent not in _SUB_MAPS:
                _SUB_MAPS[parent] = []
            for member in members:
                if member not in _SUB_MAPS[parent]:
                    _SUB_MAPS[parent].append(member)


def _get_map_json(short_name: str) -> dict:
    """Return cached map.json dict for short_name, or {}."""
    _init_map_index()
    if short_name not in _MAP_JSON_CACHE:
        path = os.path.join(MAPS_DIR, short_name, 'map.json')
        if os.path.isfile(path):
            try:
                with open(path, 'r', encoding='utf-8', errors='replace') as f:
                    _MAP_JSON_CACHE[short_name] = json.load(f)
            except Exception:
                _MAP_JSON_CACHE[short_name] = {}
        else:
            _MAP_JSON_CACHE[short_name] = {}
    return _MAP_JSON_CACHE.get(short_name, {})


def _load_map_items(short_name: str) -> dict:
    """
    Parse map.json for item balls and hidden items.
    Returns {'balls': [...], 'hidden': [...]}
    Each ball: {'item': 'ITEM_X', 'flag': '...', 'x': n, 'y': n}
    Each hidden: {'item': 'ITEM_X', 'flag': '...'}
    """
    data = _get_map_json(short_name)
    balls  = []
    hidden = []
    for evt in data.get('object_events', []):
        if evt.get('graphics_id', '') == 'OBJ_EVENT_GFX_ITEM_BALL':
            item_key = evt.get('trainer_sight_or_berry_tree_id', '')
            if item_key and item_key != '0':
                balls.append({
                    'item': item_key,
                    'flag': evt.get('flag', ''),
                    'x':    evt.get('x', 0),
                    'y':    evt.get('y', 0),
                })
    for evt in data.get('bg_events', []):
        if evt.get('type') == 'hidden_item':
            item_key = evt.get('item', '')
            if item_key:
                hidden.append({
                    'item': item_key,
                    'flag': evt.get('flag', ''),
                })
    return {'balls': balls, 'hidden': hidden}


def _load_script_data(short_name: str) -> dict:
    """
    Parse scripts.inc for trainer battles, giveitem calls, and trade references.
    Returns {
        'trainers': ['TRAINER_KEY', ...],
        'gifts':    [{'item': 'ITEM_X', 'qty': 1, 'script': 'label', 'flag': '...'}],
        'trades':   ['INGAME_TRADE_X', ...],
    }
    """
    scripts_path = os.path.join(MAPS_DIR, short_name, 'scripts.inc')
    content = _safe_read(scripts_path)
    if not content:
        return {'trainers': [], 'gifts': [], 'trades': []}

    # Trainers
    trainer_pat = re.compile(r'trainerbattle\w*\s+(TRAINER_\w+)')
    trainers = list(dict.fromkeys(m.group(1) for m in trainer_pat.finditer(content)))

    # Gifts (giveitem command)
    give_pat2  = re.compile(r'giveitem\s+(ITEM_\w+)(?:\s*,\s*(\d+))?')
    label_pat  = re.compile(r'^(\w+)::')
    flag_pat   = re.compile(r'setflag\s+(FLAG_\w+)')

    gifts = []
    lines = content.split('\n')
    current_label = ''
    for i, line in enumerate(lines):
        lm = label_pat.match(line)
        if lm:
            current_label = lm.group(1)
        gm = give_pat2.search(line)
        if gm:
            item_key = gm.group(1)
            qty_str  = gm.group(2)
            qty      = int(qty_str) if qty_str else 1
            flag = ''
            for lookahead in lines[i:i+8]:
                fm = flag_pat.search(lookahead)
                if fm:
                    flag = fm.group(1)
                    break
            gifts.append({
                'item':   item_key,
                'qty':    qty,
                'script': current_label,
                'flag':   flag,
            })

    # Trades
    trade_pat = re.compile(r'(INGAME_TRADE_\w+)')
    trades = list(dict.fromkeys(m.group(1) for m in trade_pat.finditer(content)))

    return {'trainers': trainers, 'gifts': gifts, 'trades': trades}


def _load_trade_details() -> dict:
    """
    Parse trade.h for sIngameTrades[] array.
    Returns {trade_id: {'id', 'species', 'nickname', 'held_item', 'ot_name', 'requested'}}
    """
    global _TRADE_DETAILS
    if _TRADE_DETAILS:
        return _TRADE_DETAILS

    content = _safe_read(TRADE_H_FILE)
    result = {}

    if content:
        block_pat = re.compile(
            r'\[(?P<id>INGAME_TRADE_\w+)\]\s*=\s*\{(?P<body>[^}]+)\}',
            re.DOTALL
        )
        field_pat = re.compile(r'\.(\w+)\s*=\s*(?:_\("([^"]*)"\)|(\w+))')

        for bm in block_pat.finditer(content):
            trade_id = bm.group('id')
            body     = bm.group('body')
            entry    = {'id': trade_id, 'species': '', 'nickname': '', 'held_item': '',
                        'ot_name': '', 'requested': ''}
            for fm in field_pat.finditer(body):
                fname  = fm.group(1)
                fstr   = fm.group(2)
                fident = fm.group(3)
                if fname == 'nickname':
                    entry['nickname'] = fstr or fident or ''
                elif fname == 'otName':
                    entry['ot_name'] = fstr or fident or ''
                elif fname == 'species':
                    sp = fident or ''
                    if sp.startswith('SPECIES_'):
                        sp = sp[8:]
                    entry['species'] = sp
                elif fname == 'requestedSpecies':
                    sp = fident or ''
                    if sp.startswith('SPECIES_'):
                        sp = sp[8:]
                    entry['requested'] = sp
                elif fname == 'heldItem':
                    entry['held_item'] = fident or ''
            result[trade_id] = entry

    _TRADE_DETAILS = result
    return result


def _load_trainer_db() -> dict:
    """Return {TRAINER_KEY: Trainer} for all trainers."""
    global _TRAINER_DB
    if _TRAINER_DB:
        return _TRAINER_DB
    try:
        _, trainers_list = parse_trainers_party()
        _TRAINER_DB = {t.key.upper(): t for t in trainers_list}
    except Exception as e:
        print(f"Warning: could not load trainer DB: {e}")
        _TRAINER_DB = {}
    return _TRAINER_DB


def _ensure_data_loaded():
    """Load all shared databases on first call."""
    global _data_loaded
    if _data_loaded:
        return
    _init_map_index()
    _load_map_groups()
    _load_trade_details()
    _load_trainer_db()
    _data_loaded = True


# ══════════════════════════════════════════════════════════════════════════════
# Display helpers
# ══════════════════════════════════════════════════════════════════════════════

_sprite_cache: dict = {}

def _get_sprite(species_key: str, size: int = 48) -> QPixmap:
    """Return a scaled, transparent QPixmap for the given SPECIES_ key."""
    cache_key = (species_key, size)
    if cache_key in _sprite_cache:
        return _sprite_cache[cache_key]
    raw_key = species_key[8:] if species_key.upper().startswith("SPECIES_") else species_key
    front, _ = find_sprite_for_key(raw_key)
    pix = QPixmap()
    if front and os.path.isfile(front):
        raw = QPixmap(front)
        if not raw.isNull():
            if raw.height() > raw.width():
                raw = raw.copy(0, 0, raw.width(), raw.width())
            raw = make_transparent_pixmap(raw)
            pix = raw.scaled(size, size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
    _sprite_cache[cache_key] = pix
    return pix


def _species_display(species_key: str) -> str:
    """SPECIES_RATTATA → 'Rattata'"""
    s = species_key
    if s.upper().startswith("SPECIES_"):
        s = s[8:]
    return s.replace("_", " ").title()


def _subloc_display(short_name: str, parent_name: str) -> str:
    """'RustboroCity_House1' → 'House 1', 'GraniteCave_B1F' → 'B1F'"""
    if short_name == parent_name:
        return 'Main Area'
    if short_name.startswith(parent_name + '_'):
        suffix = short_name[len(parent_name) + 1:]
    else:
        suffix = short_name
    suffix = re.sub(r'([A-Za-z])(\d)', r'\1 \2', suffix)
    suffix = re.sub(r'([a-z])([A-Z])', r'\1 \2', suffix)
    suffix = suffix.replace('_', ' ')
    return suffix


def _item_display(item_key: str) -> str:
    """ITEM_POTION → 'Potion'"""
    tup = item_lookup(item_key)
    if tup:
        return tup[1]
    if item_key.startswith('ITEM_'):
        return item_key[5:].replace('_', ' ').title()
    return item_key.replace('_', ' ').title()


def _item_icon_pixmap(item_key: str, size: int = 28) -> QPixmap:
    """Return a QPixmap for the item icon, or a blank pixmap if not found."""
    tup = item_lookup(item_key)
    pix = QPixmap()
    if tup and tup[2] and os.path.isfile(tup[2]):
        raw = QPixmap(tup[2])
        if not raw.isNull():
            pix = raw.scaled(size, size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
    return pix


def _trainer_pic_pixmap(pic_name: str, size: int = 48) -> QPixmap:
    """Find and return a trainer sprite pixmap."""
    pix = QPixmap()
    if not pic_name:
        return pix
    candidates = [
        os.path.join(TRAINER_PICS, pic_name, 'front.png'),
        os.path.join(TRAINER_PICS, pic_name.lower(), 'front.png'),
        os.path.join(TRAINER_PICS, pic_name + '.png'),
    ]
    for p in candidates:
        if os.path.isfile(p):
            raw = QPixmap(p)
            if not raw.isNull():
                raw = make_transparent_pixmap(raw)
                pix = raw.scaled(size, size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                return pix
    return pix


def _map_key_to_short(map_key: str) -> str:
    """MAP_ROUTE101 → short_name or '' if not found."""
    _init_map_index()
    return _DIR_BY_KEY.get(map_key, '')


def _make_badge(text: str, color: str) -> QLabel:
    """Create a colored badge label."""
    lbl = QLabel(text)
    lbl.setAlignment(Qt.AlignCenter)
    lbl.setStyleSheet(
        f"background:{color}; color:#1e1e2e; font-weight:bold; font-size:10px; "
        "border-radius:4px; padding:2px 7px;"
    )
    return lbl


def _sep_line() -> QFrame:
    """Thin 1px horizontal separator."""
    f = QFrame()
    f.setFrameShape(QFrame.HLine)
    f.setFixedHeight(1)
    f.setStyleSheet("background:#313244; border:none;")
    return f


def _section_header(text: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setObjectName("heading")
    return lbl


# ══════════════════════════════════════════════════════════════════════════════
# POKEMON DETAIL DIALOG
# ══════════════════════════════════════════════════════════════════════════════
class PokemonDetailDialog(QDialog):
    """Frameless detail popup shown when clicking a Pokémon row."""

    def __init__(self, species_key: str, pokemon_db: dict, ability_db: dict,
                 learnset_db: dict, wild_db: dict, parent=None):
        super().__init__(parent, Qt.FramelessWindowHint | Qt.Popup)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setModal(False)
        self._drag_pos = None

        sp = pokemon_db.get(species_key.upper().lstrip("SPECIES_") if not species_key.upper().startswith("SPECIES_") else species_key[8:].upper())
        if sp is None:
            lower = (species_key[8:] if species_key.upper().startswith("SPECIES_") else species_key).lower()
            sp = next((v for k, v in pokemon_db.items() if k.lower() == lower), None)

        self._species_key  = species_key
        self._sp           = sp
        self._ability_db   = ability_db
        self._learnset_db  = learnset_db
        self._wild_db      = wild_db
        self._normal_pix   = None
        self._shiny_pix    = None
        self._front_path   = ""
        self._shiny        = False

        self._build_ui()
        self._load_sprite()

    def _build_ui(self):
        sp   = self._sp
        name = _species_display(self._species_key) if not sp else sp.name

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        card = QFrame()
        card.setObjectName("dlg_outer")
        card.setStyleSheet(
            "#dlg_outer { background:#1e1e2e; border:1px solid #45475a; border-radius:14px; }"
        )
        card_lay = QVBoxLayout(card)
        card_lay.setContentsMargins(0, 0, 0, 0)
        card_lay.setSpacing(0)
        outer.addWidget(card)

        # Title bar
        title_bar = QWidget()
        title_bar.setFixedHeight(38)
        title_bar.setStyleSheet("background:#181825; border-radius:14px 14px 0 0;")
        tb_lay = QHBoxLayout(title_bar)
        tb_lay.setContentsMargins(14, 0, 10, 0)
        lbl = QLabel(name)
        lbl.setObjectName("title")
        lbl.setStyleSheet(
            "color:#cdd6f4; font-weight:bold; font-size:15px; "
            "background:transparent; border:none;"
        )
        tb_lay.addWidget(lbl)
        tb_lay.addStretch()

        self.shiny_btn = QPushButton("Normal")
        self.shiny_btn.setFixedSize(60, 24)
        self.shiny_btn.setStyleSheet(
            "QPushButton { background:#313244; border:1px solid #45475a; border-radius:5px; "
            "color:#cdd6f4; font-size:11px; }"
            "QPushButton:hover { border-color:#89b4fa; }"
        )
        self.shiny_btn.clicked.connect(self._toggle_shiny)
        tb_lay.addWidget(self.shiny_btn)

        close_btn = QPushButton("✕")
        close_btn.setFixedSize(28, 24)
        close_btn.setStyleSheet(
            "QPushButton { background:transparent; border:none; color:#585b70; font-size:14px; }"
            "QPushButton:hover { color:#f38ba8; }"
        )
        close_btn.clicked.connect(self.close)
        tb_lay.addWidget(close_btn)
        card_lay.addWidget(title_bar)

        title_bar.mousePressEvent   = self._on_press
        title_bar.mouseMoveEvent    = self._on_move
        title_bar.mouseReleaseEvent = self._on_release

        # Body
        body = QWidget()
        body.setStyleSheet("background:transparent;")
        body_lay = QHBoxLayout(body)
        body_lay.setContentsMargins(16, 12, 16, 16)
        body_lay.setSpacing(18)
        card_lay.addWidget(body)

        # Left column — sprite + types + gen
        left = QVBoxLayout()
        left.setSpacing(8)
        left.setAlignment(Qt.AlignTop)

        self.sprite_lbl = QLabel()
        self.sprite_lbl.setFixedSize(120, 120)
        self.sprite_lbl.setAlignment(Qt.AlignCenter)
        self.sprite_lbl.setStyleSheet(
            "background:#181825; border-radius:10px; border:1px solid #313244;"
        )
        left.addWidget(self.sprite_lbl)

        # type badges
        types_row = QHBoxLayout()
        types_row.setSpacing(5)
        t1 = (sp.type1 if sp else "")
        t2 = (sp.type2 if sp and sp.type2 else "")
        for t in filter(None, [t1, t2]):
            badge = QLabel(t.title())
            c = TYPE_HEX.get(t.upper(), "#585b70")
            badge.setStyleSheet(
                f"background:{c}; color:#1e1e2e; font-weight:bold; font-size:10px; "
                "border-radius:4px; padding:2px 7px;"
            )
            badge.setAlignment(Qt.AlignCenter)
            types_row.addWidget(badge)
        types_row.addStretch()
        left.addLayout(types_row)

        # gen / bst
        if sp:
            gen_c = GEN_HEX.get(sp.gen, "#a6adc8")
            meta_row = QHBoxLayout()
            meta_row.setSpacing(8)
            gen_lbl = QLabel(f"Gen {sp.gen}")
            gen_lbl.setStyleSheet(
                f"color:{gen_c}; font-size:11px; font-weight:bold; background:transparent;"
            )
            bst_lbl = QLabel(f"BST {sp.bst}")
            bst_lbl.setStyleSheet("color:#a6adc8; font-size:11px; background:transparent;")
            meta_row.addWidget(gen_lbl)
            meta_row.addWidget(bst_lbl)
            meta_row.addStretch()
            left.addLayout(meta_row)

        # catch rate
        if sp and hasattr(sp, "catch_rate") and sp.catch_rate:
            cr_lbl = QLabel(f"Catch rate: {sp.catch_rate}")
            cr_lbl.setStyleSheet("color:#6c7086; font-size:11px; background:transparent;")
            left.addWidget(cr_lbl)

        # abilities
        if sp and sp.abilities:
            ab_head = QLabel("ABILITIES")
            ab_head.setObjectName("heading")
            left.addWidget(ab_head)
            for ab in sp.abilities:
                if not ab:
                    continue
                ab_name  = ab.replace("ABILITY_", "").replace("_", " ").title()
                ab_label = QLabel(f"• {ab_name}")
                ab_label.setStyleSheet(
                    "color:#bac2de; font-size:11px; background:transparent;"
                )
                ab_label.setWordWrap(True)
                left.addWidget(ab_label)

        left.addStretch()
        body_lay.addLayout(left)

        # Sep line
        sep = QFrame()
        sep.setFrameShape(QFrame.VLine)
        sep.setStyleSheet("background:#313244; border:none; max-width:1px; min-width:1px;")
        body_lay.addWidget(sep)

        # Right column — stats + learnset tabs
        right = QVBoxLayout()
        right.setSpacing(6)
        body_lay.addLayout(right)

        # Base stats bars
        if sp:
            stats_head = QLabel("BASE STATS")
            stats_head.setObjectName("heading")
            right.addWidget(stats_head)
            stats = [
                ("HP",  sp.hp,  "#f38ba8"),
                ("Atk", sp.atk, "#fab387"),
                ("Def", sp.def_,"#f9e2af"),
                ("SpA", sp.spa, "#89b4fa"),
                ("SpD", sp.spd, "#a6e3a1"),
                ("Spe", sp.spe, "#cba6f7"),
            ]
            for stat_name, val, color in stats:
                row = QHBoxLayout()
                row.setSpacing(6)
                lbl_s = QLabel(stat_name)
                lbl_s.setFixedWidth(32)
                lbl_s.setStyleSheet(
                    "color:#6c7086; font-size:11px; font-weight:bold; background:transparent;"
                )
                row.addWidget(lbl_s)
                val_lbl = QLabel(str(val))
                val_lbl.setFixedWidth(30)
                val_lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
                val_lbl.setStyleSheet(
                    "color:#cdd6f4; font-size:11px; font-weight:bold; background:transparent;"
                )
                row.addWidget(val_lbl)
                bar_wrap = QWidget()
                bar_wrap.setFixedHeight(10)
                bar_wrap.setMinimumWidth(160)
                bar_wrap.setStyleSheet("background:transparent;")
                bar_wrap._stat_val   = val
                bar_wrap._stat_color = color
                bar_wrap.paintEvent  = lambda ev, bw=bar_wrap: _paint_bar(ev, bw)
                row.addWidget(bar_wrap, 1)
                right.addLayout(row)

        # Wild locations (compact)
        raw_key = (self._species_key[8:] if self._species_key.upper().startswith("SPECIES_")
                   else self._species_key).upper()
        locs = self._wild_db.get(raw_key, [])
        if locs:
            loc_head = QLabel("WILD LOCATIONS")
            loc_head.setObjectName("heading")
            right.addWidget(loc_head)
            shown = locs[:6]
            for (map_lbl, ttype, mnl, mxl, pct) in shown:
                loc_lbl = QLabel(f"  {map_lbl}  ·  {ttype}  Lv.{mnl}–{mxl}  ({pct}%)")
                loc_lbl.setStyleSheet(
                    "color:#6c7086; font-size:11px; background:transparent;"
                )
                right.addWidget(loc_lbl)
            if len(locs) > 6:
                more = QLabel(f"  …and {len(locs)-6} more")
                more.setStyleSheet("color:#45475a; font-size:11px; background:transparent;")
                right.addWidget(more)

        # Learnset (level-up only, compact)
        ls_key = species_to_learnset_key(
            self._species_key[8:] if self._species_key.upper().startswith("SPECIES_") else self._species_key
        )
        learnset = self._learnset_db.get(ls_key, {})
        levelup  = learnset.get("levelup", [])
        if levelup:
            ls_head = QLabel("LEVEL-UP MOVES")
            ls_head.setObjectName("heading")
            right.addWidget(ls_head)
            ls_scroll_area = QScrollArea()
            ls_scroll_area.setWidgetResizable(True)
            ls_scroll_area.setFixedHeight(130)
            ls_scroll_area.setStyleSheet(
                "QScrollArea { background:#181825; border:1px solid #313244; border-radius:6px; }"
            )
            ls_inner = QWidget()
            ls_inner.setStyleSheet("background:transparent;")
            ls_grid  = QGridLayout(ls_inner)
            ls_grid.setContentsMargins(8, 4, 8, 4)
            ls_grid.setSpacing(2)
            for row_i, (lvl, move_key) in enumerate(levelup[:24]):
                info   = move_lookup(move_key) or {}
                mname  = info.get("name", move_key.replace("MOVE_","").replace("_"," ").title())
                mtype  = info.get("type", "")
                tc     = TYPE_HEX.get(mtype.upper(), "#585b70") if mtype else "#585b70"
                lv_lbl = QLabel(f"Lv.{lvl}")
                lv_lbl.setStyleSheet("color:#585b70; font-size:10px; background:transparent;")
                lv_lbl.setFixedWidth(36)
                mv_lbl = QLabel(mname)
                mv_lbl.setStyleSheet("color:#cdd6f4; font-size:10px; background:transparent;")
                mv_lbl.setFixedWidth(120)
                ty_lbl = QLabel(mtype.title() if mtype else "")
                ty_lbl.setStyleSheet(
                    f"background:{tc}; color:#1e1e2e; font-size:9px; font-weight:bold; "
                    "border-radius:3px; padding:1px 4px;"
                )
                ty_lbl.setAlignment(Qt.AlignCenter)
                ty_lbl.setFixedWidth(56)
                ls_grid.addWidget(lv_lbl, row_i, 0)
                ls_grid.addWidget(mv_lbl, row_i, 1)
                ls_grid.addWidget(ty_lbl, row_i, 2)
            ls_scroll_area.setWidget(ls_inner)
            right.addWidget(ls_scroll_area)

        right.addStretch()
        self.setFixedWidth(590)

    def _load_sprite(self):
        raw_key = (
            self._species_key[8:]
            if self._species_key.upper().startswith("SPECIES_")
            else self._species_key
        )
        front, _ = find_sprite_for_key(raw_key)
        self._front_path = front
        if front and os.path.isfile(front):
            raw = QPixmap(front)
            if not raw.isNull():
                if raw.height() > raw.width():
                    raw = raw.copy(0, 0, raw.width(), raw.width())
                raw = make_transparent_pixmap(raw)
                self._normal_pix = raw
                self._render_sprite()

    def _render_sprite(self):
        pix = (self._shiny_pix if (self._shiny and self._shiny_pix) else self._normal_pix)
        if pix:
            self.sprite_lbl.setPixmap(
                pix.scaled(120, 120, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            )

    def _toggle_shiny(self):
        self._shiny = not self._shiny
        self.shiny_btn.setText("Shiny" if self._shiny else "Normal")
        if self._shiny and self._shiny_pix is None and self._normal_pix and self._front_path:
            self._shiny_pix = make_shiny_pixmap(self._front_path, self._normal_pix)
        self._render_sprite()

    def _on_press(self, ev):
        if ev.button() == Qt.LeftButton:
            self._drag_pos = ev.globalPos() - self.frameGeometry().topLeft()

    def _on_move(self, ev):
        if self._drag_pos and ev.buttons() & Qt.LeftButton:
            self.move(ev.globalPos() - self._drag_pos)

    def _on_release(self, _):
        self._drag_pos = None


def _paint_bar(ev, widget):
    p      = QPainter(widget)
    p.setRenderHint(QPainter.Antialiasing)
    val    = getattr(widget, "_stat_val", 0)
    color  = getattr(widget, "_stat_color", "#89b4fa")
    w, h   = widget.width(), widget.height()
    filled = int(w * min(val, 255) / 255)
    p.setPen(Qt.NoPen)
    p.setBrush(QColor("#313244"))
    p.drawRoundedRect(0, 0, w, h, 4, 4)
    if filled > 0:
        p.setBrush(QColor(color))
        p.drawRoundedRect(0, 0, filled, h, 4, 4)
    p.end()


# ══════════════════════════════════════════════════════════════════════════════
# ENCOUNTER ROW WIDGET
# ══════════════════════════════════════════════════════════════════════════════
class EncounterRowWidget(QWidget):
    """Single clickable row representing one Pokémon in an encounter table."""

    def __init__(self, slot: int, species_key: str, min_lvl: int, max_lvl: int,
                 rate: int, pct: int, pokemon_db, ability_db, learnset_db, wild_db,
                 parent=None):
        super().__init__(parent)
        self._species_key = species_key
        self._pokemon_db  = pokemon_db
        self._ability_db  = ability_db
        self._learnset_db = learnset_db
        self._wild_db     = wild_db
        self._detail_dlg  = None

        self.setFixedHeight(68)
        self.setCursor(Qt.PointingHandCursor)
        self.setStyleSheet(
            "EncounterRowWidget { background:#1e1e2e; border-bottom:1px solid #2a2a3c; }"
            "EncounterRowWidget:hover { background:#252536; }"
        )

        lay = QHBoxLayout(self)
        lay.setContentsMargins(10, 4, 16, 4)
        lay.setSpacing(12)

        # Slot number
        slot_lbl = QLabel(f"#{slot:02d}")
        slot_lbl.setFixedWidth(28)
        slot_lbl.setAlignment(Qt.AlignCenter)
        slot_lbl.setStyleSheet(
            "color:#45475a; font-size:11px; font-weight:bold; background:transparent;"
        )
        lay.addWidget(slot_lbl)

        # Sprite thumbnail
        sprite_lbl = QLabel()
        sprite_lbl.setFixedSize(56, 56)
        sprite_lbl.setAlignment(Qt.AlignCenter)
        sprite_lbl.setStyleSheet("background:transparent;")
        pix = _get_sprite(species_key, 56)
        if not pix.isNull():
            sprite_lbl.setPixmap(pix)
        else:
            sprite_lbl.setText("?")
            sprite_lbl.setStyleSheet("color:#45475a; font-size:20px; background:transparent;")
        lay.addWidget(sprite_lbl)

        # Name + types
        name_col = QVBoxLayout()
        name_col.setSpacing(3)
        name_col.setAlignment(Qt.AlignVCenter)

        sp   = self._pokemon_db.get(
            (species_key[8:] if species_key.upper().startswith("SPECIES_") else species_key).upper()
        )
        name = sp.name if sp else _species_display(species_key)

        name_lbl = QLabel(name)
        name_lbl.setStyleSheet(
            "color:#cdd6f4; font-size:13px; font-weight:bold; background:transparent;"
        )
        name_col.addWidget(name_lbl)

        type_row = QHBoxLayout()
        type_row.setSpacing(4)
        if sp:
            for t in filter(None, [sp.type1, sp.type2 if sp.type2 else ""]):
                c    = TYPE_HEX.get(t.upper(), "#585b70")
                tbdg = QLabel(t.title())
                tbdg.setStyleSheet(
                    f"background:{c}; color:#1e1e2e; font-weight:bold; font-size:9px; "
                    "border-radius:3px; padding:1px 5px;"
                )
                tbdg.setAlignment(Qt.AlignCenter)
                type_row.addWidget(tbdg)
        type_row.addStretch()
        name_col.addLayout(type_row)
        lay.addLayout(name_col)
        lay.addStretch()

        # Level range
        lvl_col = QVBoxLayout()
        lvl_col.setAlignment(Qt.AlignCenter)
        lvl_head = QLabel("LVL")
        lvl_head.setStyleSheet("color:#45475a; font-size:9px; background:transparent;")
        lvl_head.setAlignment(Qt.AlignCenter)
        lvl_val = QLabel(f"{min_lvl}–{max_lvl}" if min_lvl != max_lvl else str(min_lvl))
        lvl_val.setStyleSheet(
            "color:#bac2de; font-size:12px; font-weight:bold; background:transparent;"
        )
        lvl_val.setAlignment(Qt.AlignCenter)
        lvl_col.addWidget(lvl_head)
        lvl_col.addWidget(lvl_val)
        lay.addLayout(lvl_col)

        # Encounter rate bar + %
        rate_col = QVBoxLayout()
        rate_col.setAlignment(Qt.AlignCenter)
        rate_head = QLabel("RATE")
        rate_head.setStyleSheet("color:#45475a; font-size:9px; background:transparent;")
        rate_head.setAlignment(Qt.AlignCenter)
        pct_lbl = QLabel(f"{pct}%")
        pct_lbl.setFixedWidth(40)
        pct_lbl.setAlignment(Qt.AlignCenter)
        pct_color = (
            "#a6e3a1" if pct >= 20
            else "#f9e2af" if pct >= 10
            else "#f38ba8"
        )
        pct_lbl.setStyleSheet(
            f"color:{pct_color}; font-size:13px; font-weight:bold; background:transparent;"
        )
        rate_col.addWidget(rate_head)
        rate_col.addWidget(pct_lbl)
        lay.addLayout(rate_col)

        # Click hint arrow
        arrow = QLabel("›")
        arrow.setStyleSheet("color:#45475a; font-size:18px; background:transparent;")
        lay.addWidget(arrow)

    def mousePressEvent(self, ev):
        if ev.button() == Qt.LeftButton:
            self._open_detail(ev.globalPos())
        super().mousePressEvent(ev)

    def _open_detail(self, global_pos: QPoint):
        if self._detail_dlg and self._detail_dlg.isVisible():
            self._detail_dlg.close()
        dlg = PokemonDetailDialog(
            self._species_key,
            self._pokemon_db,
            self._ability_db,
            self._learnset_db,
            self._wild_db,
        )
        dlg.adjustSize()
        screen_geo = QApplication.desktop().availableGeometry(global_pos)
        x = global_pos.x() + 12
        y = global_pos.y() - dlg.height() // 2
        x = max(screen_geo.left(), min(x, screen_geo.right()  - dlg.width()))
        y = max(screen_geo.top(),  min(y, screen_geo.bottom() - dlg.height()))
        dlg.move(x, y)
        dlg.show()
        self._detail_dlg = dlg


# ══════════════════════════════════════════════════════════════════════════════
# MonInfoCard — read-only party_god-style vertical card for one TrainerMon
# ══════════════════════════════════════════════════════════════════════════════
class MonInfoCard(QFrame):
    """Read-only party_god-style vertical card for one TrainerMon."""

    _STAT_NAMES  = ["HP",  "Atk", "Def", "SpA", "SpD", "Spe"]
    _STAT_COLORS = ["#FF5959", "#F5AC78", "#FAE078", "#9DB7F5", "#A7DB8D", "#FA92B2"]

    def __init__(self, slot_idx: int, mon, pokemon_db: dict, parent=None):
        super().__init__(parent)
        self._slot_idx   = slot_idx
        self._mon        = mon
        self._pokemon_db = pokemon_db
        self.setFixedWidth(172)
        self.setStyleSheet(
            "MonInfoCard { background:#252536; border:1px solid #313244; border-radius:8px; }"
        )
        self._build_ui()

    def _build_ui(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(8, 8, 8, 8)
        lay.setSpacing(3)

        # Slot label
        slot_lbl = QLabel(f"Slot {self._slot_idx + 1}")
        slot_lbl.setStyleSheet("color:#585b70; font-size:10px;")
        lay.addWidget(slot_lbl)

        # Sprite (80px, shiny if flagged)
        sp_key = self._mon.species
        pix = _get_sprite(sp_key, 80)
        if self._mon.shiny:
            raw_path = find_sprite_for_key(sp_key)
            if raw_path:
                raw_pix = make_shiny_pixmap(QPixmap(raw_path))
                if not raw_pix.isNull():
                    pix = raw_pix.scaled(80, 80, Qt.KeepAspectRatio, Qt.SmoothTransformation)

        sprite_lbl = QLabel()
        sprite_lbl.setFixedSize(80, 80)
        sprite_lbl.setAlignment(Qt.AlignCenter)
        sprite_lbl.setStyleSheet(
            "background:#181825; border-radius:6px; border:1px solid #313244; color:#585b70;")
        if not pix.isNull():
            sprite_lbl.setPixmap(pix)
        else:
            sprite_lbl.setText("?")
        sprite_row = QHBoxLayout()
        sprite_row.addStretch()
        sprite_row.addWidget(sprite_lbl)
        sprite_row.addStretch()
        lay.addLayout(sprite_row)

        # Species lookup
        sp_db_key = (sp_key[8:] if sp_key.upper().startswith('SPECIES_') else sp_key).upper()
        sp_obj = self._pokemon_db.get(sp_db_key)
        sp_name = sp_obj.name if sp_obj else _species_display(sp_key)

        # Name (nickname or species)
        display_name = self._mon.nickname if self._mon.nickname else sp_name
        name_lbl = QLabel(display_name)
        name_lbl.setAlignment(Qt.AlignCenter)
        name_lbl.setStyleSheet("color:#cdd6f4; font-size:12px; font-weight:bold;")
        lay.addWidget(name_lbl)

        if self._mon.nickname:
            sub_lbl = QLabel(f"({sp_name})")
            sub_lbl.setAlignment(Qt.AlignCenter)
            sub_lbl.setStyleSheet("color:#585b70; font-size:10px;")
            lay.addWidget(sub_lbl)

        # Level
        lv_lbl = QLabel(f"Lv. {self._mon.level}")
        lv_lbl.setAlignment(Qt.AlignCenter)
        lv_lbl.setStyleSheet("color:#a6e3a1; font-size:11px; font-weight:bold;")
        lay.addWidget(lv_lbl)

        # Type badges
        if sp_obj:
            type_row = QHBoxLayout()
            type_row.setSpacing(4)
            type_row.addStretch()
            for t in filter(None, [getattr(sp_obj, 'type1', ''), getattr(sp_obj, 'type2', '')]):
                if t and t.upper() not in ('NONE', '???', ''):
                    tc = TYPE_HEX.get(t.upper(), '#585b70')
                    tl = QLabel(t.title())
                    tl.setStyleSheet(
                        f"background:{tc}; color:#1e1e2e; font-size:9px; font-weight:bold; "
                        "border-radius:3px; padding:1px 5px;")
                    type_row.addWidget(tl)
            type_row.addStretch()
            lay.addLayout(type_row)

        lay.addWidget(_sep_line())

        # Nature + Ability
        nat_lbl = QLabel(self._mon.nature or "—")
        nat_lbl.setAlignment(Qt.AlignCenter)
        nat_lbl.setStyleSheet("color:#cba6f7; font-size:10px;")
        lay.addWidget(nat_lbl)

        ab_raw = self._mon.ability or ''
        ab_display = (ab_raw.replace('ABILITY_', '').replace('_', ' ').title()
                      if ab_raw else "—")
        ab_lbl = QLabel(ab_display)
        ab_lbl.setAlignment(Qt.AlignCenter)
        ab_lbl.setWordWrap(True)
        ab_lbl.setStyleSheet("color:#89dceb; font-size:10px;")
        lay.addWidget(ab_lbl)

        # Held item
        item_key = self._mon.held_item or ''
        if item_key and item_key not in ('ITEM_NONE', '', '0'):
            item_row = QHBoxLayout()
            item_row.setSpacing(4)
            item_row.setContentsMargins(0, 0, 0, 0)
            icon_lbl = QLabel()
            icon_lbl.setFixedSize(16, 16)
            icon_lbl.setAlignment(Qt.AlignCenter)
            item_pix = _item_icon_pixmap(item_key, 16)
            if not item_pix.isNull():
                icon_lbl.setPixmap(item_pix)
            else:
                icon_lbl.setText("•")
                icon_lbl.setStyleSheet("color:#f9e2af; font-size:10px;")
            item_name_lbl = QLabel(_item_display(item_key))
            item_name_lbl.setStyleSheet("color:#f9e2af; font-size:10px;")
            item_row.addStretch()
            item_row.addWidget(icon_lbl)
            item_row.addWidget(item_name_lbl)
            item_row.addStretch()
            lay.addLayout(item_row)

        lay.addWidget(_sep_line())

        # IVs as compact colored bars
        ivs = self._mon.ivs if self._mon.ivs else [31] * 6
        for i, (sname, scolor) in enumerate(zip(self._STAT_NAMES, self._STAT_COLORS)):
            iv_val = ivs[i] if i < len(ivs) else 31
            row = QHBoxLayout()
            row.setSpacing(3)
            row.setContentsMargins(0, 0, 0, 0)

            sn_lbl = QLabel(sname)
            sn_lbl.setFixedWidth(26)
            sn_lbl.setStyleSheet(f"color:{scolor}; font-size:9px; font-weight:bold;")

            bar = QProgressBar()
            bar.setRange(0, 31)
            bar.setValue(iv_val)
            bar.setFixedHeight(6)
            bar.setTextVisible(False)
            bar_color = ("#a6e3a1" if iv_val == 31
                         else "#f9e2af" if iv_val >= 20 else "#f38ba8")
            bar.setStyleSheet(
                f"QProgressBar {{ background:#1e1e2e; border:none; border-radius:3px; }}"
                f"QProgressBar::chunk {{ background:{bar_color}; border-radius:3px; }}"
            )

            iv_lbl = QLabel(str(iv_val))
            iv_lbl.setFixedWidth(18)
            iv_lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            iv_lbl.setStyleSheet(f"color:{scolor}; font-size:9px;")

            row.addWidget(sn_lbl)
            row.addWidget(bar, 1)
            row.addWidget(iv_lbl)
            lay.addLayout(row)

        lay.addWidget(_sep_line())

        # Moves (up to 4) with type badge + name
        for move_key in (self._mon.moves or []):
            if not move_key or move_key in ('MOVE_NONE', ''):
                continue
            mv     = move_lookup(move_key)
            mv_name = mv.get('name', move_key.replace('MOVE_', '').replace('_', ' ').title())
            mv_type = mv.get('type', '')

            mv_row = QHBoxLayout()
            mv_row.setSpacing(4)
            mv_row.setContentsMargins(0, 0, 0, 0)

            if mv_type:
                tc = TYPE_HEX.get(mv_type.upper(), '#585b70')
                t_lbl = QLabel(mv_type[:4].title())
                t_lbl.setFixedWidth(34)
                t_lbl.setAlignment(Qt.AlignCenter)
                t_lbl.setStyleSheet(
                    f"background:{tc}; color:#1e1e2e; font-size:8px; font-weight:bold; "
                    "border-radius:3px; padding:1px 2px;")
                mv_row.addWidget(t_lbl)

            mv_lbl = QLabel(mv_name[:18])
            mv_lbl.setStyleSheet("color:#cdd6f4; font-size:10px;")
            mv_row.addWidget(mv_lbl, 1)
            lay.addLayout(mv_row)

        lay.addStretch()


# ══════════════════════════════════════════════════════════════════════════════
# TrainerTeamDialog — party_god-style popup for a trainer's full party
# ══════════════════════════════════════════════════════════════════════════════
class TrainerTeamDialog(QDialog):
    """Party_god-style read-only popup showing a trainer's full party."""

    def __init__(self, trainer, pokemon_db: dict, parent=None):
        super().__init__(parent, Qt.Dialog | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground, False)
        self._trainer    = trainer
        self._pokemon_db = pokemon_db
        self._drag_pos   = None
        self._build_ui()
        self.adjustSize()

    def _build_ui(self):
        self.setStyleSheet(
            "TrainerTeamDialog { background:#11111b; border:1px solid #45475a; border-radius:10px; }"
        )
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Header
        header = QWidget()
        header.setFixedHeight(64)
        header.setStyleSheet("background:#11111b; border-radius:10px 10px 0 0;")
        header.mousePressEvent   = self._on_drag_press
        header.mouseMoveEvent    = self._on_drag_move
        header.mouseReleaseEvent = self._on_drag_release
        h_lay = QHBoxLayout(header)
        h_lay.setContentsMargins(16, 8, 12, 8)
        h_lay.setSpacing(14)

        pic_lbl = QLabel()
        pic_lbl.setFixedSize(48, 48)
        pic_lbl.setAlignment(Qt.AlignCenter)
        pix = _trainer_pic_pixmap(self._trainer.pic or '', 48)
        if not pix.isNull():
            pic_lbl.setPixmap(pix)
            pic_lbl.setStyleSheet("background:transparent;")
        else:
            cls_colors = {
                'TRAINER_CLASS_LEADER':   '#cba6f7',
                'TRAINER_CLASS_CHAMPION': '#f9e2af',
                'TRAINER_CLASS_RIVAL':    '#f38ba8',
            }
            fb = cls_colors.get(self._trainer.trainer_class or '', '#313244')
            pic_lbl.setStyleSheet(
                f"background:{fb}; border-radius:6px; color:#1e1e2e; "
                "font-size:18px; font-weight:bold;")
            pic_lbl.setText((self._trainer.name or '?')[:2].upper())
        h_lay.addWidget(pic_lbl)

        info = QVBoxLayout()
        info.setSpacing(2)
        name_lbl = QLabel(self._trainer.name or self._trainer.key)
        name_lbl.setStyleSheet(
            "color:#cdd6f4; font-size:15px; font-weight:bold; background:transparent;")
        info.addWidget(name_lbl)

        cls_raw = (self._trainer.trainer_class or '').replace(
            'TRAINER_CLASS_', '').replace('_', ' ').title()
        meta_row = QHBoxLayout()
        meta_row.setSpacing(6)
        cls_lbl = QLabel(cls_raw)
        cls_lbl.setStyleSheet("color:#6c7086; font-size:11px; background:transparent;")
        meta_row.addWidget(cls_lbl)
        if self._trainer.double_battle:
            meta_row.addWidget(_make_badge("DOUBLE", "#fab387"))
        meta_row.addStretch()
        info.addLayout(meta_row)
        h_lay.addLayout(info)
        h_lay.addStretch()

        close_btn = QPushButton("✕")
        close_btn.setFixedSize(28, 28)
        close_btn.setStyleSheet(
            "QPushButton { background:transparent; border:none; color:#585b70; font-size:14px; }"
            "QPushButton:hover { color:#f38ba8; }"
        )
        close_btn.clicked.connect(self.close)
        h_lay.addWidget(close_btn)
        root.addWidget(header)

        # Divider
        div = QFrame()
        div.setFixedHeight(1)
        div.setStyleSheet("background:#313244;")
        root.addWidget(div)

        # Party cards in horizontal scroll
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet(
            "QScrollArea { border:none; background:#181825; }"
            "QScrollBar:horizontal { height:6px; background:#1e1e2e; }"
            "QScrollBar::handle:horizontal { background:#45475a; border-radius:3px; }"
            "QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width:0; }"
        )

        cards_widget = QWidget()
        cards_widget.setStyleSheet("background:#181825;")
        cards_lay = QHBoxLayout(cards_widget)
        cards_lay.setContentsMargins(16, 16, 16, 16)
        cards_lay.setSpacing(10)

        party = self._trainer.party or []
        for i, mon in enumerate(party):
            cards_lay.addWidget(MonInfoCard(i, mon, self._pokemon_db))
        cards_lay.addStretch()

        scroll.setWidget(cards_widget)
        root.addWidget(scroll)
        self.setMinimumHeight(64 + 1 + 520)
        self.setMaximumHeight(64 + 1 + 520)

    def _on_drag_press(self, ev):
        if ev.button() == Qt.LeftButton:
            self._drag_pos = ev.globalPos() - self.frameGeometry().topLeft()

    def _on_drag_move(self, ev):
        if self._drag_pos and ev.buttons() == Qt.LeftButton:
            self.move(ev.globalPos() - self._drag_pos)

    def _on_drag_release(self, ev):
        self._drag_pos = None


# ══════════════════════════════════════════════════════════════════════════════
# TrainerPartyMon — 64x80 thumbnail; click → PokemonDetailDialog
# ══════════════════════════════════════════════════════════════════════════════
class TrainerPartyMon(QWidget):
    """48px sprite + name + level badge for one party member. Click → detail dialog."""

    def __init__(self, mon, pokemon_db, ability_db, learnset_db, wild_db, parent=None):
        super().__init__(parent)
        self._mon        = mon
        self._species    = mon.species if mon else ''
        self._pokemon_db = pokemon_db
        self._ability_db = ability_db
        self._learnset_db = learnset_db
        self._wild_db    = wild_db
        self._detail_dlg = None
        self.setFixedSize(64, 80)
        self.setCursor(Qt.PointingHandCursor)
        self._build_ui()

    def _build_ui(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(2, 2, 2, 2)
        lay.setSpacing(1)
        lay.setAlignment(Qt.AlignCenter)

        sp_key = self._species
        sp_db_key = (sp_key[8:] if sp_key.upper().startswith('SPECIES_') else sp_key).upper()
        sp_obj = self._pokemon_db.get(sp_db_key)

        border_color = '#313244'
        if sp_obj and sp_obj.type1:
            border_color = TYPE_HEX.get(sp_obj.type1.upper(), '#313244')

        self.setStyleSheet(
            f"TrainerPartyMon {{ background:#1e1e2e; border:2px solid {border_color}; "
            "border-radius:6px; }"
            "TrainerPartyMon:hover { background:#252536; }"
        )

        sprite_lbl = QLabel()
        sprite_lbl.setFixedSize(48, 48)
        sprite_lbl.setAlignment(Qt.AlignCenter)
        sprite_lbl.setStyleSheet("background:transparent; border:none;")
        pix = _get_sprite(sp_key, 48)
        if not pix.isNull():
            sprite_lbl.setPixmap(pix)
        else:
            sprite_lbl.setText('?')
            sprite_lbl.setStyleSheet("color:#45475a; font-size:18px; background:transparent; border:none;")
        lay.addWidget(sprite_lbl, 0, Qt.AlignCenter)

        name = sp_obj.name if sp_obj else _species_display(sp_key)
        if self._mon and self._mon.nickname:
            name = self._mon.nickname
        name_lbl = QLabel(name[:8])
        name_lbl.setAlignment(Qt.AlignCenter)
        name_lbl.setStyleSheet("color:#cdd6f4; font-size:9px; background:transparent; border:none;")
        lay.addWidget(name_lbl)

        if self._mon:
            lvl_lbl = QLabel(f"Lv.{self._mon.level}")
            lvl_lbl.setAlignment(Qt.AlignCenter)
            lvl_lbl.setStyleSheet("color:#a6adc8; font-size:8px; background:transparent; border:none;")
            lay.addWidget(lvl_lbl)

    def mousePressEvent(self, ev):
        if ev.button() == Qt.LeftButton:
            self._open_detail(ev.globalPos())
        super().mousePressEvent(ev)

    def _open_detail(self, global_pos: QPoint):
        if self._detail_dlg and self._detail_dlg.isVisible():
            self._detail_dlg.close()
        dlg = PokemonDetailDialog(
            self._species,
            self._pokemon_db,
            self._ability_db,
            self._learnset_db,
            self._wild_db,
        )
        dlg.adjustSize()
        screen_geo = QApplication.desktop().availableGeometry(global_pos)
        x = global_pos.x() + 12
        y = global_pos.y() - dlg.height() // 2
        x = max(screen_geo.left(), min(x, screen_geo.right()  - dlg.width()))
        y = max(screen_geo.top(),  min(y, screen_geo.bottom() - dlg.height()))
        dlg.move(x, y)
        dlg.show()
        self._detail_dlg = dlg


# ══════════════════════════════════════════════════════════════════════════════
# TrainerCard — clickable card; opens TrainerTeamDialog on click
# ══════════════════════════════════════════════════════════════════════════════
class TrainerCard(QFrame):
    """Card showing trainer sprite, name/class, and party row. Click → TrainerTeamDialog."""

    def __init__(self, trainer, pokemon_db, ability_db, learnset_db, wild_db, parent=None):
        super().__init__(parent)
        self._trainer    = trainer
        self._pokemon_db = pokemon_db
        self._ability_db = ability_db
        self._learnset_db = learnset_db
        self._wild_db    = wild_db
        self._detail_dlg = None

        self.setMinimumHeight(100)
        self.setCursor(Qt.PointingHandCursor)
        self.setStyleSheet(
            "TrainerCard { background:#181825; border:1px solid #313244; border-radius:8px; }"
            "TrainerCard:hover { border-color:#45475a; }"
        )
        self._build_ui()

    def _build_ui(self):
        lay = QHBoxLayout(self)
        lay.setContentsMargins(12, 10, 12, 10)
        lay.setSpacing(14)

        # Trainer sprite
        pic_lbl = QLabel()
        pic_lbl.setFixedSize(48, 48)
        pic_lbl.setAlignment(Qt.AlignCenter)
        pix = _trainer_pic_pixmap(self._trainer.pic or '', 48)
        if not pix.isNull():
            pic_lbl.setPixmap(pix)
            pic_lbl.setStyleSheet("background:transparent;")
        else:
            cls_colors = {
                'TRAINER_CLASS_LEADER': '#cba6f7',
                'TRAINER_CLASS_CHAMPION': '#f9e2af',
                'TRAINER_CLASS_RIVAL': '#f38ba8',
            }
            fb_color = cls_colors.get(self._trainer.trainer_class or '', '#313244')
            pic_lbl.setStyleSheet(
                f"background:{fb_color}; border-radius:6px; color:#1e1e2e; "
                "font-size:18px; font-weight:bold;"
            )
            initials = (self._trainer.name or '?')[:2].upper()
            pic_lbl.setText(initials)
        lay.addWidget(pic_lbl, 0, Qt.AlignTop)

        # Info column
        info_col = QVBoxLayout()
        info_col.setSpacing(3)
        info_col.setAlignment(Qt.AlignTop)

        name_lbl = QLabel(self._trainer.name or self._trainer.key)
        name_lbl.setStyleSheet("color:#cdd6f4; font-size:13px; font-weight:bold; background:transparent;")
        info_col.addWidget(name_lbl)

        cls_raw = (self._trainer.trainer_class or '').replace('TRAINER_CLASS_', '').replace('_', ' ').title()
        meta_row = QHBoxLayout()
        meta_row.setSpacing(6)
        cls_lbl = QLabel(cls_raw)
        cls_lbl.setStyleSheet("color:#6c7086; font-size:11px; background:transparent;")
        meta_row.addWidget(cls_lbl)
        if self._trainer.double_battle:
            dbl = _make_badge("DOUBLE", "#fab387")
            meta_row.addWidget(dbl)
        meta_row.addStretch()
        info_col.addLayout(meta_row)

        lay.addLayout(info_col)
        lay.addStretch()

        # Party row
        party_row = QHBoxLayout()
        party_row.setSpacing(4)
        party_row.setAlignment(Qt.AlignVCenter)
        for mon in (self._trainer.party or []):
            mon_widget = TrainerPartyMon(
                mon,
                self._pokemon_db,
                self._ability_db,
                self._learnset_db,
                self._wild_db,
            )
            party_row.addWidget(mon_widget)
        lay.addLayout(party_row)

    def mousePressEvent(self, ev):
        if ev.button() == Qt.LeftButton:
            self._open_team_dialog(ev.globalPos())
        super().mousePressEvent(ev)

    def _open_team_dialog(self, global_pos: QPoint):
        if self._detail_dlg and self._detail_dlg.isVisible():
            self._detail_dlg.close()
        dlg = TrainerTeamDialog(self._trainer, self._pokemon_db, parent=self)
        screen_geo = QApplication.desktop().availableGeometry(global_pos)
        x = max(screen_geo.left(), min(global_pos.x() - dlg.width() // 2,
                                        screen_geo.right() - dlg.width()))
        y = max(screen_geo.top(), min(global_pos.y() - dlg.height() // 2,
                                       screen_geo.bottom() - dlg.height()))
        dlg.move(x, y)
        dlg.show()
        self._detail_dlg = dlg


# ══════════════════════════════════════════════════════════════════════════════
# TrainersTab
# ══════════════════════════════════════════════════════════════════════════════
class TrainersTab(QWidget):
    """Scrollable list of TrainerCard widgets."""

    def __init__(self, trainer_keys: list, trainer_db: dict,
                 pokemon_db, ability_db, learnset_db, wild_db, parent=None):
        super().__init__(parent)
        self._trainer_keys = trainer_keys
        self._trainer_db   = trainer_db
        self._pokemon_db   = pokemon_db
        self._ability_db   = ability_db
        self._learnset_db  = learnset_db
        self._wild_db      = wild_db
        self._built        = False

    def showEvent(self, ev):
        if not self._built:
            self._build_ui()
            self._built = True
        super().showEvent(ev)

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        trainers = []
        for key in self._trainer_keys:
            t = self._trainer_db.get(key.upper())
            if t:
                trainers.append(t)

        count_hdr = QWidget()
        count_hdr.setFixedHeight(32)
        count_hdr.setStyleSheet("background:#181825; border-bottom:1px solid #313244;")
        ch_lay = QHBoxLayout(count_hdr)
        ch_lay.setContentsMargins(14, 0, 14, 0)
        count_txt = f"{len(trainers)} Trainer{'s' if len(trainers) != 1 else ''}"
        count_lbl = QLabel(count_txt)
        count_lbl.setStyleSheet("color:#6c7086; font-size:11px; background:transparent;")
        ch_lay.addWidget(count_lbl)
        ch_lay.addStretch()
        outer.addWidget(count_hdr)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border:none; background:#1e1e2e; }")

        inner = QWidget()
        inner.setStyleSheet("background:#1e1e2e;")
        inner_lay = QVBoxLayout(inner)
        inner_lay.setContentsMargins(12, 12, 12, 12)
        inner_lay.setSpacing(8)

        if not trainers:
            empty = QLabel("No trainers in this area.")
            empty.setAlignment(Qt.AlignCenter)
            empty.setStyleSheet("color:#45475a; font-size:13px; padding:24px; background:transparent;")
            inner_lay.addWidget(empty)
        else:
            for t in trainers:
                card = TrainerCard(t, self._pokemon_db, self._ability_db,
                                   self._learnset_db, self._wild_db)
                inner_lay.addWidget(card)

        inner_lay.addStretch()
        scroll.setWidget(inner)
        outer.addWidget(scroll, 1)


# ══════════════════════════════════════════════════════════════════════════════
# ItemRow
# ══════════════════════════════════════════════════════════════════════════════
class ItemRow(QWidget):
    """Single item row: icon + name + type badge."""

    BADGE_COLORS = {
        'Ball':   '#a6e3a1',
        'Hidden': '#f9e2af',
        'Gift':   '#89b4fa',
        'Trade':  '#cba6f7',
    }

    def __init__(self, item_key: str, badge_type: str,
                 extra_text: str = '', parent=None):
        super().__init__(parent)
        self.setFixedHeight(40)
        self._item_key  = item_key
        self._badge_type = badge_type
        lay = QHBoxLayout(self)
        lay.setContentsMargins(10, 4, 16, 4)
        lay.setSpacing(10)

        icon_lbl = QLabel()
        icon_lbl.setFixedSize(28, 28)
        icon_lbl.setAlignment(Qt.AlignCenter)
        pix = _item_icon_pixmap(item_key, 28)
        if not pix.isNull():
            icon_lbl.setPixmap(pix)
            icon_lbl.setStyleSheet("background:transparent;")
        else:
            icon_lbl.setText("?")
            icon_lbl.setStyleSheet("color:#45475a; font-size:14px; background:transparent;")
        lay.addWidget(icon_lbl)

        name_col = QVBoxLayout()
        name_col.setSpacing(1)
        name_col.setAlignment(Qt.AlignVCenter)
        name_lbl = QLabel(_item_display(item_key))
        name_lbl.setStyleSheet("color:#cdd6f4; font-size:12px; font-weight:bold; background:transparent;")
        name_col.addWidget(name_lbl)
        if extra_text:
            extra_lbl = QLabel(extra_text)
            extra_lbl.setStyleSheet("color:#6c7086; font-size:10px; background:transparent;")
            name_col.addWidget(extra_lbl)
        lay.addLayout(name_col)
        lay.addStretch()

        badge_color = self.BADGE_COLORS.get(badge_type, '#585b70')
        badge = _make_badge(badge_type.upper(), badge_color)
        lay.addWidget(badge)

    def mouseDoubleClickEvent(self, ev):
        super().mouseDoubleClickEvent(ev)


# ══════════════════════════════════════════════════════════════════════════════
# TradeRow
# ══════════════════════════════════════════════════════════════════════════════
class TradeRow(QWidget):
    """Row showing an in-game trade: offered species + wanted species."""

    def __init__(self, trade: dict, pokemon_db, ability_db, learnset_db, wild_db, parent=None):
        super().__init__(parent)
        self._trade      = trade
        self._pokemon_db = pokemon_db
        self._ability_db = ability_db
        self._learnset_db = learnset_db
        self._wild_db    = wild_db
        self.setFixedHeight(72)
        self.setCursor(Qt.PointingHandCursor)
        self.setStyleSheet(
            "TradeRow { background:#1e1e2e; border-bottom:1px solid #2a2a3c; }"
            "TradeRow:hover { background:#252536; }"
        )
        self._detail_dlg = None
        self._click_species = None
        self._build_ui()

    def _build_ui(self):
        lay = QHBoxLayout(self)
        lay.setContentsMargins(12, 6, 16, 6)
        lay.setSpacing(12)

        offered = 'SPECIES_' + self._trade.get('species', '')
        wanted  = 'SPECIES_' + self._trade.get('requested', '')

        off_lbl = QLabel()
        off_lbl.setFixedSize(48, 48)
        off_lbl.setAlignment(Qt.AlignCenter)
        off_lbl.setStyleSheet("background:transparent;")
        pix = _get_sprite(offered, 48)
        if not pix.isNull():
            off_lbl.setPixmap(pix)
        else:
            off_lbl.setText("?")
            off_lbl.setStyleSheet("color:#45475a; font-size:18px; background:transparent;")
        lay.addWidget(off_lbl)

        off_col = QVBoxLayout()
        off_col.setSpacing(2)
        off_col.setAlignment(Qt.AlignVCenter)
        nick = self._trade.get('nickname', '')
        sp_name = _species_display(offered)
        if nick:
            off_name = QLabel(nick)
            off_name.setStyleSheet("color:#cdd6f4; font-size:12px; font-weight:bold; background:transparent;")
            off_col.addWidget(off_name)
            sp_sub = QLabel(f"({sp_name})")
            sp_sub.setStyleSheet("color:#6c7086; font-size:10px; background:transparent;")
            off_col.addWidget(sp_sub)
        else:
            off_name = QLabel(sp_name)
            off_name.setStyleSheet("color:#cdd6f4; font-size:12px; font-weight:bold; background:transparent;")
            off_col.addWidget(off_name)
        ot = self._trade.get('ot_name', '')
        if ot:
            ot_lbl = QLabel(f"OT: {ot}")
            ot_lbl.setStyleSheet("color:#45475a; font-size:10px; background:transparent;")
            off_col.addWidget(ot_lbl)
        lay.addLayout(off_col)

        arrow = QLabel("⇄")
        arrow.setStyleSheet("color:#89b4fa; font-size:18px; background:transparent;")
        arrow.setAlignment(Qt.AlignCenter)
        lay.addWidget(arrow)

        want_col = QVBoxLayout()
        want_col.setSpacing(2)
        want_col.setAlignment(Qt.AlignVCenter)
        want_name = QLabel(_species_display(wanted))
        want_name.setStyleSheet("color:#cdd6f4; font-size:12px; font-weight:bold; background:transparent;")
        want_col.addWidget(want_name)
        want_lbl = QLabel("Wants")
        want_lbl.setStyleSheet("color:#6c7086; font-size:10px; background:transparent;")
        want_col.addWidget(want_lbl)
        lay.addLayout(want_col)

        want_lbl2 = QLabel()
        want_lbl2.setFixedSize(48, 48)
        want_lbl2.setAlignment(Qt.AlignCenter)
        want_lbl2.setStyleSheet("background:transparent;")
        pix2 = _get_sprite(wanted, 48)
        if not pix2.isNull():
            want_lbl2.setPixmap(pix2)
        else:
            want_lbl2.setText("?")
            want_lbl2.setStyleSheet("color:#45475a; font-size:18px; background:transparent;")
        lay.addWidget(want_lbl2)

        held = self._trade.get('held_item', '')
        if held:
            held_pix = _item_icon_pixmap(held, 24)
            held_lbl = QLabel()
            held_lbl.setFixedSize(24, 24)
            held_lbl.setAlignment(Qt.AlignCenter)
            held_lbl.setStyleSheet("background:transparent;")
            if not held_pix.isNull():
                held_lbl.setPixmap(held_pix)
            else:
                held_lbl.setText("@")
                held_lbl.setStyleSheet("color:#6c7086; font-size:10px; background:transparent;")
            lay.addWidget(held_lbl)

        lay.addStretch()

        self._off_species = offered
        self._want_species = wanted

    def mousePressEvent(self, ev):
        if ev.button() == Qt.LeftButton:
            mid_x = self.width() // 2
            species = self._off_species if ev.pos().x() < mid_x else self._want_species
            self._open_detail(ev.globalPos(), species)
        super().mousePressEvent(ev)

    def _open_detail(self, global_pos: QPoint, species: str):
        if self._detail_dlg and self._detail_dlg.isVisible():
            self._detail_dlg.close()
        dlg = PokemonDetailDialog(
            species,
            self._pokemon_db,
            self._ability_db,
            self._learnset_db,
            self._wild_db,
        )
        dlg.adjustSize()
        screen_geo = QApplication.desktop().availableGeometry(global_pos)
        x = global_pos.x() + 12
        y = global_pos.y() - dlg.height() // 2
        x = max(screen_geo.left(), min(x, screen_geo.right()  - dlg.width()))
        y = max(screen_geo.top(),  min(y, screen_geo.bottom() - dlg.height()))
        dlg.move(x, y)
        dlg.show()
        self._detail_dlg = dlg


# ══════════════════════════════════════════════════════════════════════════════
# ItemsTab
# ══════════════════════════════════════════════════════════════════════════════
class ItemsTab(QWidget):
    """Scrollable tab with item balls, hidden items, NPC gifts, and trades."""

    def __init__(self, item_data: dict, script_data: dict,
                 trade_details: dict, pokemon_db, ability_db, learnset_db, wild_db,
                 parent=None):
        super().__init__(parent)
        self._item_data    = item_data
        self._script_data  = script_data
        self._trade_details = trade_details
        self._pokemon_db   = pokemon_db
        self._ability_db   = ability_db
        self._learnset_db  = learnset_db
        self._wild_db      = wild_db
        self._built        = False

    def showEvent(self, ev):
        if not self._built:
            self._build_ui()
            self._built = True
        super().showEvent(ev)

    def _build_ui(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border:none; background:#1e1e2e; }")

        inner = QWidget()
        inner.setStyleSheet("background:#1e1e2e;")
        inner_lay = QVBoxLayout(inner)
        inner_lay.setContentsMargins(12, 12, 12, 12)
        inner_lay.setSpacing(4)

        has_anything = False

        balls = self._item_data.get('balls', [])
        if balls:
            has_anything = True
            hdr = _section_header("ITEM BALLS")
            inner_lay.addWidget(hdr)
            for b in balls:
                row = ItemRow(b['item'], 'Ball')
                inner_lay.addWidget(row)
            inner_lay.addSpacing(8)

        hidden = self._item_data.get('hidden', [])
        if hidden:
            has_anything = True
            hdr = _section_header("HIDDEN ITEMS")
            inner_lay.addWidget(hdr)
            for h in hidden:
                row = ItemRow(h['item'], 'Hidden')
                inner_lay.addWidget(row)
            inner_lay.addSpacing(8)

        gifts = self._script_data.get('gifts', [])
        if gifts:
            has_anything = True
            hdr = _section_header("NPC GIFTS")
            inner_lay.addWidget(hdr)
            for g in gifts:
                label = g.get('script', '')
                extra = f"from: {label}" if label else ''
                qty = g.get('qty', 1)
                if qty > 1:
                    extra = f"×{qty}  {extra}".strip()
                row = ItemRow(g['item'], 'Gift', extra)
                inner_lay.addWidget(row)
            inner_lay.addSpacing(8)

        trade_ids = self._script_data.get('trades', [])
        trade_rows = [self._trade_details.get(tid) for tid in trade_ids
                      if self._trade_details.get(tid)]
        if trade_rows:
            has_anything = True
            hdr = _section_header("IN-GAME TRADES")
            inner_lay.addWidget(hdr)
            for trade in trade_rows:
                row = TradeRow(trade, self._pokemon_db, self._ability_db,
                               self._learnset_db, self._wild_db)
                inner_lay.addWidget(row)
            inner_lay.addSpacing(8)

        if not has_anything:
            empty = QLabel("No items or trades in this area.")
            empty.setAlignment(Qt.AlignCenter)
            empty.setStyleSheet("color:#45475a; font-size:13px; padding:24px; background:transparent;")
            inner_lay.addWidget(empty)

        inner_lay.addStretch()
        scroll.setWidget(inner)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)


# ══════════════════════════════════════════════════════════════════════════════
# EncountersTab
# ══════════════════════════════════════════════════════════════════════════════
class EncountersTab(QWidget):
    """Encounter tables for a single map/subloc, reusing EncounterRowWidget."""

    def __init__(self, enc_data: dict, pokemon_db, ability_db, learnset_db, wild_db,
                 parent=None):
        super().__init__(parent)
        self._enc_data    = enc_data
        self._pokemon_db  = pokemon_db
        self._ability_db  = ability_db
        self._learnset_db = learnset_db
        self._wild_db     = wild_db
        self._built       = False

    def showEvent(self, ev):
        if not self._built:
            self._build_ui()
            self._built = True
        super().showEvent(ev)

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        if not self._enc_data:
            empty = QLabel("No encounter data for this location.")
            empty.setAlignment(Qt.AlignCenter)
            empty.setStyleSheet("color:#45475a; font-size:13px; padding:40px; background:transparent;")
            outer.addWidget(empty)
            return

        tabs = QTabWidget()
        tabs.setStyleSheet(
            "QTabWidget::pane { border:none; }"
            "QTabBar::tab { background:#181825; color:#6c7086; padding:8px 20px; "
            "   border-top-left-radius:6px; border-top-right-radius:6px; "
            "   border:1px solid #313244; margin-right:2px; }"
            "QTabBar::tab:selected { background:#1e1e2e; color:#cdd6f4; "
            "   border-bottom:2px solid #89b4fa; }"
            "QTabBar::tab:hover { background:#252536; color:#bac2de; }"
        )

        for ftype, tab_label in TABLE_ORDER:
            if ftype not in self._enc_data:
                continue
            table_color = TABLE_COLOR.get(ftype, "#89b4fa")

            if ftype == "fishing_mons":
                fish_data = self._enc_data["fishing_mons"]
                tab_widget = QWidget()
                tab_widget.setStyleSheet("background:#1e1e2e;")
                tab_v = QVBoxLayout(tab_widget)
                tab_v.setContentsMargins(0, 0, 0, 0)
                tab_v.setSpacing(0)

                fish_scroll = QScrollArea()
                fish_scroll.setWidgetResizable(True)
                fish_scroll.setStyleSheet("QScrollArea { border:none; background:#1e1e2e; }")
                fish_inner  = QWidget()
                fish_inner.setStyleSheet("background:transparent;")
                fish_lay    = QVBoxLayout(fish_inner)
                fish_lay.setContentsMargins(0, 0, 0, 12)
                fish_lay.setSpacing(0)

                has_fish = False
                for rod_key, rod_label in ROD_ORDER:
                    mons = fish_data.get(rod_key, [])
                    if not mons:
                        continue
                    has_fish = True
                    rod_hdr = QWidget()
                    rod_hdr.setFixedHeight(32)
                    rod_hdr.setStyleSheet(
                        f"background:#181825; border-bottom:1px solid #313244; "
                        f"border-left:3px solid {table_color};"
                    )
                    rh_lay = QHBoxLayout(rod_hdr)
                    rh_lay.setContentsMargins(14, 0, 14, 0)
                    rh_lbl = QLabel(rod_label.upper())
                    rh_lbl.setStyleSheet(
                        f"color:{table_color}; font-size:10px; font-weight:bold; "
                        "letter-spacing:1px; background:transparent;"
                    )
                    rh_lay.addWidget(rh_lbl)
                    rh_lay.addStretch()
                    fish_lay.addWidget(rod_hdr)

                    for slot_i, mon in enumerate(mons, 1):
                        row = EncounterRowWidget(
                            slot_i, mon["species"],
                            mon["min_level"], mon["max_level"],
                            mon["rate"], mon["pct"],
                            self._pokemon_db, self._ability_db,
                            self._learnset_db, self._wild_db,
                        )
                        fish_lay.addWidget(row)

                fish_lay.addStretch()
                fish_scroll.setWidget(fish_inner)
                tab_v.addWidget(fish_scroll)
                if has_fish:
                    tabs.addTab(tab_widget, tab_label)
            else:
                table_info = self._enc_data[ftype]
                mons       = table_info.get("mons", [])
                if not mons:
                    continue

                enc_rate   = table_info.get("encounter_rate", 0)
                tab_widget = QWidget()
                tab_widget.setStyleSheet("background:#1e1e2e;")
                tab_v = QVBoxLayout(tab_widget)
                tab_v.setContentsMargins(0, 0, 0, 0)
                tab_v.setSpacing(0)

                if enc_rate:
                    enc_hdr = QWidget()
                    enc_hdr.setFixedHeight(28)
                    enc_hdr.setStyleSheet(
                        f"background:#181825; border-bottom:1px solid #313244; "
                        f"border-left:3px solid {table_color};"
                    )
                    eh_lay = QHBoxLayout(enc_hdr)
                    eh_lay.setContentsMargins(14, 0, 14, 0)
                    eh_lbl = QLabel(f"{tab_label.upper()}  ·  Area encounter rate: {enc_rate}%")
                    eh_lbl.setStyleSheet(
                        f"color:{table_color}; font-size:10px; font-weight:bold; "
                        "letter-spacing:0.8px; background:transparent;"
                    )
                    eh_lay.addWidget(eh_lbl)
                    eh_lay.addStretch()
                    tab_v.addWidget(enc_hdr)

                scroll = QScrollArea()
                scroll.setWidgetResizable(True)
                scroll.setStyleSheet("QScrollArea { border:none; background:#1e1e2e; }")
                inner  = QWidget()
                inner.setStyleSheet("background:transparent;")
                inner_lay = QVBoxLayout(inner)
                inner_lay.setContentsMargins(0, 0, 0, 12)
                inner_lay.setSpacing(0)

                for slot_i, mon in enumerate(mons, 1):
                    row = EncounterRowWidget(
                        slot_i, mon["species"],
                        mon["min_level"], mon["max_level"],
                        mon["rate"], mon["pct"],
                        self._pokemon_db, self._ability_db,
                        self._learnset_db, self._wild_db,
                    )
                    inner_lay.addWidget(row)

                inner_lay.addStretch()
                scroll.setWidget(inner)
                tab_v.addWidget(scroll, 1)
                tabs.addTab(tab_widget, tab_label)

        if tabs.count() == 0:
            empty = QLabel("No encounter data for this location.")
            empty.setAlignment(Qt.AlignCenter)
            empty.setStyleSheet("color:#45475a; font-size:13px; padding:40px; background:transparent;")
            outer.addWidget(empty)
        else:
            outer.addWidget(tabs, 1)


# ══════════════════════════════════════════════════════════════════════════════
# SublocationWidget — tabbed content for one floor / indoor area
# ══════════════════════════════════════════════════════════════════════════════
class SublocationWidget(QWidget):
    """
    Tabbed content widget for one sub-location (map floor / indoor area).
    Tabs: Encounters | Trainers | Items & Trades
    """

    def __init__(self, short_name: str, parent_name: str,
                 enc_data: dict, pokemon_db, ability_db, learnset_db, wild_db,
                 trainer_db, trade_details, parent=None):
        super().__init__(parent)
        self._short_name   = short_name
        self._parent_name  = parent_name
        self._enc_data     = enc_data
        self._pokemon_db   = pokemon_db
        self._ability_db   = ability_db
        self._learnset_db  = learnset_db
        self._wild_db      = wild_db
        self._trainer_db   = trainer_db
        self._trade_details = trade_details
        self._built        = False

    def ensure_built(self):
        if not self._built:
            self._build_ui()
            self._built = True

    def _build_ui(self):
        item_data   = _load_map_items(self._short_name)
        script_data = _load_script_data(self._short_name)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        tabs = QTabWidget()
        tabs.setStyleSheet(
            "QTabWidget::pane { border:none; background:#1e1e2e; }"
            "QTabBar::tab { background:#181825; color:#6c7086; padding:8px 24px; "
            "   border-top-left-radius:6px; border-top-right-radius:6px; "
            "   border:1px solid #313244; margin-right:2px; }"
            "QTabBar::tab:selected { background:#1e1e2e; color:#cdd6f4; "
            "   border-bottom:2px solid #89b4fa; }"
            "QTabBar::tab:hover { background:#252536; color:#bac2de; }"
        )

        enc_tab = EncountersTab(
            self._enc_data, self._pokemon_db, self._ability_db,
            self._learnset_db, self._wild_db,
        )
        tabs.addTab(enc_tab, "Encounters")

        trainer_tab = TrainersTab(
            script_data.get('trainers', []),
            self._trainer_db,
            self._pokemon_db, self._ability_db,
            self._learnset_db, self._wild_db,
        )
        tabs.addTab(trainer_tab, "Trainers")

        items_tab = ItemsTab(
            item_data, script_data, self._trade_details,
            self._pokemon_db, self._ability_db,
            self._learnset_db, self._wild_db,
        )
        tabs.addTab(items_tab, "Items & Trades")

        def _on_tab_change(idx):
            w = tabs.widget(idx)
            if hasattr(w, '_built') and not w._built:
                w._build_ui()
                w._built = True

        tabs.currentChanged.connect(_on_tab_change)
        outer.addWidget(tabs, 1)


# ══════════════════════════════════════════════════════════════════════════════
# LocationPanel
# ══════════════════════════════════════════════════════════════════════════════
class LocationPanel(QWidget):
    """
    Right-side panel showing full info for one primary location.
    Header bar → sub-location button strip → stacked content area.
    """

    def __init__(self, pokemon_db, ability_db, learnset_db, wild_db,
                 trainer_db, trade_details, map_encounters, parent=None):
        super().__init__(parent)
        self._pokemon_db   = pokemon_db
        self._ability_db   = ability_db
        self._learnset_db  = learnset_db
        self._wild_db      = wild_db
        self._trainer_db   = trainer_db
        self._trade_details = trade_details
        self._map_encounters = map_encounters

        self._current_map_key = ''
        self._subloc_buttons  = []
        self._subloc_widgets  = {}

        self._build_ui()

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # Header bar
        self._header = QWidget()
        self._header.setFixedHeight(52)
        self._header.setStyleSheet("background:#181825; border-bottom:1px solid #313244;")
        h_lay = QHBoxLayout(self._header)
        h_lay.setContentsMargins(18, 0, 18, 0)
        h_lay.setSpacing(12)

        self._loc_lbl = QLabel("Select a location")
        self._loc_lbl.setObjectName("title")
        h_lay.addWidget(self._loc_lbl)

        self._type_badge = QLabel("")
        self._type_badge.setStyleSheet(
            "background:#313244; color:#cdd6f4; font-size:10px; font-weight:bold; "
            "border-radius:4px; padding:2px 8px;"
        )
        self._type_badge.hide()
        h_lay.addWidget(self._type_badge)

        h_lay.addStretch()
        outer.addWidget(self._header)

        # Sub-location strip
        self._subloc_strip = QWidget()
        self._subloc_strip.setFixedHeight(44)
        self._subloc_strip.setStyleSheet("background:#181825; border-bottom:1px solid #313244;")
        self._strip_lay = QHBoxLayout(self._subloc_strip)
        self._strip_lay.setContentsMargins(12, 6, 12, 6)
        self._strip_lay.setSpacing(6)
        self._strip_lay.addStretch()
        outer.addWidget(self._subloc_strip)

        # Stacked content
        self._stack = QStackedWidget()
        self._stack.setStyleSheet("background:#1e1e2e;")
        outer.addWidget(self._stack, 1)

        # Placeholder
        self._placeholder = QLabel("Select a location from the left panel.")
        self._placeholder.setAlignment(Qt.AlignCenter)
        self._placeholder.setStyleSheet("color:#45475a; font-size:14px; padding:40px; background:transparent;")
        self._stack.addWidget(self._placeholder)

    def load_location(self, map_key: str):
        """Switch to showing the given primary map location."""
        if map_key == self._current_map_key:
            return
        self._current_map_key = map_key

        short_name = _map_key_to_short(map_key)
        display    = _map_name_to_label(map_key)

        self._loc_lbl.setText(display)

        map_data = _get_map_json(short_name) if short_name else {}
        map_type = map_data.get('map_type', '')
        if map_type:
            self._type_badge.setText(map_type.replace('_', ' ').title())
            self._type_badge.show()
        else:
            self._type_badge.hide()

        # Clear old subloc buttons
        for btn in self._subloc_buttons:
            self._strip_lay.removeWidget(btn)
            btn.deleteLater()
        self._subloc_buttons = []
        self._subloc_widgets = {}

        # Remove all widgets from stack except placeholder
        while self._stack.count() > 1:
            w = self._stack.widget(1)
            self._stack.removeWidget(w)
            w.deleteLater()

        # Build sub-location list: [main_area] + sub_maps
        sublocs = [short_name] if short_name else []
        if short_name:
            subs = _SUB_MAPS.get(short_name, [])
            sublocs += subs

        # Deduplicate while preserving order
        seen = set()
        deduped = []
        for s in sublocs:
            if s not in seen:
                seen.add(s)
                deduped.append(s)
        sublocs = deduped

        for subloc in sublocs:
            display_name = _subloc_display(subloc, short_name)
            btn = QPushButton(display_name)
            btn.setCheckable(True)
            btn.setStyleSheet(
                "QPushButton { background:#313244; color:#cdd6f4; border:1px solid #45475a; "
                "   border-radius:12px; padding:3px 12px; font-size:11px; }"
                "QPushButton:checked { background:#89b4fa; color:#1e1e2e; border-color:#89b4fa; "
                "   font-weight:bold; }"
                "QPushButton:hover { background:#3d3f4f; }"
            )
            subloc_copy = subloc
            btn.clicked.connect(lambda checked, s=subloc_copy: self._switch_subloc(s))
            self._strip_lay.insertWidget(self._strip_lay.count() - 1, btn)
            self._subloc_buttons.append(btn)

        # Select first subloc
        if sublocs:
            self._switch_subloc(sublocs[0])
        else:
            self._stack.setCurrentIndex(0)

    def _switch_subloc(self, short_name: str):
        """Switch the stacked widget to the given sublocation."""
        for btn in self._subloc_buttons:
            btn.setChecked(btn.text() == _subloc_display(
                short_name, _map_key_to_short(self._current_map_key)))

        if short_name not in self._subloc_widgets:
            enc_data = self._map_encounters.get(
                _KEY_BY_DIR.get(short_name, ''), {})
            w = SublocationWidget(
                short_name,
                _map_key_to_short(self._current_map_key),
                enc_data,
                self._pokemon_db, self._ability_db,
                self._learnset_db, self._wild_db,
                self._trainer_db, self._trade_details,
            )
            self._stack.addWidget(w)
            self._subloc_widgets[short_name] = w

        w = self._subloc_widgets[short_name]
        w.ensure_built()
        self._stack.setCurrentWidget(w)


# ══════════════════════════════════════════════════════════════════════════════
# Search panel
# ══════════════════════════════════════════════════════════════════════════════

def _build_search_index(map_encounters: dict, pokemon_db: dict) -> dict:
    """
    Build a flat search index over all maps.
    Returns {
      'items':    [{'name', 'type', 'map_key', 'short_name'}],
      'trainers': [{'name', 'trainer_key', 'map_key', 'short_name'}],
      'pokemon':  [{'name', 'species_key', 'map_key', 'short_name', 'table_type'}],
      'trades':   [{'offered', 'wanted', 'trade_id', 'map_key', 'short_name'}],
    }
    """
    global _SEARCH_INDEX
    if _SEARCH_INDEX:
        return _SEARCH_INDEX

    result = {'items': [], 'trainers': [], 'pokemon': [], 'trades': []}

    if not os.path.isdir(MAPS_DIR):
        _SEARCH_INDEX = result
        return result

    trade_details = _load_trade_details()

    for short_name in sorted(os.listdir(MAPS_DIR)):
        map_key = _KEY_BY_DIR.get(short_name, '')

        try:
            item_data = _load_map_items(short_name)
            for b in item_data.get('balls', []):
                result['items'].append({
                    'name': _item_display(b['item']),
                    'item_key': b['item'],
                    'badge': 'Ball',
                    'map_key': map_key,
                    'short_name': short_name,
                })
            for h in item_data.get('hidden', []):
                result['items'].append({
                    'name': _item_display(h['item']),
                    'item_key': h['item'],
                    'badge': 'Hidden',
                    'map_key': map_key,
                    'short_name': short_name,
                })
        except Exception:
            pass

        try:
            script_data = _load_script_data(short_name)
            trainer_db  = _load_trainer_db()
            for tk in script_data.get('trainers', []):
                t = trainer_db.get(tk.upper())
                name = (t.name if t else tk.replace('TRAINER_', '').replace('_', ' ').title())
                result['trainers'].append({
                    'name': name,
                    'trainer_key': tk,
                    'map_key': map_key,
                    'short_name': short_name,
                })
            for g in script_data.get('gifts', []):
                result['items'].append({
                    'name': _item_display(g['item']),
                    'item_key': g['item'],
                    'badge': 'Gift',
                    'map_key': map_key,
                    'short_name': short_name,
                })
            for tid in script_data.get('trades', []):
                td = trade_details.get(tid, {})
                result['trades'].append({
                    'offered':  td.get('species', tid),
                    'wanted':   td.get('requested', ''),
                    'trade_id': tid,
                    'map_key':  map_key,
                    'short_name': short_name,
                })
        except Exception:
            pass

        try:
            enc = map_encounters.get(map_key, {})
            seen_species = set()
            for ftype, tab_label in TABLE_ORDER:
                if ftype == 'fishing_mons':
                    fish = enc.get('fishing_mons', {})
                    for rod_key, mons in fish.items():
                        for mon in mons:
                            sp = mon.get('species', '')
                            if sp and sp not in seen_species:
                                seen_species.add(sp)
                                sp_obj = pokemon_db.get(
                                    (sp[8:] if sp.upper().startswith('SPECIES_') else sp).upper()
                                )
                                name = sp_obj.name if sp_obj else _species_display(sp)
                                result['pokemon'].append({
                                    'name': name,
                                    'species_key': sp,
                                    'map_key': map_key,
                                    'short_name': short_name,
                                    'table_type': 'Fishing',
                                })
                else:
                    tinfo = enc.get(ftype, {})
                    for mon in tinfo.get('mons', []):
                        sp = mon.get('species', '')
                        if sp and sp not in seen_species:
                            seen_species.add(sp)
                            sp_obj = pokemon_db.get(
                                (sp[8:] if sp.upper().startswith('SPECIES_') else sp).upper()
                            )
                            name = sp_obj.name if sp_obj else _species_display(sp)
                            result['pokemon'].append({
                                'name': name,
                                'species_key': sp,
                                'map_key': map_key,
                                'short_name': short_name,
                                'table_type': tab_label,
                            })
        except Exception:
            pass

    _SEARCH_INDEX = result
    return result


class SearchResultRow(QWidget):
    """Single search result row — icon + name + location path."""

    def __init__(self, icon_pix: QPixmap, primary: str, secondary: str,
                 location: str, map_key: str, on_navigate, parent=None):
        super().__init__(parent)
        self._map_key    = map_key
        self._on_navigate = on_navigate
        self.setFixedHeight(44)
        self.setCursor(Qt.PointingHandCursor)
        self.setStyleSheet(
            "SearchResultRow { background:#1e1e2e; border-bottom:1px solid #2a2a3c; }"
            "SearchResultRow:hover { background:#252536; }"
        )
        lay = QHBoxLayout(self)
        lay.setContentsMargins(12, 4, 16, 4)
        lay.setSpacing(10)

        icon_lbl = QLabel()
        icon_lbl.setFixedSize(32, 32)
        icon_lbl.setAlignment(Qt.AlignCenter)
        icon_lbl.setStyleSheet("background:transparent;")
        if icon_pix and not icon_pix.isNull():
            icon_lbl.setPixmap(icon_pix)
        else:
            icon_lbl.setText("?")
            icon_lbl.setStyleSheet("color:#45475a; font-size:14px; background:transparent;")
        lay.addWidget(icon_lbl)

        text_col = QVBoxLayout()
        text_col.setSpacing(1)
        text_col.setAlignment(Qt.AlignVCenter)
        primary_lbl = QLabel(primary)
        primary_lbl.setStyleSheet("color:#cdd6f4; font-size:12px; font-weight:bold; background:transparent;")
        text_col.addWidget(primary_lbl)
        if secondary:
            sec_lbl = QLabel(secondary)
            sec_lbl.setStyleSheet("color:#6c7086; font-size:10px; background:transparent;")
            text_col.addWidget(sec_lbl)
        lay.addLayout(text_col)
        lay.addStretch()

        loc_lbl = QLabel(location)
        loc_lbl.setStyleSheet("color:#585b70; font-size:10px; background:transparent;")
        lay.addWidget(loc_lbl)

        nav_lbl = QLabel("›")
        nav_lbl.setStyleSheet("color:#45475a; font-size:14px; background:transparent;")
        lay.addWidget(nav_lbl)

    def mousePressEvent(self, ev):
        if ev.button() == Qt.LeftButton and self._map_key and self._on_navigate:
            self._on_navigate(self._map_key)
        super().mousePressEvent(ev)


class SearchResultsPanel(QWidget):
    """Full-panel display of search results with tabbed categories."""

    def __init__(self, pokemon_db, on_navigate, parent=None):
        super().__init__(parent)
        self._pokemon_db  = pokemon_db
        self._on_navigate = on_navigate
        self._build_ui()

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        hdr = QWidget()
        hdr.setFixedHeight(48)
        hdr.setStyleSheet("background:#181825; border-bottom:1px solid #313244;")
        h_lay = QHBoxLayout(hdr)
        h_lay.setContentsMargins(18, 0, 18, 0)
        self._result_count_lbl = QLabel("Search results")
        self._result_count_lbl.setObjectName("title")
        h_lay.addWidget(self._result_count_lbl)
        h_lay.addStretch()
        outer.addWidget(hdr)

        self._tabs = QTabWidget()
        self._tabs.setStyleSheet(
            "QTabWidget::pane { border:none; background:#1e1e2e; }"
            "QTabBar::tab { background:#181825; color:#6c7086; padding:8px 20px; "
            "   border-top-left-radius:6px; border-top-right-radius:6px; "
            "   border:1px solid #313244; margin-right:2px; }"
            "QTabBar::tab:selected { background:#1e1e2e; color:#cdd6f4; "
            "   border-bottom:2px solid #89b4fa; }"
            "QTabBar::tab:hover { background:#252536; color:#bac2de; }"
        )
        outer.addWidget(self._tabs, 1)

        self._tab_widgets = {}
        for cat in ['All', 'Items', 'Trainers', 'Pokemon', 'Trades']:
            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            scroll.setStyleSheet("QScrollArea { border:none; background:#1e1e2e; }")
            inner = QWidget()
            inner.setStyleSheet("background:#1e1e2e;")
            lay   = QVBoxLayout(inner)
            lay.setContentsMargins(0, 0, 0, 12)
            lay.setSpacing(0)
            scroll.setWidget(inner)
            self._tabs.addTab(scroll, cat)
            self._tab_widgets[cat] = (scroll, inner, lay)

    def _clear_tab(self, cat: str):
        _, inner, lay = self._tab_widgets[cat]
        while lay.count():
            item = lay.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def populate(self, query: str, search_index: dict):
        q = query.strip().lower()
        total = 0

        for cat in ['All', 'Items', 'Trainers', 'Pokemon', 'Trades']:
            self._clear_tab(cat)

        def _add_row(cat_name: str, icon_pix, primary, secondary, location, map_key):
            nonlocal total
            for tab_cat in ['All', cat_name]:
                _, inner, lay = self._tab_widgets[tab_cat]
                row = SearchResultRow(icon_pix, primary, secondary, location,
                                      map_key, self._on_navigate)
                lay.addWidget(row)
            if cat_name != 'All':
                total += 1

        for entry in search_index.get('items', []):
            if q and q not in entry['name'].lower() and q not in entry['item_key'].lower():
                continue
            pix = _item_icon_pixmap(entry['item_key'], 28)
            loc = _map_name_to_label(entry['map_key']) if entry['map_key'] else entry['short_name']
            _add_row('Items', pix, entry['name'], entry['badge'], loc, entry['map_key'])

        for entry in search_index.get('trainers', []):
            if q and q not in entry['name'].lower() and q not in entry['trainer_key'].lower():
                continue
            loc = _map_name_to_label(entry['map_key']) if entry['map_key'] else entry['short_name']
            trainer_db = _load_trainer_db()
            t = trainer_db.get(entry['trainer_key'].upper())
            pix = _trainer_pic_pixmap(t.pic if t else '', 28)
            cls_text = (t.trainer_class or '').replace('TRAINER_CLASS_', '').replace('_', ' ').title() if t else ''
            _add_row('Trainers', pix, entry['name'], cls_text, loc, entry['map_key'])

        for entry in search_index.get('pokemon', []):
            if q and q not in entry['name'].lower() and q not in entry['species_key'].lower():
                continue
            pix = _get_sprite(entry['species_key'], 28)
            loc = _map_name_to_label(entry['map_key']) if entry['map_key'] else entry['short_name']
            _add_row('Pokemon', pix, entry['name'], entry['table_type'], loc, entry['map_key'])

        for entry in search_index.get('trades', []):
            offered_name = _species_display('SPECIES_' + entry['offered']) if entry['offered'] else entry['trade_id']
            wanted_name  = _species_display('SPECIES_' + entry['wanted'])  if entry['wanted'] else ''
            if q and (q not in offered_name.lower() and q not in wanted_name.lower()
                      and q not in entry['trade_id'].lower()):
                continue
            pix = _get_sprite('SPECIES_' + entry['offered'], 28) if entry['offered'] else QPixmap()
            loc = _map_name_to_label(entry['map_key']) if entry['map_key'] else entry['short_name']
            secondary = f"wants: {wanted_name}" if wanted_name else ''
            _add_row('Trades', pix, offered_name, secondary, loc, entry['map_key'])

        for cat in ['All', 'Items', 'Trainers', 'Pokemon', 'Trades']:
            _, inner, lay = self._tab_widgets[cat]
            if lay.count() == 0:
                empty = QLabel(f"No {cat.lower()} results found." if q else f"No {cat.lower()} data available.")
                empty.setAlignment(Qt.AlignCenter)
                empty.setStyleSheet("color:#45475a; font-size:13px; padding:24px; background:transparent;")
                lay.addWidget(empty)
            lay.addStretch()

        self._result_count_lbl.setText(
            f"Search: \"{query}\"  —  {total} results" if q else "All Data"
        )


# ══════════════════════════════════════════════════════════════════════════════
# FatefulEncounterWindow — merged main window
# ══════════════════════════════════════════════════════════════════════════════
class FatefulEncounterWindow(QMainWindow):

    def __init__(self, pokemon_db, ability_db, learnset_db, wild_db,
                 trainer_db, trade_details, map_encounters):
        super().__init__()
        self._pokemon_db    = pokemon_db
        self._ability_db    = ability_db
        self._learnset_db   = learnset_db
        self._wild_db       = wild_db
        self._trainer_db    = trainer_db
        self._trade_details = trade_details
        self._map_encounters = map_encounters
        self._search_index  = {}
        self._search_built  = False

        self.setWindowTitle("Fateful Encounter — Hoenn Navigator")
        self.resize(1280, 800)
        self._build_ui()

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root_lay = QVBoxLayout(central)
        root_lay.setContentsMargins(0, 0, 0, 0)
        root_lay.setSpacing(0)

        # Top bar: title + search
        top_bar = QWidget()
        top_bar.setFixedHeight(52)
        top_bar.setStyleSheet(
            "background:#11111b; border-bottom:1px solid #313244;"
        )
        tb_lay = QHBoxLayout(top_bar)
        tb_lay.setContentsMargins(18, 0, 18, 0)
        tb_lay.setSpacing(14)

        title_lbl = QLabel("FATEFUL ENCOUNTER")
        title_lbl.setStyleSheet(
            "color:#cba6f7; font-size:13px; font-weight:bold; letter-spacing:2px; "
            "background:transparent;"
        )
        tb_lay.addWidget(title_lbl)

        tb_lay.addStretch()

        self._search_input = QLineEdit()
        self._search_input.setPlaceholderText("Search items, trainers, Pokémon…")
        self._search_input.setFixedWidth(320)
        self._search_input.setFixedHeight(32)
        self._search_input.setStyleSheet(
            "QLineEdit { background:#1e1e2e; border:1px solid #45475a; border-radius:6px; "
            "   color:#cdd6f4; padding:4px 10px; font-size:12px; }"
            "QLineEdit:focus { border-color:#cba6f7; }"
        )
        self._search_input.returnPressed.connect(self._do_search)
        tb_lay.addWidget(self._search_input)

        search_btn = QPushButton("Search")
        search_btn.setFixedHeight(32)
        search_btn.setStyleSheet(
            "QPushButton { background:#cba6f7; color:#1e1e2e; border:none; border-radius:6px; "
            "   padding:0 16px; font-size:12px; font-weight:bold; }"
            "QPushButton:hover { background:#d5baf9; }"
            "QPushButton:pressed { background:#a882d0; }"
        )
        search_btn.clicked.connect(self._do_search)
        tb_lay.addWidget(search_btn)

        clear_btn = QPushButton("Clear")
        clear_btn.setFixedHeight(32)
        clear_btn.setStyleSheet(
            "QPushButton { background:#313244; color:#cdd6f4; border:1px solid #45475a; "
            "   border-radius:6px; padding:0 12px; font-size:12px; }"
            "QPushButton:hover { background:#3d3f4f; }"
        )
        clear_btn.clicked.connect(self._clear_search)
        tb_lay.addWidget(clear_btn)

        root_lay.addWidget(top_bar)

        # Body: splitter (tree | right panel)
        splitter = QSplitter(Qt.Horizontal)
        splitter.setHandleWidth(1)
        splitter.setStyleSheet(
            "QSplitter::handle { background:#313244; }"
        )

        # Left nav panel
        nav_panel = QWidget()
        nav_panel.setMinimumWidth(200)
        nav_panel.setMaximumWidth(300)
        nav_panel.setStyleSheet("background:#181825; border-right:1px solid #313244;")
        nav_lay = QVBoxLayout(nav_panel)
        nav_lay.setContentsMargins(0, 0, 0, 0)
        nav_lay.setSpacing(0)

        nav_hdr = QWidget()
        nav_hdr.setFixedHeight(40)
        nav_hdr.setStyleSheet("background:#181825; border-bottom:1px solid #313244;")
        nh_lay = QHBoxLayout(nav_hdr)
        nh_lay.setContentsMargins(14, 0, 14, 0)
        nav_title = QLabel("REGIONS")
        nav_title.setStyleSheet(
            "color:#cba6f7; font-size:10px; font-weight:bold; letter-spacing:1.5px; "
            "background:transparent;"
        )
        nh_lay.addWidget(nav_title)
        nav_lay.addWidget(nav_hdr)

        self._tree = QTreeWidget()
        self._tree.setHeaderHidden(True)
        self._tree.setStyleSheet(
            "QTreeWidget { background:#181825; border:none; color:#cdd6f4; outline:none; }"
            "QTreeWidget::item { padding:4px 6px; border-bottom:1px solid #1e1e2e; }"
            "QTreeWidget::item:selected { background:#313244; color:#cdd6f4; }"
            "QTreeWidget::item:hover { background:#252536; }"
            "QTreeWidget::branch { background:#181825; }"
            "QTreeWidget::branch:has-children:closed { color:#585b70; }"
            "QTreeWidget::branch:has-children:open   { color:#cba6f7; }"
        )
        self._tree.setIndentation(14)
        self._tree.itemClicked.connect(self._on_tree_click)
        self._populate_tree()
        nav_lay.addWidget(self._tree, 1)

        # Footer
        nav_footer = QWidget()
        nav_footer.setFixedHeight(30)
        nav_footer.setStyleSheet("background:#181825; border-top:1px solid #313244;")
        nf_lay = QHBoxLayout(nav_footer)
        nf_lay.setContentsMargins(10, 0, 10, 0)
        count = sum(len(maps) for _, maps in ROUTING)
        nf_lbl = QLabel(f"{count} locations")
        nf_lbl.setStyleSheet("color:#45475a; font-size:11px; background:transparent;")
        nf_lay.addWidget(nf_lbl)
        nav_lay.addWidget(nav_footer)

        splitter.addWidget(nav_panel)

        # Right: stacked (location panel | search results)
        self._right_stack = QStackedWidget()
        self._right_stack.setStyleSheet("background:#1e1e2e;")

        self._loc_panel = LocationPanel(
            self._pokemon_db, self._ability_db, self._learnset_db,
            self._wild_db, self._trainer_db, self._trade_details,
            self._map_encounters,
        )
        self._right_stack.addWidget(self._loc_panel)

        self._search_panel = SearchResultsPanel(
            self._pokemon_db,
            on_navigate=self._navigate_to_map,
        )
        self._right_stack.addWidget(self._search_panel)

        splitter.addWidget(self._right_stack)
        splitter.setSizes([240, 1040])

        root_lay.addWidget(splitter, 1)

        QTimer.singleShot(100, self._select_first)

    def _populate_tree(self):
        """Build the chapter tree with all ROUTING entries."""
        self._map_to_item = {}
        _init_map_index()

        for chapter_name, map_keys in ROUTING:
            chapter_item = QTreeWidgetItem([chapter_name])
            chapter_item.setForeground(0, QColor("#cba6f7"))
            font = chapter_item.font(0)
            font.setBold(True)
            font.setPointSize(9)
            chapter_item.setFont(0, font)
            chapter_item.setData(0, Qt.UserRole, None)

            for mk in map_keys:
                short_name = _DIR_BY_KEY.get(mk, '')
                if not short_name:
                    continue
                display = _map_name_to_label(mk)
                child = QTreeWidgetItem([display])
                child.setData(0, Qt.UserRole, mk)

                enc_data = self._map_encounters.get(mk, {})
                if 'land_mons' in enc_data:
                    child.setForeground(0, QColor("#a6e3a1"))
                elif 'water_mons' in enc_data:
                    child.setForeground(0, QColor("#89b4fa"))
                elif enc_data:
                    child.setForeground(0, QColor("#f9e2af"))
                else:
                    child.setForeground(0, QColor("#bac2de"))

                chapter_item.addChild(child)
                self._map_to_item[mk] = child

            if chapter_item.childCount() > 0:
                self._tree.addTopLevelItem(chapter_item)

        self._tree.expandAll()

    def _select_first(self):
        root = self._tree.invisibleRootItem()
        for i in range(root.childCount()):
            chapter = root.child(i)
            if chapter.childCount() > 0:
                first_child = chapter.child(0)
                self._tree.setCurrentItem(first_child)
                self._on_tree_click(first_child, 0)
                return

    def _on_tree_click(self, item: QTreeWidgetItem, _col: int):
        map_key = item.data(0, Qt.UserRole)
        if not map_key:
            item.setExpanded(not item.isExpanded())
            return
        self._right_stack.setCurrentWidget(self._loc_panel)
        self._loc_panel.load_location(map_key)

    def _do_search(self):
        query = self._search_input.text().strip()
        if not self._search_built:
            print("Building search index...")
            self._search_index = _build_search_index(
                self._map_encounters, self._pokemon_db)
            self._search_built = True
        self._search_panel.populate(query, self._search_index)
        self._right_stack.setCurrentWidget(self._search_panel)

    def _clear_search(self):
        self._search_input.clear()
        self._right_stack.setCurrentWidget(self._loc_panel)

    def _navigate_to_map(self, map_key: str):
        """Navigate tree and location panel to the given map key."""
        self._right_stack.setCurrentWidget(self._loc_panel)
        self._loc_panel.load_location(map_key)
        item = self._map_to_item.get(map_key)
        if item:
            self._tree.setCurrentItem(item)
            self._tree.scrollToItem(item)


# ══════════════════════════════════════════════════════════════════════════════
# Compact stylesheet addon
# ══════════════════════════════════════════════════════════════════════════════
_COMPACT = """
QWidget          { font-size:12px; }
QPushButton      { font-size:12px; padding:4px 10px; }
QLineEdit, QSpinBox, QComboBox { padding:3px 8px; min-height:22px; font-size:12px; }
QTabBar::tab     { padding:5px 12px; font-size:12px; }
QListWidget::item{ padding:2px 5px; }
QGroupBox        { margin-top:5px; padding-top:4px; font-size:10px; }
QCheckBox        { font-size:11px; }
QLabel           { font-size:12px; }
QLabel#title     { font-size:15px; }
QLabel#heading   { font-size:9px; }
"""


# ══════════════════════════════════════════════════════════════════════════════
# Entry point
# ══════════════════════════════════════════════════════════════════════════════
def main():
    print("Fateful Encounter — loading data...")

    print("  Pokemon database...", end=' ', flush=True)
    pokemon_db = {p.key.upper(): p for p in load_all_pokemon()}
    print(f"{len(pokemon_db)} species")

    print("  Abilities / learnsets...", end=' ', flush=True)
    ability_db  = load_ability_info()
    learnset_db = load_learnsets()
    print("done")

    print("  Wild encounters...", end=' ', flush=True)
    wild_db        = load_wild_encounters()
    map_encounters = load_map_encounters()
    print(f"{len(map_encounters)} locations")

    print("  Map index / trainers...", end=' ', flush=True)
    load_items()
    _ensure_data_loaded()
    print(f"{len(_TRAINER_DB)} trainers")

    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setStyleSheet(DARK_STYLE + _COMPACT)

    _icon_path = os.path.join(_HERE, "gfx", "party_god_icon.png")
    if os.path.isfile(_icon_path):
        app.setWindowIcon(QIcon(_icon_path))

    win = FatefulEncounterWindow(
        pokemon_db, ability_db, learnset_db, wild_db,
        _TRAINER_DB, _TRADE_DETAILS, map_encounters,
    )
    win.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
