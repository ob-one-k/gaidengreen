#!/usr/bin/env python3
"""
stat_dex.py — Full Pokédex viewer & stat balancing tool

  GUI mode (default):  python stat_dex.py
  CLI mode:            python stat_dex.py --cli [options]

STATUS column is user-controlled. Click any Status cell to cycle:
  UNTOUCHED → BUFFED → NERFED → UNTOUCHED
All changes are auto-saved to stat_dex_status.json next to this script.

Stats always resolve to Gen 8+ (GEN_LATEST) values.
"""
import os, re, sys, json, argparse, shutil

# ── Resolve lib/ on path so decomp_data is importable ────────────────────────
_HERE = os.path.dirname(os.path.abspath(__file__))
_LIB  = os.path.join(_HERE, "lib")
if _LIB not in sys.path:
    sys.path.insert(0, _LIB)

# ══════════════════════════════════════════════════════════════════════════════
# SHARED DATA LIBRARY
# ══════════════════════════════════════════════════════════════════════════════
from decomp_data import (
    ROOT, DATA_DIR, GEN_FILES, SPRITES_DIR,
    ALL_TYPES, TYPE_HEX, STATUS_HEX, STATUS_BG, GEN_HEX,
    EVO_STAGES, STATUSES, STATUS_CYCLE, STAGE_ORDER, bst_color,
    PAT_BLOCK, PAT_FIELD, PAT_TYPES, PAT_NAME, PAT_DEFINE, PAT_TERNARY,
    PAT_EVO_HAS, PAT_EVO_TARGET,
    get_form_label, Pokemon, load_all_pokemon, build_sprite_map, find_sprite_for_key,
    load_status, save_status, cycle_status,
    load_learnsets, species_to_learnset_key, move_lookup,
    load_ability_info, load_wild_encounters, get_dex_base_stats, load_move_learners,
    load_evo_chains,
    make_shiny_pixmap, make_transparent_pixmap, DARK_STYLE,
)

# ══════════════════════════════════════════════════════════════════════════════
# STATUS FILE  (per-tool, with migration from old stat_king_status.json)
# ══════════════════════════════════════════════════════════════════════════════
_DATA_DIR   = os.path.join(_HERE, "data")
os.makedirs(_DATA_DIR, exist_ok=True)
STATUS_FILE = os.path.join(_DATA_DIR, "stat_dex_status.json")
_old_status = os.path.join(_HERE, "stat_king_status.json")
if not os.path.isfile(STATUS_FILE) and os.path.isfile(_old_status):
    shutil.copy(_old_status, STATUS_FILE)

def _load_status():  return load_status(STATUS_FILE)
def _save_status(d): return save_status(d, STATUS_FILE)


# ── Suppress C-level stderr (libpng bKGD warnings, etc.) ─────────────────────
import contextlib

@contextlib.contextmanager
def _quiet_stderr():
    """Redirect fd 2 to /dev/null for the duration of the block.

    libpng emits 'bKGD: invalid index' warnings directly to the C stderr
    file descriptor when Qt loads indexed PNG sprites.  These are harmless
    metadata warnings (invalid background-colour hint chunk) but flood the
    console.  This suppresses them without touching Python's sys.stderr.
    """
    try:
        null_fd  = os.open(os.devnull, os.O_WRONLY)
        saved_fd = os.dup(2)
        os.dup2(null_fd, 2)
        try:
            yield
        finally:
            os.dup2(saved_fd, 2)
            os.close(saved_fd)
            os.close(null_fd)
    except Exception:
        yield  # if fd ops fail (unusual), just run unguarded


def _pixel_perfect(pix, target_w, target_h):
    """Scale a pixmap using the largest integer multiplier that fits inside
    target_w × target_h, then use nearest-neighbor (FastTransformation).

    Integer-multiple nearest-neighbor is the only way to get crisp pixel art
    from GBA sprites — bilinear (SmoothTransformation) blurs them.
    Falls back to a plain FastTransformation fit if the source is already
    larger than the target.
    """
    if pix.isNull():
        return pix
    sw, sh = pix.width(), pix.height()
    if sw == 0 or sh == 0:
        return pix
    factor = max(1, min(target_w // sw, target_h // sh))
    return pix.scaled(sw * factor, sh * factor,
                      Qt.KeepAspectRatio, Qt.FastTransformation)


# ══════════════════════════════════════════════════════════════════════════════
# SORT FIELDS
# ══════════════════════════════════════════════════════════════════════════════
SORT_FIELDS = [
    ("BST",      "bst"),
    ("Name A→Z", "name"),
    ("Name Z→A", "name_rev"),
    ("Gen",      "gen"),
    ("Dex #",    "nat_dex"),
    ("HP",       "hp"),
    ("Atk",      "atk"),
    ("Def",      "def_"),
    ("SpA",      "spa"),
    ("SpD",      "spd"),
    ("Spe",      "spe"),
    ("Height",   "height"),
    ("Weight",   "weight"),
    ("Stage",    "stage"),
    ("Status",   "status"),
]

# ══════════════════════════════════════════════════════════════════════════════
# CLI MODE
# ══════════════════════════════════════════════════════════════════════════════
_ANSI_RESET  = "\033[0m"
_ANSI_BOLD   = "\033[1m"
_ANSI_TYPE   = {
    "FIRE":"\033[91m","WATER":"\033[94m","GRASS":"\033[92m","ELECTRIC":"\033[93m",
    "ICE":"\033[96m","PSYCHIC":"\033[95m","NORMAL":"\033[97m","FIGHTING":"\033[31m",
    "POISON":"\033[35m","GROUND":"\033[33m","GHOST":"\033[34m","ROCK":"\033[90m",
    "BUG":"\033[32m","DRAGON":"\033[34m","DARK":"\033[90m","STEEL":"\033[37m",
    "FAIRY":"\033[95m","FLYING":"\033[34m",
}
_ANSI_STATUS = {"BUFFED":"\033[92m","NERFED":"\033[91m","UNTOUCHED":"\033[90m"}


def cli_apply_filters(lst, args, status_dict):
    out = lst
    if args.type:
        raw = args.type.upper()
        if '/' in raw:
            a, b = raw.split('/')
            out = [p for p in out if p.dual_type(a.strip(), b.strip())]
        else:
            out = [p for p in out if p.has_type(raw)]
    if args.gen:
        out = [p for p in out if p.gen == args.gen]
    if args.min is not None:
        out = [p for p in out if p.bst >= args.min]
    if args.max is not None:
        out = [p for p in out if p.bst <= args.max]
    if args.search:
        q = args.search.lower()
        out = [p for p in out if q in p.name.lower() or q in p.key.lower()]
    if args.status:
        s = args.status.upper()
        out = [p for p in out if status_dict.get(p.key,'UNTOUCHED') == s]
    if args.stage:
        s = args.stage.upper()
        out = [p for p in out if p.stage == s]
    if args.legendary:   out = [p for p in out if p.is_legendary]
    if args.mythical:    out = [p for p in out if p.is_mythical]
    if args.ultra_beast: out = [p for p in out if p.is_ultra_beast]
    if args.paradox:     out = [p for p in out if p.is_paradox]
    return out


def cli_apply_sort(lst, sort_key, status_dict):
    order = {
        'bst-desc': lambda p: -p.bst,
        'bst-asc':  lambda p:  p.bst,
        'name':     lambda p:  p.name.lower(),
        'name-rev': lambda p: [-ord(c) for c in p.name.lower()],
        'gen':      lambda p: (p.gen, p.name.lower()),
        'nat-dex':  lambda p: (p.nat_dex, p.name.lower()),
        'height':   lambda p: -p.height,
        'weight':   lambda p: -p.weight,
        'stage':    lambda p: (STAGE_ORDER.get(p.stage,9), p.name.lower()),
        'hp':  lambda p: -p.hp,  'atk': lambda p: -p.atk,
        'def': lambda p: -p.def_, 'spa': lambda p: -p.spa,
        'spd': lambda p: -p.spd,  'spe': lambda p: -p.spe,
        'status': lambda p: (STATUS_CYCLE.index(status_dict.get(p.key,'UNTOUCHED')), -p.bst),
    }
    return sorted(lst, key=order.get(sort_key, order['bst-desc']))


def cli_print_table(lst, status_dict, use_color, show_bar):
    if not lst:
        print("No Pokemon matched your filters."); return
    NW = max(16, max(len(p.name) for p in lst) + 2)
    TW, SW = 10, 14

    def c(txt, code): return f"{code}{txt}{_ANSI_RESET}" if use_color and code else txt
    def ct(t):
        if not t: return '-'
        return c(t, _ANSI_TYPE.get(t,''))
    def cs(p):
        st = status_dict.get(p.key,'UNTOUCHED')
        return c(st, _ANSI_STATUS.get(st,''))

    hdr = (f"{'NAME':<{NW}} GEN  {'TYPE1':<{TW}}{'TYPE2':<{TW}}"
           f" {'STG':<6}{'HP':>5}{'ATK':>5}{'DEF':>5}{'SpA':>5}{'SpD':>5}{'SPE':>5}"
           f"  {'BST':>4}  {'STATUS':<{SW}}" + ("  BAR" if show_bar else ""))
    sep = "─" * (NW+5+TW*2+6+30+2+4+2+SW+(20 if show_bar else 0))
    if use_color: print(f"{_ANSI_BOLD}{hdr}{_ANSI_RESET}")
    else:         print(hdr)
    print(sep)

    for p in lst:
        st     = status_dict.get(p.key,'UNTOUCHED')
        t1_raw = p.type1 or '-';  t2_raw = p.type2 or '-'
        t1_col = ct(p.type1);     t2_col = ct(p.type2)
        st_col = cs(p)
        t1_pad = TW + (len(t1_col)-len(t1_raw))
        t2_pad = TW + (len(t2_col)-len(t2_raw))
        st_pad = SW + (len(st_col)-len(st))
        marker = ('★' if p.is_legendary else '✦' if p.is_mythical else
                  '◆' if p.is_ultra_beast else '◈' if p.is_paradox else '')
        row = (f"{p.name+marker:<{NW}} G{p.gen:<3}  {t1_col:<{t1_pad}}{t2_col:<{t2_pad}}"
               f" {p.stage:<6}{p.hp:>5}{p.atk:>5}{p.def_:>5}{p.spa:>5}{p.spd:>5}{p.spe:>5}"
               f"  {p.bst:>4}  {st_col:<{st_pad}}")
        if show_bar:
            filled = min(int(p.bst/750*18), 18)
            row += f"  {'█'*filled}{'░'*(18-filled)}"
        print(row)

    print(sep)
    n   = len(lst)
    avg = sum(p.bst for p in lst) / n
    nb  = sum(1 for p in lst if status_dict.get(p.key,'UNTOUCHED') == 'BUFFED')
    nn  = sum(1 for p in lst if status_dict.get(p.key,'UNTOUCHED') == 'NERFED')
    nu  = n - nb - nn
    print(f"  {n} Pokemon  Avg BST:{avg:.0f}  BUFFED:{nb}  NERFED:{nn}  UNTOUCHED:{nu}")


def cli_main(args):
    print("Loading Pokemon data...", end=' ', flush=True)
    all_pokemon = load_all_pokemon()
    status_dict = _load_status()
    print(f"{len(all_pokemon)} loaded.")
    filtered = cli_apply_filters(all_pokemon, args, status_dict)
    sorted_l = cli_apply_sort(filtered, args.sort, status_dict)
    if args.limit: sorted_l = sorted_l[:args.limit]
    use_color = hasattr(sys.stdout,'isatty') and sys.stdout.isatty() and not args.no_color
    cli_print_table(sorted_l, status_dict, use_color, not args.no_bar)


# ══════════════════════════════════════════════════════════════════════════════
# GUI
# ══════════════════════════════════════════════════════════════════════════════
try:
    from PyQt5.QtWidgets import (
        QApplication, QMainWindow, QDialog, QWidget, QTableWidget, QTableWidgetItem,
        QHeaderView, QAbstractItemView,
        QVBoxLayout, QHBoxLayout, QFormLayout, QSplitter, QLineEdit,
        QComboBox, QSpinBox, QCheckBox, QPushButton, QLabel, QFrame, QGroupBox,
        QHeaderView, QStatusBar, QScrollArea, QAbstractItemView, QSizePolicy,
        QProgressBar, QTabWidget,
    )
    from PyQt5.QtCore  import Qt, QTimer, QFileSystemWatcher, QSize
    from PyQt5.QtGui   import QColor, QFont, QBrush, QPixmap, QIcon
    HAS_QT = True
except ImportError:
    HAS_QT = False


if HAS_QT:

    # ─── Column definitions ───────────────────────────────────────────────────
    COL_SPRITE =  0   # front sprite icon (no header text)
    COL_NAME   =  1
    COL_GEN    =  2
    COL_TYPE1  =  3
    COL_TYPE2  =  4
    COL_STAGE  =  5
    COL_HP     =  6
    COL_ATK    =  7
    COL_DEF    =  8
    COL_SPA    =  9
    COL_SPD    = 10
    COL_SPE    = 11
    COL_BST    = 12
    COL_STATUS = 13

    COLUMNS = [
        ("",       68),   # sprite — no header text
        ("Name",  160), ("Gen",  40), ("Type",  78), ("Type2", 78),
        ("Stage",  66), ("HP",   46), ("Atk",   46), ("Def",   46),
        ("SpA",    46), ("SpD",  46), ("Spe",   46), ("BST",   58),
        ("Status", 105),
    ]

    # ─── Numeric-sortable item ────────────────────────────────────────────────
    class NumItem(QTableWidgetItem):
        def __init__(self, val, display=None):
            super().__init__(str(val) if display is None else str(display))
            self._val = val
        def __lt__(self, other):
            if isinstance(other, NumItem): return self._val < other._val
            return super().__lt__(other)

    # ─── Filter panel ─────────────────────────────────────────────────────────
    class FilterPanel(QWidget):
        def __init__(self, parent=None):
            super().__init__(parent)
            self.setFixedWidth(230)

            scroll = QScrollArea(self)
            scroll.setWidgetResizable(True)
            scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

            inner = QWidget()
            lay   = QVBoxLayout(inner)
            lay.setContentsMargins(12, 10, 12, 10)
            lay.setSpacing(4)

            def heading(txt):
                lbl = QLabel(txt)
                lbl.setObjectName("heading")
                return lbl

            def sep():
                f = QFrame(); f.setObjectName("sep")
                f.setFrameShape(QFrame.HLine)
                return f

            # ── Search ─────────────────────────────────────────────────────
            lay.addWidget(heading("SEARCH"))
            self.search = QLineEdit()
            self.search.setPlaceholderText("Name or key…")
            self.search.setClearButtonEnabled(True)
            lay.addWidget(self.search)
            lay.addWidget(sep())

            # ── Generation ─────────────────────────────────────────────────
            lay.addWidget(heading("GENERATION"))
            self.gen_cb = QComboBox()
            self.gen_cb.addItem("All Generations", 0)
            for i in range(1, 10):
                self.gen_cb.addItem(f"Gen {i}", i)
            lay.addWidget(self.gen_cb)
            lay.addWidget(sep())

            # ── Type ───────────────────────────────────────────────────────
            lay.addWidget(heading("TYPE"))
            type_row = QHBoxLayout()
            self.type1_cb = QComboBox(); self.type2_cb = QComboBox()
            for cb in (self.type1_cb, self.type2_cb):
                cb.addItem("Any", "")
                for t in ALL_TYPES:
                    cb.addItem(t.title(), t)
            type_row.addWidget(self.type1_cb)
            type_row.addWidget(self.type2_cb)
            lay.addLayout(type_row)
            lay.addWidget(sep())

            # ── Ability ────────────────────────────────────────────────────
            lay.addWidget(heading("ABILITY"))
            self.ability_search = QLineEdit()
            self.ability_search.setPlaceholderText("Filter by ability…")
            self.ability_search.setClearButtonEnabled(True)
            lay.addWidget(self.ability_search)
            lay.addWidget(sep())

            # ── Evo Stage ──────────────────────────────────────────────────
            lay.addWidget(heading("EVO STAGE"))
            self.stage_cb = QComboBox()
            self.stage_cb.addItem("All Stages", "")
            for s in EVO_STAGES:
                self.stage_cb.addItem(s.title(), s)
            lay.addWidget(self.stage_cb)
            lay.addWidget(sep())

            # ── Status ─────────────────────────────────────────────────────
            lay.addWidget(heading("STATUS"))
            self.status_cb = QComboBox()
            self.status_cb.addItem("All Statuses", "")
            for s in STATUSES:
                self.status_cb.addItem(s.title(), s)
            lay.addWidget(self.status_cb)
            lay.addWidget(sep())

            # ── BST Range ──────────────────────────────────────────────────
            lay.addWidget(heading("BST RANGE"))
            bst_row = QHBoxLayout()
            bst_row.setSpacing(6)
            self.bst_min = QSpinBox(); self.bst_min.setRange(0, 800); self.bst_min.setValue(0)
            self.bst_max = QSpinBox(); self.bst_max.setRange(0, 800); self.bst_max.setValue(800)
            dash = QLabel("–"); dash.setAlignment(Qt.AlignCenter)
            bst_row.addWidget(self.bst_min)
            bst_row.addWidget(dash)
            bst_row.addWidget(self.bst_max)
            lay.addLayout(bst_row)
            lay.addWidget(sep())

            # ── Sort ───────────────────────────────────────────────────────
            lay.addWidget(heading("SORT BY"))
            self.sort_cb = QComboBox()
            for label, _ in SORT_FIELDS:
                self.sort_cb.addItem(label)
            self.sort_cb.setCurrentIndex(0)   # BST default
            lay.addWidget(self.sort_cb)

            self.order_cb = QComboBox()
            self.order_cb.addItem("High → Low", Qt.DescendingOrder)
            self.order_cb.addItem("Low → High",  Qt.AscendingOrder)
            lay.addWidget(self.order_cb)
            lay.addWidget(sep())

            # ── Classification ─────────────────────────────────────────────
            lay.addWidget(heading("CLASSIFICATION"))
            self.chk_legendary   = QCheckBox("Legendary")
            self.chk_mythical    = QCheckBox("Mythical")
            self.chk_ultra_beast = QCheckBox("Ultra Beast")
            self.chk_paradox     = QCheckBox("Paradox")
            for chk in (self.chk_legendary, self.chk_mythical,
                        self.chk_ultra_beast, self.chk_paradox):
                lay.addWidget(chk)
            lay.addWidget(sep())

            # ── Reset ──────────────────────────────────────────────────────
            self.reset_btn = QPushButton("Reset Filters")
            lay.addWidget(self.reset_btn)
            lay.addStretch()

            scroll.setWidget(inner)
            outer = QVBoxLayout(self)
            outer.setContentsMargins(0, 0, 0, 0)
            outer.addWidget(scroll)

        def collect(self):
            """Return a dict of current filter values."""
            return {
                'search':        self.search.text().strip().lower(),
                'ability':       self.ability_search.text().strip().lower(),
                'gen':           self.gen_cb.currentData(),
                'type1':         self.type1_cb.currentData(),
                'type2':         self.type2_cb.currentData(),
                'stage':         self.stage_cb.currentData(),
                'status':        self.status_cb.currentData(),
                'bst_min':       self.bst_min.value(),
                'bst_max':       self.bst_max.value(),
                'sort_idx':      self.sort_cb.currentIndex(),
                'sort_key':      SORT_FIELDS[self.sort_cb.currentIndex()][1],
                'order':         self.order_cb.currentData(),
                'legendary':     self.chk_legendary.isChecked(),
                'mythical':      self.chk_mythical.isChecked(),
                'ultra_beast':   self.chk_ultra_beast.isChecked(),
                'paradox':       self.chk_paradox.isChecked(),
            }

        def reset(self):
            self.search.clear()
            self.ability_search.clear()
            self.gen_cb.setCurrentIndex(0)
            self.type1_cb.setCurrentIndex(0)
            self.type2_cb.setCurrentIndex(0)
            self.stage_cb.setCurrentIndex(0)
            self.status_cb.setCurrentIndex(0)
            self.bst_min.setValue(0)
            self.bst_max.setValue(800)
            self.sort_cb.setCurrentIndex(0)
            self.order_cb.setCurrentIndex(0)
            for chk in (self.chk_legendary, self.chk_mythical,
                        self.chk_ultra_beast, self.chk_paradox):
                chk.setChecked(False)

    class MoveDetailDialog(QDialog):
        """Full detail popup for a single move: stats, description, and learners list."""

        def __init__(self, move_name_or_key, parent=None):
            super().__init__(parent)
            self.setAttribute(Qt.WA_DeleteOnClose)
            mv = move_lookup(move_name_or_key) or {}
            name = mv.get('name', move_name_or_key)
            self.setWindowTitle(f"{name}  —  Move Details")
            self.setMinimumSize(540, 500)
            self.resize(580, 560)
            self._build_ui(mv)

        def _badge(self, text, color):
            lbl = QLabel(text)
            h = color.lstrip('#')
            r, g, b = int(h[0:2],16), int(h[2:4],16), int(h[4:6],16)
            lbl.setStyleSheet(
                f"background:rgba({r},{g},{b},0.20); color:{color}; "
                f"border:1px solid rgba({r},{g},{b},0.40); "
                "border-radius:4px; padding:2px 10px; font-size:12px; font-weight:bold;"
            )
            return lbl

        def _build_ui(self, mv):
            root = QVBoxLayout(self)
            root.setContentsMargins(18, 14, 18, 14); root.setSpacing(8)

            name = mv.get('name', '—')
            name_lbl = QLabel(name)
            name_lbl.setStyleSheet("font-size:22px; font-weight:bold; color:#cdd6f4;")
            root.addWidget(name_lbl)

            t   = mv.get('type','').replace('TYPE_','')
            cat = mv.get('category','')
            badge_row = QHBoxLayout(); badge_row.setSpacing(6)
            tc = TYPE_HEX.get(t, '#585b70') if t else '#585b70'
            cat_hex = {'DAMAGE_CATEGORY_PHYSICAL':'#fab387',
                       'DAMAGE_CATEGORY_SPECIAL':'#89b4fa',
                       'DAMAGE_CATEGORY_STATUS':'#a6adc8'}.get(cat,'#a6adc8')
            cat_name = cat.replace('DAMAGE_CATEGORY_','').title() if cat else ''
            if t:
                badge_row.addWidget(self._badge(t.title(), tc))
            if cat_name:
                badge_row.addWidget(self._badge(cat_name, cat_hex))
            badge_row.addStretch()
            root.addLayout(badge_row)

            sep1 = QFrame(); sep1.setFrameShape(QFrame.HLine)
            sep1.setStyleSheet("background:#313244; max-height:1px; margin:2px 0;")
            root.addWidget(sep1)

            pw = mv.get('power',0); acc = mv.get('accuracy',0); pp = mv.get('pp',0)
            stats_row = QHBoxLayout(); stats_row.setSpacing(24)
            for label, val in [("Power", str(pw) if pw else "—"),
                                ("Accuracy", f"{acc}%" if acc else "—"),
                                ("PP", str(pp) if pp else "—")]:
                col = QVBoxLayout(); col.setSpacing(2)
                lbl = QLabel(label); lbl.setStyleSheet("color:#6c7086; font-size:11px;")
                vl  = QLabel(val);   vl.setStyleSheet("color:#cdd6f4; font-size:18px; font-weight:bold;")
                col.addWidget(lbl); col.addWidget(vl)
                stats_row.addLayout(col)
            stats_row.addStretch()
            root.addLayout(stats_row)

            desc = mv.get('description','')
            if desc:
                desc_lbl = QLabel(desc)
                desc_lbl.setWordWrap(True)
                desc_lbl.setStyleSheet(
                    "color:#a6adc8; font-size:12px; font-style:italic; "
                    "background:#181825; border-radius:6px; padding:8px 12px;"
                )
                root.addWidget(desc_lbl)

            sep2 = QFrame(); sep2.setFrameShape(QFrame.HLine)
            sep2.setStyleSheet("background:#313244; max-height:1px; margin:4px 0;")
            root.addWidget(sep2)

            learners = load_move_learners()
            entries  = learners.get(name.lower(), [])
            header   = QLabel(f"Pokémon that can learn {name}  ({len(entries)} total)")
            header.setStyleSheet("color:#89b4fa; font-size:13px; font-weight:bold;")
            root.addWidget(header)

            if entries:
                tbl = QTableWidget(len(entries), 2)
                tbl.setHorizontalHeaderLabels(["Pokémon", "How"])
                tbl.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
                tbl.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
                tbl.setEditTriggers(QAbstractItemView.NoEditTriggers)
                tbl.setSelectionBehavior(QAbstractItemView.SelectRows)
                tbl.verticalHeader().setVisible(False)
                tbl.setAlternatingRowColors(True)
                tbl.setStyleSheet(
                    "QTableWidget { background:#181825; color:#cdd6f4; border:none; "
                    "  alternate-background-color:#1e1e2e; gridline-color:#313244; }"
                    "QHeaderView::section { background:#313244; color:#a6adc8; "
                    "  border:none; padding:4px 8px; }"
                    "QTableWidget::item { padding:3px 6px; }"
                )
                for row, (species_name, method) in enumerate(entries):
                    tbl.setRowHeight(row, 22)
                    tbl.setItem(row, 0, QTableWidgetItem(species_name))
                    m_item = QTableWidgetItem(method)
                    m_item.setTextAlignment(Qt.AlignCenter)
                    if method.startswith('Lv.'):
                        m_item.setForeground(QBrush(QColor("#a6e3a1")))
                    elif method == 'Egg':
                        m_item.setForeground(QBrush(QColor("#f9e2af")))
                    else:
                        m_item.setForeground(QBrush(QColor("#89dceb")))
                    tbl.setItem(row, 1, m_item)
                root.addWidget(tbl, 1)
            else:
                no_lbl = QLabel("Not found in any Pokémon's learnset.")
                no_lbl.setStyleSheet("color:#585b70; padding:8px;")
                root.addWidget(no_lbl)
                root.addStretch()

            close_btn = QPushButton("Close"); close_btn.setFixedHeight(32)
            close_btn.clicked.connect(self.close)
            footer = QHBoxLayout()
            footer.addStretch(); footer.addWidget(close_btn)
            root.addLayout(footer)

    # ─── Pokemon Detail Dialog ────────────────────────────────────────────────
    class PokemonDetailDialog(QDialog):
        """Detail popup: full Pokédex-style layout with abilities, stats, learnset, encounters."""

        # ── Static helpers ────────────────────────────────────────────────────
        @staticmethod
        def _type_tag(type_str):
            """Return a styled QLabel type badge (clean flat tag)."""
            c = TYPE_HEX.get(type_str, '#585b70')
            lbl = QLabel(type_str.title())
            lbl.setFixedHeight(22)
            lbl.setAlignment(Qt.AlignCenter)
            lbl.setContentsMargins(10, 0, 10, 0)
            lbl.setStyleSheet(
                f"background:{c}; color:#1e1e2e; border-radius:3px; "
                "font-size:11px; font-weight:bold; padding:0 10px;"
            )
            return lbl

        @staticmethod
        def _section(title):
            """A QGroupBox styled as a clean titled section with a border."""
            gb = QGroupBox(title)
            gb.setStyleSheet(
                "QGroupBox { color:#6c7086; font-size:10px; font-weight:bold; "
                "  border:1px solid #313244; border-radius:6px; "
                "  margin-top:14px; padding-top:6px; }"
                "QGroupBox::title { subcontrol-origin:margin; subcontrol-position:top left; "
                "  left:10px; padding:0 4px; background:#1e1e2e; }"
            )
            return gb

        # ── Constructor ───────────────────────────────────────────────────────
        def __init__(self, pokemon, sprite_data, status, status_callback, parent=None):
            super().__init__(parent)
            self.setAttribute(Qt.WA_DeleteOnClose)
            self._pokemon    = pokemon
            self._status     = status
            self._cb         = status_callback
            self._shiny      = False
            self._normal_pix = None
            self._shiny_pix  = None
            self._front_path = sprite_data[0] if sprite_data else ''
            self._learnset_loaded   = False
            self._encounters_loaded = False
            self._evo_loaded        = False

            self.setWindowTitle(f"{pokemon.display_name}  ·  Pokédex Entry")
            self.setMinimumSize(780, 600)
            self.resize(920, 700)
            self._build_ui(pokemon)
            self._load_sprite()

        # ── Top-level layout ──────────────────────────────────────────────────
        def _build_ui(self, p):
            root = QVBoxLayout(self)
            root.setContentsMargins(0, 0, 0, 0)
            root.setSpacing(0)

            # ── Header strip ─────────────────────────────────────────────────
            root.addWidget(self._build_header(p))

            # ── Body ─────────────────────────────────────────────────────────
            body_frame = QFrame()
            body_frame.setStyleSheet("QFrame { background:#1e1e2e; border:none; }")
            body_lay = QHBoxLayout(body_frame)
            body_lay.setContentsMargins(16, 14, 16, 10)
            body_lay.setSpacing(18)

            body_lay.addWidget(self._build_left_col(p), 0)
            body_lay.addWidget(self._build_right_col(p), 1)
            root.addWidget(body_frame, 1)

            # ── Flavor text strip ─────────────────────────────────────────────
            if p.description:
                root.addWidget(self._build_flavor(p.description))

            # ── Footer: status + close ────────────────────────────────────────
            root.addWidget(self._build_footer())

        # ── Header ───────────────────────────────────────────────────────────
        def _build_header(self, p):
            hdr = QFrame()
            hdr.setFixedHeight(88)
            hdr.setStyleSheet(
                "QFrame { background:#181825; border-bottom:1px solid #313244; border-radius:0; }"
            )
            lay = QHBoxLayout(hdr)
            lay.setContentsMargins(14, 8, 16, 8)
            lay.setSpacing(14)

            # Sprite thumbnail
            self._hdr_sprite = QLabel()
            self._hdr_sprite.setFixedSize(72, 72)
            self._hdr_sprite.setAlignment(Qt.AlignCenter)
            self._hdr_sprite.setStyleSheet("background:transparent; border:none;")
            lay.addWidget(self._hdr_sprite)

            # Name block
            name_block = QVBoxLayout()
            name_block.setSpacing(2)
            name_lbl = QLabel(p.display_name)
            name_lbl.setStyleSheet(
                "font-size:26px; font-weight:bold; color:#cdd6f4; "
                "background:transparent; border:none;"
            )
            name_block.addWidget(name_lbl)

            sub_row = QHBoxLayout(); sub_row.setSpacing(8)
            if p.nat_dex:
                dex_lbl = QLabel(f"#{p.nat_dex:04d}")
                dex_lbl.setStyleSheet(
                    "font-size:13px; color:#6c7086; background:transparent; border:none;")
                sub_row.addWidget(dex_lbl)
            if p.category:
                cat_lbl = QLabel(f"{p.category} Pokémon")
                cat_lbl.setStyleSheet(
                    "font-size:13px; color:#a6adc8; font-style:italic; "
                    "background:transparent; border:none;")
                sub_row.addWidget(cat_lbl)
            sub_row.addStretch()
            name_block.addLayout(sub_row)
            lay.addLayout(name_block)
            lay.addStretch()

            # Right side: type tags + gen/stage
            right_tags = QVBoxLayout(); right_tags.setSpacing(6)
            right_tags.addStretch()

            types_row = QHBoxLayout(); types_row.setSpacing(6)
            for t in filter(None, [p.type1, p.type2]):
                types_row.addWidget(self._type_tag(t))
            right_tags.addLayout(types_row)

            meta_row = QHBoxLayout(); meta_row.setSpacing(6)
            if p.gen:
                gen_c = GEN_HEX.get(p.gen, '#a6adc8')
                gen_l = QLabel(f"Gen {p.gen}")
                gen_l.setStyleSheet(
                    f"color:{gen_c}; font-size:11px; font-weight:bold; "
                    "background:transparent; border:none;")
                meta_row.addWidget(gen_l)
            if p.stage and p.stage != 'SINGLE':
                stage_map = {'BASIC':'Base form','MIDDLE':'Mid-stage','FINAL':'Final form'}
                stage_c   = {'BASIC':'#a6e3a1','MIDDLE':'#f9e2af','FINAL':'#cba6f7'}.get(p.stage,'#6c7086')
                st_l = QLabel(stage_map.get(p.stage, p.stage.title()))
                st_l.setStyleSheet(
                    f"color:{stage_c}; font-size:11px; background:transparent; border:none;")
                meta_row.addWidget(st_l)
            # Special tags
            if p.is_legendary:
                sl = QLabel("★ Legendary"); sl.setStyleSheet(
                    "color:#fab387; font-size:11px; font-weight:bold; "
                    "background:transparent; border:none;")
                meta_row.addWidget(sl)
            elif p.is_mythical:
                sl = QLabel("✦ Mythical"); sl.setStyleSheet(
                    "color:#f9e2af; font-size:11px; font-weight:bold; "
                    "background:transparent; border:none;")
                meta_row.addWidget(sl)
            elif p.is_ultra_beast:
                sl = QLabel("◆ Ultra Beast"); sl.setStyleSheet(
                    "color:#89dceb; font-size:11px; font-weight:bold; "
                    "background:transparent; border:none;")
                meta_row.addWidget(sl)
            elif p.is_paradox:
                sl = QLabel("◈ Paradox"); sl.setStyleSheet(
                    "color:#cba6f7; font-size:11px; font-weight:bold; "
                    "background:transparent; border:none;")
                meta_row.addWidget(sl)
            right_tags.addLayout(meta_row)
            right_tags.addStretch()
            lay.addLayout(right_tags)
            return hdr

        # ── Left column ───────────────────────────────────────────────────────
        def _build_left_col(self, p):
            col = QWidget(); col.setFixedWidth(220)
            col.setStyleSheet("QWidget { background:transparent; border:none; }")
            lay = QVBoxLayout(col)
            lay.setContentsMargins(0, 0, 0, 0)
            lay.setSpacing(10)

            # Sprite
            sprite_frame = QFrame()
            sprite_frame.setFixedSize(210, 210)
            sprite_frame.setStyleSheet(
                "QFrame { background:#181825; border:1px solid #313244; border-radius:10px; }"
            )
            sf_lay = QVBoxLayout(sprite_frame)
            sf_lay.setContentsMargins(0, 0, 0, 0)
            self.front_img = QLabel()
            self.front_img.setFixedSize(208, 208)
            self.front_img.setAlignment(Qt.AlignCenter)
            self.front_img.setStyleSheet("background:transparent; border:none; color:#585b70;")
            sf_lay.addWidget(self.front_img)
            lay.addWidget(sprite_frame, 0, Qt.AlignHCenter)

            # Shiny toggle
            self.shiny_btn = QPushButton("Normal")
            self.shiny_btn.setCheckable(True)
            self.shiny_btn.setFixedHeight(30)
            self.shiny_btn.setStyleSheet(
                "QPushButton { background:#252536; border:1px solid #45475a; "
                "border-radius:6px; padding:5px 12px; color:#a6adc8; font-size:12px; }"
                "QPushButton:checked { background:#2e2a1a; border-color:#f9e2af; color:#f9e2af; }"
                "QPushButton:hover { background:#313244; }"
            )
            self.shiny_btn.clicked.connect(self._toggle_shiny)
            lay.addWidget(self.shiny_btn)

            # Physical data card
            phys_sec = self._section("Physical Data")
            phys_lay = QVBoxLayout()
            phys_lay.setContentsMargins(10, 4, 10, 8)
            phys_lay.setSpacing(6)

            def _stat_row(label, value):
                row = QHBoxLayout()
                lbl = QLabel(label)
                lbl.setStyleSheet("color:#6c7086; font-size:11px; background:transparent; border:none;")
                lbl.setFixedWidth(78)
                val = QLabel(value)
                val.setStyleSheet("color:#cdd6f4; font-size:12px; font-weight:bold; background:transparent; border:none;")
                val.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
                row.addWidget(lbl); row.addWidget(val)
                return row

            if p.height:
                phys_lay.addLayout(_stat_row("Height", f"{p.height/10:.1f} m"))
                phys_lay.addLayout(_stat_row("Weight", f"{p.weight/10:.1f} kg"))
            if p.catch_rate:
                cr_pct = round(p.catch_rate / 255 * 100)
                phys_lay.addLayout(_stat_row("Catch Rate", f"{p.catch_rate}  ({cr_pct}%)"))

            phys_sec.setLayout(phys_lay)
            lay.addWidget(phys_sec)
            lay.addStretch()
            return col

        # ── Right column (tabbed) ─────────────────────────────────────────────
        def _build_right_col(self, p):
            tabs = QTabWidget()
            tabs.setStyleSheet(
                "QTabWidget::pane { border:1px solid #313244; border-radius:6px; "
                "  background:#1e1e2e; margin-top:-1px; }"
                "QTabBar::tab { background:#181825; color:#a6adc8; padding:7px 18px; "
                "  border:1px solid #313244; border-bottom:none; border-radius:6px 6px 0 0; "
                "  margin-right:2px; font-size:12px; font-weight:bold; }"
                "QTabBar::tab:selected { background:#1e1e2e; color:#cdd6f4; "
                "  border-bottom:1px solid #1e1e2e; }"
                "QTabBar::tab:hover:!selected { background:#252536; }"
            )

            # Profile tab
            profile_w = QWidget()
            profile_w.setStyleSheet("QWidget { background:transparent; border:none; }")
            pf_lay = QVBoxLayout(profile_w)
            pf_lay.setContentsMargins(12, 12, 12, 12)
            pf_lay.setSpacing(12)
            self._build_profile_tab(pf_lay, p)
            tabs.addTab(profile_w, "Profile")

            # Learnset tab (lazy)
            self._learnset_tab = QWidget()
            self._learnset_tab.setStyleSheet("QWidget { background:transparent; border:none; }")
            self._learnset_lay = QVBoxLayout(self._learnset_tab)
            self._learnset_lay.setContentsMargins(8, 8, 8, 8)
            tabs.addTab(self._learnset_tab, "Learnset")

            # Encounters tab (lazy)
            self._encounters_tab = QWidget()
            self._encounters_tab.setStyleSheet("QWidget { background:transparent; border:none; }")
            self._encounters_lay = QVBoxLayout(self._encounters_tab)
            self._encounters_lay.setContentsMargins(8, 8, 8, 8)
            tabs.addTab(self._encounters_tab, "Encounters")

            # Evolution tab (lazy)
            self._evo_tab = QWidget()
            self._evo_tab.setStyleSheet("QWidget { background:transparent; border:none; }")
            self._evo_lay = QVBoxLayout(self._evo_tab)
            self._evo_lay.setContentsMargins(0, 0, 0, 0)
            tabs.addTab(self._evo_tab, "Evolution")

            tabs.currentChanged.connect(self._on_tab_changed)
            return tabs

        # ── Profile tab ───────────────────────────────────────────────────────
        def _build_profile_tab(self, lay, p):
            # ── Abilities ────────────────────────────────────────────────────
            ab_sec = self._section("Abilities")
            ab_inner = QHBoxLayout()
            ab_inner.setContentsMargins(10, 4, 10, 10)
            ab_inner.setSpacing(10)

            ability_info = load_ability_info()
            slot_labels = ["Ability 1", "Ability 2", "Hidden Ability"]
            slot_colors = ["#89b4fa", "#89b4fa", "#cba6f7"]

            for i in range(3):
                ab_name = p.abilities[i] if i < len(p.abilities) else ''
                card = QFrame()
                card.setStyleSheet(
                    "QFrame { background:#181825; border:1px solid #313244; border-radius:6px; }"
                )
                card_lay = QVBoxLayout(card)
                card_lay.setContentsMargins(10, 8, 10, 8)
                card_lay.setSpacing(3)

                # Slot label
                slot_lbl = QLabel(slot_labels[i])
                slot_lbl.setStyleSheet(
                    f"color:{slot_colors[i]}; font-size:9px; font-weight:bold; "
                    "text-transform:uppercase; letter-spacing:1px; "
                    "background:transparent; border:none;"
                )
                card_lay.addWidget(slot_lbl)

                if ab_name:
                    name_lbl = QLabel(ab_name)
                    name_lbl.setStyleSheet(
                        "color:#cdd6f4; font-size:13px; font-weight:bold; "
                        "background:transparent; border:none;"
                    )
                    card_lay.addWidget(name_lbl)

                    info = ability_info.get(ab_name.lower().replace(' ','_'), {})
                    if not info:
                        info = ability_info.get(ab_name.lower(), {})
                    desc_text = info.get('desc', '')
                    if desc_text:
                        desc_lbl = QLabel(desc_text)
                        desc_lbl.setWordWrap(True)
                        desc_lbl.setStyleSheet(
                            "color:#a6adc8; font-size:11px; "
                            "background:transparent; border:none; "
                            "line-height:1.4;"
                        )
                        card_lay.addWidget(desc_lbl)
                    card_lay.addStretch()
                else:
                    empty_lbl = QLabel("—")
                    empty_lbl.setStyleSheet(
                        "color:#45475a; font-size:18px; "
                        "background:transparent; border:none;"
                    )
                    card_lay.addWidget(empty_lbl)
                    card_lay.addStretch()

                ab_inner.addWidget(card, 1)

            ab_sec.setLayout(ab_inner)
            lay.addWidget(ab_sec)

            # ── Base Stats ────────────────────────────────────────────────────
            stats_sec = self._section("Base Stats")
            stats_inner = QVBoxLayout()
            stats_inner.setContentsMargins(12, 4, 12, 10)
            stats_inner.setSpacing(5)

            stat_defs = [
                ("HP",       p.hp,   "#f38ba8"),
                ("Attack",   p.atk,  "#fab387"),
                ("Defense",  p.def_, "#f9e2af"),
                ("Sp. Atk",  p.spa,  "#a6e3a1"),
                ("Sp. Def",  p.spd,  "#89dceb"),
                ("Speed",    p.spe,  "#89b4fa"),
            ]

            max_val = 255
            for stat_name, val, color in stat_defs:
                row = QHBoxLayout(); row.setSpacing(8)

                nl = QLabel(stat_name)
                nl.setFixedWidth(56)
                nl.setStyleSheet(
                    "color:#bac2de; font-size:12px; background:transparent; border:none;"
                )

                vl = QLabel(str(val))
                vl.setFixedWidth(36)
                vl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
                vl.setStyleSheet(
                    f"color:{color}; font-weight:bold; font-size:13px; "
                    "background:transparent; border:none;"
                )

                bar = QProgressBar()
                bar.setRange(0, max_val); bar.setValue(val)
                bar.setFixedHeight(10); bar.setTextVisible(False)
                bar.setStyleSheet(
                    f"QProgressBar {{ background:#252536; border:none; border-radius:4px; }}"
                    f"QProgressBar::chunk {{ background:{color}; border-radius:4px; }}"
                )

                if val < 50:     rating, rc = "Very Low",  "#585b70"
                elif val < 70:   rating, rc = "Low",       "#a6adc8"
                elif val < 90:   rating, rc = "Average",   "#cdd6f4"
                elif val < 120:  rating, rc = "High",      "#a6e3a1"
                else:            rating, rc = "Very High", "#f9e2af"
                rl = QLabel(rating)
                rl.setFixedWidth(66)
                rl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
                rl.setStyleSheet(
                    f"color:{rc}; font-size:10px; background:transparent; border:none;"
                )

                row.addWidget(nl); row.addWidget(vl); row.addWidget(bar, 1); row.addWidget(rl)
                stats_inner.addLayout(row)

            # BST total row
            bst_row = QHBoxLayout()
            divider = QFrame(); divider.setFrameShape(QFrame.HLine)
            divider.setStyleSheet("background:#313244; max-height:1px; border:none; margin:2px 0;")
            stats_inner.addWidget(divider)

            bst_lbl = QLabel("Total")
            bst_lbl.setStyleSheet("color:#6c7086; font-size:11px; font-weight:bold; background:transparent; border:none;")
            bst_lbl.setFixedWidth(56)
            bst_val = QLabel(str(p.bst))
            bst_val.setStyleSheet(
                f"color:{bst_color(p.bst)}; font-size:18px; font-weight:bold; "
                "background:transparent; border:none;"
            )
            bst_row.addWidget(bst_lbl); bst_row.addWidget(bst_val); bst_row.addStretch()
            stats_inner.addLayout(bst_row)

            stats_sec.setLayout(stats_inner)
            lay.addWidget(stats_sec)
            lay.addStretch()

        # ── Flavor text ───────────────────────────────────────────────────────
        def _build_flavor(self, description):
            frame = QFrame()
            frame.setStyleSheet(
                "QFrame { background:#181825; border-top:1px solid #313244; border-radius:0; }"
            )
            lay = QHBoxLayout(frame)
            lay.setContentsMargins(20, 10, 20, 10)

            quote_mark = QLabel("\u201c")
            quote_mark.setStyleSheet(
                "color:#313244; font-size:36px; line-height:1; "
                "background:transparent; border:none;"
            )
            quote_mark.setFixedWidth(24)
            quote_mark.setAlignment(Qt.AlignTop)
            lay.addWidget(quote_mark)

            desc_lbl = QLabel(description)
            desc_lbl.setWordWrap(True)
            desc_lbl.setStyleSheet(
                "color:#bac2de; font-size:12px; font-style:italic; "
                "background:transparent; border:none; line-height:1.5;"
            )
            lay.addWidget(desc_lbl, 1)
            return frame

        # ── Footer: status + close ────────────────────────────────────────────
        def _build_footer(self):
            footer = QFrame()
            footer.setFixedHeight(52)
            footer.setStyleSheet(
                "QFrame { background:#181825; border-top:1px solid #313244; border-radius:0; }"
            )
            lay = QHBoxLayout(footer)
            lay.setContentsMargins(16, 8, 16, 8)
            lay.setSpacing(10)

            status_lbl_title = QLabel("Balance Status:")
            status_lbl_title.setStyleSheet(
                "color:#6c7086; font-size:11px; background:transparent; border:none;")
            lay.addWidget(status_lbl_title)

            self.status_badge = QLabel(self._status)
            s_color = STATUS_HEX.get(self._status, '#6c7086')
            self.status_badge.setStyleSheet(
                f"color:{s_color}; font-size:12px; font-weight:bold; "
                "background:transparent; border:none;"
            )
            lay.addWidget(self.status_badge)

            cycle_btn = QPushButton("Change")
            cycle_btn.setFixedHeight(28)
            cycle_btn.setFixedWidth(70)
            cycle_btn.setStyleSheet(
                "QPushButton { background:#313244; border:1px solid #45475a; border-radius:4px; "
                "  color:#a6adc8; font-size:11px; }"
                "QPushButton:hover { background:#45475a; }"
            )
            cycle_btn.clicked.connect(self._cycle_status)
            lay.addWidget(cycle_btn)

            lay.addStretch()

            close_btn = QPushButton("Close")
            close_btn.setFixedHeight(32)
            close_btn.setFixedWidth(80)
            close_btn.setStyleSheet(
                "QPushButton { background:#313244; border:1px solid #45475a; border-radius:6px; "
                "  color:#cdd6f4; font-size:12px; }"
                "QPushButton:hover { background:#45475a; }"
            )
            close_btn.clicked.connect(self.close)
            lay.addWidget(close_btn)
            return footer

        # ── Lazy tab loading ──────────────────────────────────────────────────
        def _on_tab_changed(self, idx):
            if idx == 1 and not self._learnset_loaded:
                self._learnset_loaded = True
                self._populate_learnset_tab(self._pokemon)
            elif idx == 2 and not self._encounters_loaded:
                self._encounters_loaded = True
                self._populate_encounters_tab(self._pokemon)
            elif idx == 3 and not self._evo_loaded:
                self._evo_loaded = True
                self._populate_evo_tab(self._pokemon)

        def _populate_encounters_tab(self, p):
            lay = self._encounters_lay
            encounters = load_wild_encounters()
            entries = encounters.get(p.key, [])
            if not entries:
                no_lbl = QLabel("Not found in any wild encounter table.")
                no_lbl.setStyleSheet("color:#585b70; padding:16px; font-size:12px;")
                lay.addWidget(no_lbl); lay.addStretch(); return

            tbl = QTableWidget(len(entries), 4)
            tbl.setHorizontalHeaderLabels(["Location", "Method", "Levels", "%"])
            tbl.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
            tbl.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
            tbl.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
            tbl.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
            tbl.setEditTriggers(QAbstractItemView.NoEditTriggers)
            tbl.setSelectionBehavior(QAbstractItemView.SelectRows)
            tbl.setAlternatingRowColors(True)
            tbl.verticalHeader().setVisible(False)
            tbl.setStyleSheet(
                "QTableWidget { background:#181825; color:#cdd6f4; border:none; "
                "  alternate-background-color:#1e1e2e; gridline-color:#313244; }"
                "QHeaderView::section { background:#181825; color:#89b4fa; font-size:11px; "
                "  font-weight:bold; border:none; border-bottom:1px solid #313244; padding:5px 8px; }"
                "QTableWidget::item { padding:4px 8px; }"
            )
            for row, (map_lbl, table_type, min_l, max_l, pct) in enumerate(entries):
                tbl.setItem(row, 0, QTableWidgetItem(map_lbl))
                tbl.setItem(row, 1, QTableWidgetItem(table_type))
                lvl_range = f"{min_l}\u2013{max_l}" if min_l != max_l else str(min_l)
                lv_item = QTableWidgetItem(lvl_range)
                lv_item.setTextAlignment(Qt.AlignCenter)
                tbl.setItem(row, 2, lv_item)
                pct_item = QTableWidgetItem(f"{pct}%")
                pct_item.setTextAlignment(Qt.AlignCenter)
                tbl.setItem(row, 3, pct_item)
            lay.addWidget(tbl)

        # ── Evolution tab ─────────────────────────────────────────────────────
        def _populate_evo_tab(self, p):
            lay = self._evo_lay
            forward, backward = load_evo_chains()

            # Build a lookup: UPPER_KEY → Pokemon for the chain renderer
            all_pkmn = {pk.key.upper(): pk for pk in load_all_pokemon()}

            # Walk backward to find root of this Pokémon's chain
            def _chain_root(key):
                visited = set()
                while key in backward and key not in visited:
                    visited.add(key)
                    key = backward[key]
                return key

            root_key = _chain_root(p.key)
            has_chain = (root_key in forward) or (p.key in backward)

            if not has_chain and p.key not in forward:
                lbl = QLabel("Does not evolve.")
                lbl.setAlignment(Qt.AlignCenter)
                lbl.setStyleSheet("color:#585b70; font-size:13px; padding:24px;")
                lay.addWidget(lbl)
                lay.addStretch()
                return

            # Scroll area wrapping the chain canvas
            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            scroll.setStyleSheet("QScrollArea { border:none; background:#1e1e2e; }")
            canvas = QWidget()
            canvas.setStyleSheet("background:#1e1e2e;")
            canvas_lay = QVBoxLayout(canvas)
            canvas_lay.setContentsMargins(18, 18, 18, 18)
            canvas_lay.setSpacing(12)
            canvas_lay.setAlignment(Qt.AlignTop | Qt.AlignLeft)

            # Chain title
            chain_hdr = QLabel("EVOLUTIONARY LINE")
            chain_hdr.setObjectName("heading")
            canvas_lay.addWidget(chain_hdr)

            # Horizontal chain row
            chain_row = QWidget()
            chain_row.setStyleSheet("background:transparent;")
            chain_h = QHBoxLayout(chain_row)
            chain_h.setContentsMargins(0, 0, 0, 0)
            chain_h.setSpacing(0)
            chain_h.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            self._render_evo_node(chain_h, root_key, forward, all_pkmn, p.key, depth=0)
            chain_h.addStretch()
            canvas_lay.addWidget(chain_row)

            # Stage legend
            canvas_lay.addSpacing(8)
            sep = QFrame()
            sep.setFrameShape(QFrame.HLine)
            sep.setStyleSheet("background:#313244; border:none; max-height:1px;")
            canvas_lay.addWidget(sep)
            canvas_lay.addSpacing(6)

            legend_hdr = QLabel("STAGE LEGEND")
            legend_hdr.setObjectName("heading")
            canvas_lay.addWidget(legend_hdr)
            legend_row = QHBoxLayout()
            legend_row.setSpacing(20)
            for stage, color in [("Basic", "#a6e3a1"), ("Middle", "#89b4fa"),
                                  ("Final", "#cba6f7"), ("Single", "#f9e2af")]:
                dot = QLabel(f"● {stage}")
                dot.setStyleSheet(
                    f"color:{color}; font-size:11px; font-weight:bold; background:transparent;"
                )
                legend_row.addWidget(dot)
            legend_row.addStretch()
            canvas_lay.addLayout(legend_row)
            canvas_lay.addStretch()

            scroll.setWidget(canvas)
            lay.addWidget(scroll)

        def _render_evo_node(self, parent_lay, key, forward, all_pkmn, current_key, depth):
            """Recursively render a species card + its evolution branches."""
            if depth > 6:
                return
            parent_lay.addWidget(self._evo_species_card(key, all_pkmn, key == current_key))

            evolutions = forward.get(key, [])
            if not evolutions:
                return

            if len(evolutions) == 1:
                evo = evolutions[0]
                parent_lay.addWidget(self._evo_arrow(evo['label'], evo['conditions']))
                self._render_evo_node(parent_lay, evo['target'], forward, all_pkmn,
                                      current_key, depth + 1)
            else:
                branches_w = QWidget()
                branches_w.setStyleSheet("background:transparent;")
                v_lay = QVBoxLayout(branches_w)
                v_lay.setContentsMargins(0, 0, 0, 0)
                v_lay.setSpacing(6)
                for evo in evolutions:
                    row_w = QWidget()
                    row_w.setStyleSheet("background:transparent;")
                    row_h = QHBoxLayout(row_w)
                    row_h.setContentsMargins(0, 0, 0, 0)
                    row_h.setSpacing(0)
                    row_h.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
                    row_h.addWidget(self._evo_arrow(evo['label'], evo['conditions']))
                    self._render_evo_node(row_h, evo['target'], forward, all_pkmn,
                                          current_key, depth + 1)
                    row_h.addStretch()
                    v_lay.addWidget(row_w)
                parent_lay.addWidget(branches_w)

        def _evo_species_card(self, key, all_pkmn, is_current):
            """Build a species card widget for the evolution chain."""
            sp = all_pkmn.get(key)
            stage = getattr(sp, 'stage', 'SINGLE') if sp else 'SINGLE'
            stage_colors = {
                'BASIC': '#a6e3a1', 'MIDDLE': '#89b4fa',
                'FINAL': '#cba6f7', 'SINGLE': '#f9e2af',
            }
            border_color = '#89b4fa' if is_current else '#313244'
            stage_color  = stage_colors.get(stage, '#585b70')

            frame = QFrame()
            frame.setFixedSize(88, 118)
            frame.setStyleSheet(
                f"QFrame {{ background:#181825; border:2px solid {border_color}; "
                f"border-radius:8px; }}"
            )
            lay = QVBoxLayout(frame)
            lay.setContentsMargins(4, 4, 4, 4)
            lay.setSpacing(2)
            lay.setAlignment(Qt.AlignCenter)

            # Sprite
            spr_lbl = QLabel()
            spr_lbl.setFixedSize(58, 58)
            spr_lbl.setAlignment(Qt.AlignCenter)
            spr_lbl.setStyleSheet("background:transparent; border:none;")
            front, _ = find_sprite_for_key(key.lower())
            if front and os.path.isfile(front):
                raw = QPixmap(front)
                if not raw.isNull():
                    if raw.height() > raw.width():
                        raw = raw.copy(0, 0, raw.width(), raw.width())
                    raw = make_transparent_pixmap(raw)
                    spr_lbl.setPixmap(_pixel_perfect(raw, 56, 56))
            else:
                spr_lbl.setText("?")
                spr_lbl.setStyleSheet(
                    "color:#45475a; font-size:18px; background:transparent; border:none;"
                )
            lay.addWidget(spr_lbl)

            # Name
            name = sp.name if sp else key.replace('_', ' ').title()
            name_lbl = QLabel(name)
            name_lbl.setAlignment(Qt.AlignCenter)
            name_lbl.setWordWrap(True)
            name_color = '#89b4fa' if is_current else '#cdd6f4'
            name_lbl.setStyleSheet(
                f"color:{name_color}; font-size:9px; font-weight:bold; "
                "background:transparent; border:none;"
            )
            lay.addWidget(name_lbl)

            # Stage dot + type badges in one row
            meta_row = QHBoxLayout()
            meta_row.setSpacing(2)
            meta_row.setAlignment(Qt.AlignCenter)
            stage_dot = QLabel("●")
            stage_dot.setStyleSheet(
                f"color:{stage_color}; font-size:9px; background:transparent; border:none;"
            )
            meta_row.addWidget(stage_dot)
            if sp:
                for t in filter(None, [sp.type1, sp.type2 if sp.type2 else ""]):
                    c    = TYPE_HEX.get(t.upper(), '#585b70')
                    tbdg = QLabel(t.title())
                    tbdg.setStyleSheet(
                        f"background:{c}; color:#1e1e2e; font-weight:bold; font-size:7px; "
                        "border-radius:2px; padding:1px 3px; border:none;"
                    )
                    tbdg.setAlignment(Qt.AlignCenter)
                    meta_row.addWidget(tbdg)
            lay.addLayout(meta_row)
            return frame

        @staticmethod
        def _evo_arrow(label, conditions):
            """Build an arrow widget showing the evo method and conditions."""
            w = QWidget()
            w.setStyleSheet("background:transparent;")
            v = QVBoxLayout(w)
            v.setContentsMargins(6, 0, 6, 0)
            v.setSpacing(2)
            v.setAlignment(Qt.AlignCenter)

            arr = QLabel(f"── {label} ──▶")
            arr.setAlignment(Qt.AlignCenter)
            arr.setStyleSheet(
                "color:#89b4fa; font-size:10px; font-weight:bold; "
                "background:transparent; border:none;"
            )
            v.addWidget(arr)

            for cond in conditions:
                cl = QLabel(cond)
                cl.setAlignment(Qt.AlignCenter)
                cl.setStyleSheet(
                    "color:#f9e2af; font-size:9px; background:transparent; border:none;"
                )
                v.addWidget(cl)
            return w

        def _populate_learnset_tab(self, p):
            lay = self._learnset_lay
            learnsets = load_learnsets()
            lkey = species_to_learnset_key(p.key)
            data = learnsets.get(lkey, {})

            def _open_move_detail_from_table(tbl, pos, name_col):
                item = tbl.itemAt(pos)
                if not item: return
                nm_item = tbl.item(item.row(), name_col)
                if not nm_item: return
                dlg = MoveDetailDialog(nm_item.text(), parent=self)
                dlg.exec_()

            sub = QTabWidget()
            sub.setStyleSheet(
                "QTabWidget::pane { border:none; background:#181825; }"
                "QTabBar::tab { background:#181825; color:#a6adc8; padding:5px 14px; "
                "  border:none; border-bottom:2px solid transparent; font-size:12px; font-weight:bold; }"
                "QTabBar::tab:selected { color:#89b4fa; border-bottom-color:#89b4fa; }"
                "QTabBar::tab:hover:!selected { background:#252536; }"
            )

            _TBL_STYLE = (
                "QTableWidget { background:#181825; color:#cdd6f4; border:none; "
                "  alternate-background-color:#1e1e2e; gridline-color:#2a2a3c; }"
                "QTableWidget::item { padding:3px 6px; }"
                "QHeaderView::section { background:#181825; color:#89b4fa; font-size:11px; "
                "  font-weight:bold; padding:5px 6px; border:none; "
                "  border-bottom:1px solid #313244; }"
            )

            def make_move_table(data_rows, headers, col_widths):
                tbl = QTableWidget(len(data_rows), len(headers))
                tbl.setHorizontalHeaderLabels(headers)
                tbl.setEditTriggers(QAbstractItemView.NoEditTriggers)
                tbl.setSelectionBehavior(QAbstractItemView.SelectRows)
                tbl.verticalHeader().setVisible(False)
                tbl.setAlternatingRowColors(True)
                tbl.setStyleSheet(_TBL_STYLE)
                for i, w in enumerate(col_widths):
                    if w == -1: tbl.horizontalHeader().setSectionResizeMode(i, QHeaderView.Stretch)
                    else: tbl.setColumnWidth(i, w)
                return tbl

            def fill_move_row(tbl, i, mv_key, extra_first=None):
                tbl.setRowHeight(i, 24)
                mv = move_lookup(mv_key)
                name  = mv.get('name', mv_key) if mv else mv_key
                mtype = mv.get('type','').replace('TYPE_','') if mv else ''
                mcat  = mv.get('category','') if mv else ''
                mpow  = mv.get('power', 0) if mv else 0
                macc  = mv.get('accuracy', 0) if mv else 0
                tc    = TYPE_HEX.get(mtype, '#585b70') if mtype else '#585b70'
                col = 0
                if extra_first is not None:
                    ei = NumItem(extra_first)
                    ei.setTextAlignment(Qt.AlignCenter)
                    tbl.setItem(i, col, ei); col += 1
                tbl.setItem(i, col, QTableWidgetItem(name)); col += 1
                ty_i = QTableWidgetItem(mtype.title() if mtype else '\u2014')
                ty_i.setForeground(QBrush(QColor(tc))); ty_i.setTextAlignment(Qt.AlignCenter)
                tbl.setItem(i, col, ty_i); col += 1
                cat_d = mcat.replace('DAMAGE_CATEGORY_','').title() if mcat else '\u2014'
                ci = QTableWidgetItem(cat_d); ci.setTextAlignment(Qt.AlignCenter)
                tbl.setItem(i, col, ci); col += 1
                pi = NumItem(mpow, str(mpow) if mpow else '\u2014'); pi.setTextAlignment(Qt.AlignCenter)
                tbl.setItem(i, col, pi); col += 1
                ai = NumItem(macc, f"{macc}%" if macc else '\u2014'); ai.setTextAlignment(Qt.AlignCenter)
                tbl.setItem(i, col, ai)

            # Level-Up
            lu_data = sorted(data.get('levelup',[]), key=lambda x: x[0])
            if lu_data:
                lu_tbl = make_move_table(lu_data,
                    ["Lv.", "Move", "Type", "Cat.", "Pwr", "Acc"],
                    [40, -1, 75, 72, 46, 52])
                lu_tbl.setContextMenuPolicy(Qt.CustomContextMenu)
                lu_tbl.customContextMenuRequested.connect(
                    lambda pos, t=lu_tbl: _open_move_detail_from_table(t, pos, 1))
                for i, (lvl, mk) in enumerate(lu_data):
                    fill_move_row(lu_tbl, i, mk, extra_first=lvl)
                sub.addTab(lu_tbl, f"Level-Up  ({len(lu_data)})")

            # Egg
            egg_data = data.get('egg', [])
            if egg_data:
                egg_tbl = make_move_table(egg_data,
                    ["Move", "Type", "Cat.", "Pwr", "Acc"],
                    [-1, 75, 72, 46, 52])
                egg_tbl.setContextMenuPolicy(Qt.CustomContextMenu)
                egg_tbl.customContextMenuRequested.connect(
                    lambda pos, t=egg_tbl: _open_move_detail_from_table(t, pos, 0))
                for i, mk in enumerate(egg_data):
                    fill_move_row(egg_tbl, i, mk)
                sub.addTab(egg_tbl, f"Egg  ({len(egg_data)})")

            def _build_move_tab(data_keys, label):
                if not data_keys: return
                tbl = make_move_table(data_keys,
                    ["Move", "Type", "Cat.", "Pwr", "Acc"],
                    [-1, 75, 72, 46, 52])
                tbl.setContextMenuPolicy(Qt.CustomContextMenu)
                tbl.customContextMenuRequested.connect(
                    lambda pos, t=tbl: _open_move_detail_from_table(t, pos, 0))
                for i, mk in enumerate(data_keys):
                    fill_move_row(tbl, i, mk)
                sub.addTab(tbl, f"{label}  ({len(data_keys)})")

            _build_move_tab(data.get('tm', []),    "TM / HM")
            _build_move_tab(data.get('tutor', []), "Tutor")

            if sub.count() == 0:
                no_data = QLabel("No learnset data found.")
                no_data.setStyleSheet("color:#585b70; font-size:13px; padding:20px;")
                no_data.setAlignment(Qt.AlignCenter)
                lay.addWidget(no_data)
            else:
                lay.addWidget(sub)

        # ── Sprite helpers ────────────────────────────────────────────────────
        def _load_sprite(self):
            path = self._front_path
            if path and os.path.isfile(path):
                raw = QPixmap(path)
                if not raw.isNull():
                    if raw.height() > raw.width():
                        raw = raw.copy(0, 0, raw.width(), raw.width())
                    raw = make_transparent_pixmap(raw)
                    self._normal_pix = raw
                    self._render_sprite()
                    self._hdr_sprite.setPixmap(_pixel_perfect(raw, 72, 72))
            else:
                self.front_img.setText("No sprite")

        def _render_sprite(self):
            pix = (self._shiny_pix if (self._shiny and self._shiny_pix)
                   else self._normal_pix)
            if pix:
                self.front_img.setPixmap(
                    _pixel_perfect(pix, self.front_img.width(), self.front_img.height()))

        def _toggle_shiny(self, checked):
            self._shiny = checked
            self.shiny_btn.setText("Shiny" if checked else "Normal")
            if checked and self._shiny_pix is None and self._normal_pix and self._front_path:
                self._shiny_pix = make_shiny_pixmap(self._front_path, self._normal_pix)
            self._render_sprite()
            if self._normal_pix:
                pix_src = self._shiny_pix if (checked and self._shiny_pix) else self._normal_pix
                self._hdr_sprite.setPixmap(_pixel_perfect(pix_src, 72, 72))

        def _cycle_status(self):
            self._status = cycle_status(self._status)
            c = STATUS_HEX.get(self._status, '#6c7086')
            self.status_badge.setStyleSheet(
                f"color:{c}; font-size:12px; font-weight:bold; "
                "background:transparent; border:none;"
            )
            self.status_badge.setText(self._status)
            if self._cb:
                self._cb(self._pokemon.key, self._status)

        # Keep legacy method name used by external callers
        def _refresh_sprites(self):
            self._render_sprite()

    # ─── Main Window ──────────────────────────────────────────────────────────
    class MainWindow(QMainWindow):

        def __init__(self, all_pokemon, status_dict, sprite_map):
            super().__init__()
            self.all_pokemon = all_pokemon
            self.status_dict = status_dict
            self.sprite_map  = sprite_map
            self._visible_keys = []
            self._sort_col   = COL_BST
            self._sort_order = Qt.DescendingOrder

            self.setWindowTitle("Stat Dex — Pokédex")
            self.resize(1280, 780)
            self._setup_ui()
            self._connect_signals()
            self.refresh_table()
            self._setup_file_watcher()

        def _setup_ui(self):
            splitter = QSplitter(Qt.Horizontal)
            splitter.setHandleWidth(3)

            self.filters = FilterPanel()
            splitter.addWidget(self.filters)

            right = QWidget()
            rl = QVBoxLayout(right)
            rl.setContentsMargins(0, 0, 0, 0)
            rl.setSpacing(0)

            self.table = QTableWidget()
            self.table.setColumnCount(len(COLUMNS))
            self.table.setHorizontalHeaderLabels([c[0] for c in COLUMNS])
            self.table.horizontalHeader().setSectionsClickable(True)
            self.table.horizontalHeader().setSortIndicatorShown(True)
            self.table.verticalHeader().setVisible(False)
            self.table.setAlternatingRowColors(True)
            self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
            self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
            self.table.setSortingEnabled(True)
            self.table.setShowGrid(True)
            self.table.setIconSize(QSize(56, 56))

            for i, (_, w) in enumerate(COLUMNS):
                self.table.setColumnWidth(i, w)
            self.table.horizontalHeader().setStretchLastSection(True)

            rl.addWidget(self.table)
            splitter.addWidget(right)
            splitter.setSizes([230, 1050])

            self.setCentralWidget(splitter)
            self.status_bar = QStatusBar()
            self.setStatusBar(self.status_bar)

        def _connect_signals(self):
            f = self.filters
            self._timer = QTimer(); self._timer.setSingleShot(True)
            self._timer.timeout.connect(self.refresh_table)

            def schedule(): self._timer.start(200)

            f.search.textChanged.connect(schedule)
            f.ability_search.textChanged.connect(schedule)
            f.bst_min.valueChanged.connect(schedule)
            f.bst_max.valueChanged.connect(schedule)
            f.gen_cb.currentIndexChanged.connect(self.refresh_table)
            f.type1_cb.currentIndexChanged.connect(self.refresh_table)
            f.type2_cb.currentIndexChanged.connect(self.refresh_table)
            f.stage_cb.currentIndexChanged.connect(self.refresh_table)
            f.status_cb.currentIndexChanged.connect(self.refresh_table)
            f.sort_cb.currentIndexChanged.connect(self._panel_sort_changed)
            f.order_cb.currentIndexChanged.connect(self._panel_sort_changed)
            f.chk_legendary.stateChanged.connect(self.refresh_table)
            f.chk_mythical.stateChanged.connect(self.refresh_table)
            f.chk_ultra_beast.stateChanged.connect(self.refresh_table)
            f.chk_paradox.stateChanged.connect(self.refresh_table)
            f.reset_btn.clicked.connect(self._reset)

            self.table.cellClicked.connect(self._cell_clicked)
            self.table.cellDoubleClicked.connect(self._open_detail)
            self.table.horizontalHeader().sectionClicked.connect(self._header_clicked)

        def refresh_table(self):
            cfg = self.filters.collect()
            filt = self._filter(self.all_pokemon, cfg)
            self._populate(filt, cfg)
            self._update_status_bar(filt)

        def _filter(self, lst, cfg):
            out = lst
            if cfg['search']:
                q = cfg['search']
                out = [p for p in out if q in p.name.lower() or q in p.key.lower()]
            if cfg['ability']:
                q = cfg['ability']
                out = [p for p in out if any(q in ab.lower() for ab in p.abilities)]
            if cfg['gen']:
                out = [p for p in out if p.gen == cfg['gen']]
            if cfg['type1']:
                out = [p for p in out if p.has_type(cfg['type1'])]
            if cfg['type2']:
                out = [p for p in out if p.has_type(cfg['type2'])]
            if cfg['stage']:
                out = [p for p in out if p.stage == cfg['stage']]
            if cfg['status']:
                s = cfg['status']
                out = [p for p in out if self.status_dict.get(p.key,'UNTOUCHED') == s]
            out = [p for p in out if cfg['bst_min'] <= p.bst <= cfg['bst_max']]
            if cfg['legendary']:   out = [p for p in out if p.is_legendary]
            if cfg['mythical']:    out = [p for p in out if p.is_mythical]
            if cfg['ultra_beast']: out = [p for p in out if p.is_ultra_beast]
            if cfg['paradox']:     out = [p for p in out if p.is_paradox]
            return out

        def _sort_key_fn(self, p, sort_key):
            """Return sort key for a Pokemon, with status_dict captured via closure."""
            sd = self.status_dict
            return {
                'bst':      -p.bst,
                'name':      p.name.lower(),
                'name_rev': tuple(-ord(c) for c in p.name.lower()),
                'gen':      (p.gen, p.name.lower()),
                'nat_dex':  (p.nat_dex, p.name.lower()),
                'hp':       -p.hp,
                'atk':      -p.atk,
                'def_':     -p.def_,
                'spa':      -p.spa,
                'spd':      -p.spd,
                'spe':      -p.spe,
                'height':   -p.height,
                'weight':   -p.weight,
                'stage':    (STAGE_ORDER.get(p.stage,9), p.name.lower()),
                'status':   (STATUS_CYCLE.index(sd.get(p.key,'UNTOUCHED')), -p.bst),
            }.get(sort_key, -p.bst)

        def _populate(self, pokemon_list, cfg):
            sort_key = cfg['sort_key']
            # Pre-sort the list before populating (table column sort also works)
            order = cfg['order']
            reverse = (order == Qt.DescendingOrder)
            if sort_key in ('name','name_rev','gen','nat_dex','stage','status'):
                # These need custom key functions
                pokemon_list = sorted(
                    pokemon_list,
                    key=lambda p: self._sort_key_fn(p, sort_key),
                    reverse=False,  # direction encoded in key fn (negation)
                )
                if sort_key == 'name_rev':
                    pokemon_list = list(reversed(pokemon_list))
            else:
                pokemon_list = sorted(
                    pokemon_list,
                    key=lambda p: self._sort_key_fn(p, sort_key),
                    reverse=False,  # negation encodes descending
                )
                if order == Qt.AscendingOrder:
                    pokemon_list = list(reversed(pokemon_list))

            self.table.setSortingEnabled(False)
            self.table.setRowCount(0)
            self.table.setRowCount(len(pokemon_list))
            self._visible_keys = []

            for row, p in enumerate(pokemon_list):
                self.table.setRowHeight(row, 64)
                st = self.status_dict.get(p.key, 'UNTOUCHED')
                self._visible_keys.append(p.key)

                # Sprite column
                spr_item = QTableWidgetItem()
                spr_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
                front, _ = find_sprite_for_key(p.key.lower())
                if front and os.path.isfile(front):
                    with _quiet_stderr():
                        raw = QPixmap(front)
                    if not raw.isNull():
                        if raw.height() > raw.width():
                            raw = raw.copy(0, 0, raw.width(), raw.width())
                        raw = make_transparent_pixmap(raw)
                        pix = _pixel_perfect(raw, 56, 56)
                        spr_item.setIcon(QIcon(pix))
                self.table.setItem(row, COL_SPRITE, spr_item)

                marker = ('★' if p.is_legendary else '✦' if p.is_mythical else
                          '◆' if p.is_ultra_beast else '◈' if p.is_paradox else '')
                name_item = QTableWidgetItem(p.display_name + marker)
                name_item.setData(Qt.UserRole, p.key)
                if p.key in self.sprite_map:
                    name_item.setToolTip("Double-click for details")
                self.table.setItem(row, COL_NAME, name_item)

                gen_item = NumItem(p.gen, f"G{p.gen}")
                gen_item.setForeground(QBrush(QColor(GEN_HEX.get(p.gen, '#cdd6f4'))))
                gen_item.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(row, COL_GEN, gen_item)

                for col, tval in ((COL_TYPE1, p.type1), (COL_TYPE2, p.type2)):
                    display = tval.title() if tval else '—'
                    t_item  = QTableWidgetItem(display)
                    color = TYPE_HEX.get(tval,'#585b70') if tval else '#585b70'
                    t_item.setForeground(QBrush(QColor(color)))
                    t_item.setTextAlignment(Qt.AlignCenter)
                    self.table.setItem(row, col, t_item)

                stage_colors = {
                    'SINGLE':'#6c7086','BASIC':'#a6e3a1',
                    'MIDDLE':'#f9e2af','FINAL':'#cba6f7',
                }
                stg_item = QTableWidgetItem(p.stage.title())
                stg_item.setData(Qt.UserRole, STAGE_ORDER.get(p.stage, 9))
                stg_item.setForeground(QBrush(QColor(stage_colors.get(p.stage,'#cdd6f4'))))
                stg_item.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(row, COL_STAGE, stg_item)

                for col, val in zip(
                    [COL_HP,COL_ATK,COL_DEF,COL_SPA,COL_SPD,COL_SPE],
                    [p.hp, p.atk, p.def_, p.spa, p.spd, p.spe]
                ):
                    si = NumItem(val)
                    si.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                    self.table.setItem(row, col, si)

                bst_item = NumItem(p.bst)
                bst_item.setForeground(QBrush(QColor(bst_color(p.bst))))
                bst_item.setFont(QFont("", -1, QFont.Bold))
                bst_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.table.setItem(row, COL_BST, bst_item)

                self._set_status_item(row, st)

            self.table.setSortingEnabled(True)

        def _set_status_item(self, row, status):
            labels = {'UNTOUCHED':'Untouched','BUFFED':'▲ Buffed','NERFED':'▼ Nerfed'}
            item = QTableWidgetItem(labels.get(status, status))
            item.setForeground(QBrush(QColor(STATUS_HEX.get(status,'#cdd6f4'))))
            item.setBackground(QBrush(QColor(STATUS_BG.get(status,'#1e1e2e'))))
            item.setTextAlignment(Qt.AlignCenter)
            item.setToolTip("Click to cycle:  Untouched → Buffed → Nerfed")
            item.setData(Qt.UserRole, status)
            self.table.setItem(row, COL_STATUS, item)

        def _header_clicked(self, col):
            if self._sort_col == col:
                self._sort_order = (Qt.AscendingOrder if self._sort_order == Qt.DescendingOrder
                                    else Qt.DescendingOrder)
            else:
                self._sort_col   = col
                self._sort_order = Qt.DescendingOrder
            # Sync filter panel dropdown
            col_to_sort_key = {
                COL_NAME:'name', COL_GEN:'gen', COL_BST:'bst',
                COL_HP:'hp', COL_ATK:'atk', COL_DEF:'def_',
                COL_SPA:'spa', COL_SPD:'spd', COL_SPE:'spe',
                COL_STAGE:'stage', COL_STATUS:'status',
            }
            skey = col_to_sort_key.get(col)
            if skey:
                for i, (_, k) in enumerate(SORT_FIELDS):
                    if k == skey:
                        self.filters.sort_cb.blockSignals(True)
                        self.filters.sort_cb.setCurrentIndex(i)
                        self.filters.sort_cb.blockSignals(False)
                        break
            self.refresh_table()

        def _panel_sort_changed(self):
            cfg = self.filters.collect()
            self._sort_order = cfg['order']
            # Map sort_key to column for visual indicator
            skey = cfg['sort_key']
            key_to_col = {
                'name':'name','name_rev':'name',
                'gen':COL_GEN,'bst':COL_BST,'hp':COL_HP,'atk':COL_ATK,
                'def_':COL_DEF,'spa':COL_SPA,'spd':COL_SPD,'spe':COL_SPE,
                'stage':COL_STAGE,'status':COL_STATUS,
            }
            col = key_to_col.get(skey, COL_BST)
            if isinstance(col, int):
                self._sort_col = col
            self.refresh_table()

        def _cell_clicked(self, row, col):
            if col != COL_STATUS: return
            key = self.table.item(row, COL_NAME).data(Qt.UserRole)
            if not key: return
            current = self.status_dict.get(key, 'UNTOUCHED')
            new_st  = cycle_status(current)
            self.status_dict[key] = new_st
            _save_status(self.status_dict)
            self._set_status_item(row, new_st)
            self._update_status_bar(
                [p for p in self.all_pokemon if p.key in self._visible_keys]
            )

        def _update_status_bar(self, visible):
            n   = len(visible)
            avg = (sum(p.bst for p in visible) / n) if n else 0
            nb  = sum(1 for p in visible if self.status_dict.get(p.key,'UNTOUCHED')=='BUFFED')
            nn  = sum(1 for p in visible if self.status_dict.get(p.key,'UNTOUCHED')=='NERFED')
            nu  = n - nb - nn
            total = len(self.all_pokemon)
            self.status_bar.showMessage(
                f"  Showing {n} / {total}  ·  Avg BST: {avg:.0f}  "
                f"·  ▲ Buffed: {nb}   ▼ Nerfed: {nn}   · Untouched: {nu}"
            )

        def _open_detail(self, row, _col):
            item = self.table.item(row, COL_NAME)
            if not item: return
            key = item.data(Qt.UserRole)
            pokemon = next((p for p in self.all_pokemon if p.key == key), None)
            if not pokemon: return
            sprite_data = self.sprite_map.get(key)
            current_status = self.status_dict.get(key, 'UNTOUCHED')
            def on_status_change(k, s):
                self.status_dict[k] = s
                _save_status(self.status_dict)
                self.refresh_table()
            dlg = PokemonDetailDialog(pokemon, sprite_data, current_status, on_status_change, self)
            dlg.show()

        def _reset(self):
            self.filters.reset()
            self.refresh_table()

        def _setup_file_watcher(self):
            self._watcher = QFileSystemWatcher(self)
            for path in GEN_FILES.values():
                if os.path.isfile(path):
                    self._watcher.addPath(path)
            self._reload_timer = QTimer(self)
            self._reload_timer.setSingleShot(True)
            self._reload_timer.setInterval(800)
            self._reload_timer.timeout.connect(self._on_source_changed)
            self._watcher.fileChanged.connect(lambda _: self._reload_timer.start())

        def _on_source_changed(self):
            self.status_bar.showMessage("  ⟳  Source files changed — reloading…")
            self.all_pokemon = load_all_pokemon()
            self.sprite_map  = build_sprite_map(self.all_pokemon)
            self.refresh_table()
            for path in GEN_FILES.values():
                if os.path.isfile(path) and path not in self._watcher.files():
                    self._watcher.addPath(path)
            self.status_bar.showMessage(
                f"  ✓  Reloaded {len(self.all_pokemon)} Pokémon  (source updated)"
            )


    def gui_main(all_pokemon, status_dict):
        from PyQt5.QtGui import QIcon as _QIcon
        app = QApplication(sys.argv)
        app.setStyle("Fusion")
        app.setStyleSheet(DARK_STYLE)
        _icon_path = os.path.join(_HERE, "gfx", "stat_dex_icon.png")
        if os.path.isfile(_icon_path):
            app.setWindowIcon(_QIcon(_icon_path))
        sprite_map = build_sprite_map(all_pokemon)
        win = MainWindow(all_pokemon, status_dict, sprite_map)
        win.show()
        sys.exit(app.exec_())


# ══════════════════════════════════════════════════════════════════════════════
# ENTRY POINT
# ══════════════════════════════════════════════════════════════════════════════
def build_cli_parser():
    p = argparse.ArgumentParser(
        description="Stat Dex — Full Pokédex viewer. Run without --cli to open the GUI.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--cli",       action="store_true",  help="Run in terminal (no GUI)")
    p.add_argument("--type",      metavar="TYPE",        help="e.g. fire  or  grass/poison")
    p.add_argument("--gen",       metavar="N", type=int, choices=range(1,10))
    p.add_argument("--min",       metavar="BST", type=int)
    p.add_argument("--max",       metavar="BST", type=int)
    p.add_argument("--search",    metavar="NAME")
    p.add_argument("--status",    metavar="S", choices=["buffed","nerfed","untouched",
                                                         "BUFFED","NERFED","UNTOUCHED"])
    p.add_argument("--stage",     metavar="S", choices=["single","basic","middle","final",
                                                         "SINGLE","BASIC","MIDDLE","FINAL"])
    p.add_argument("--sort",      metavar="KEY", default="bst-desc",
                   choices=["bst-desc","bst-asc","name","name-rev","gen","nat-dex",
                            "hp","atk","def","spa","spd","spe",
                            "height","weight","stage","status"])
    p.add_argument("--legendary",   action="store_true")
    p.add_argument("--mythical",    action="store_true")
    p.add_argument("--ultra-beast", action="store_true", dest="ultra_beast")
    p.add_argument("--paradox",     action="store_true")
    p.add_argument("--no-bar",   action="store_true", dest="no_bar")
    p.add_argument("--no-color", action="store_true", dest="no_color")
    p.add_argument("--limit",    metavar="N", type=int)
    return p


def main():
    parser = build_cli_parser()
    args   = parser.parse_args()
    want_gui = not args.cli and HAS_QT

    print("Loading Pokémon data...", end=' ', flush=True)
    all_pokemon = load_all_pokemon()
    status_dict = _load_status()
    print(f"{len(all_pokemon)} loaded.")

    if not all_pokemon:
        print(f"ERROR: No data found in {DATA_DIR}"); sys.exit(1)

    if want_gui:
        gui_main(all_pokemon, status_dict)
    else:
        if not HAS_QT and not args.cli:
            print("PyQt5 not found — falling back to CLI mode.")
        cli_main(args)


if __name__ == "__main__":
    main()
