#!/usr/bin/env python3
"""
party_god.py — Advanced Trainer Editor for pokeemerald-expansion

Pokemon Showdown-style GUI for editing src/data/trainers.party.
Features:
  - Full trainer metadata (class, pic, music, AI flags, items, battle type)
  - Per-slot Pokemon editor: species, level, held item w/ sprite, nature, IVs
  - Live Hidden Power type display from IVs
  - Move selector: Restricted (species learnset) and Unrestricted (all moves)
  - Held item picker with item sprites
  - Trainer pic picker with trainer front sprites
"""
import os, re, sys, json
from typing import List, Optional

# ── Resolve lib/ on path so decomp_data is importable ────────────────────────
_HERE = os.path.dirname(os.path.abspath(__file__))
_LIB  = os.path.join(_HERE, "lib")
if _LIB not in sys.path:
    sys.path.insert(0, _LIB)

# ══════════════════════════════════════════════════════════════════════════════
# SHARED DATA LIBRARY
# ══════════════════════════════════════════════════════════════════════════════
from decomp_data import (
    ROOT, PARTY_FILE, MOVES_FILE, SPECIES_FILE, ITEMS_FILE, TRAINERS_CONST,
    AI_FLAGS_FILE, ITEM_ICONS, TRAINER_PICS, POKEMON_GFX, SPRITES_DIR,
    LEARNSET_DIR, EGG_MOVES_FILE, TEACHABLE_FILE,
    TYPE_HEX, CATEGORY_HEX, type_color, cat_color, cat_label,
    ALL_TYPES, NATURE_MODS, NATURES, STAT_NAMES, _NATURE_BOOST,
    AI_FLAGS_ORDERED, AI_FLAG_BY_DISPLAY, AI_CONST_TO_DISPLAY, AI_PRESETS,
    MUSIC_OPTIONS, GENDER_OPTIONS, BATTLE_OPTIONS, MUGSHOT_OPTIONS,
    TrainerMon, Trainer,
    load_species, load_all_pokemon, load_all_abilities, load_ability_info, load_items, item_lookup,
    load_trainer_classes, load_trainer_pics, load_moves, move_lookup,
    load_learnsets, species_to_learnset_key, load_move_learners,
    find_sprite_for_key, pokemon_sprite, make_shiny_pixmap, make_transparent_pixmap,
    parse_trainers_party, write_trainers_party, build_trainer_location_map,
    load_item_descriptions, load_item_stats,
    _HP_TYPES, calc_hidden_power, optimal_ivs_for_hp_type,
    calc_ingame_hp, calc_ingame_stat, calc_all_ingame_stats, get_dex_base_stats,
    _TYPE_CHART, _ABILITY_IMMUNITIES, _mon_type_effectiveness, calc_team_type_profile,
    MEGA_STONE_TO_SPECIES, _get_mega_species, rival_starter_info,
    DARK_STYLE, STATUS_HEX, GEN_HEX, EVO_STAGES, STATUSES, STATUS_CYCLE,
    bst_color,
)

# ══════════════════════════════════════════════════════════════════════════════
# GUI
# ══════════════════════════════════════════════════════════════════════════════
try:
    from PyQt5.QtWidgets import (
        QApplication, QMainWindow, QDialog, QWidget, QSplitter,
        QListWidget, QListWidgetItem, QLineEdit, QTextEdit,
        QComboBox, QSpinBox, QCheckBox, QProgressBar,
        QPushButton, QFileDialog, QMessageBox, QTabWidget,
        QLabel, QFrame, QGroupBox, QScrollArea,
        QHBoxLayout, QVBoxLayout, QGridLayout, QFormLayout,
        QStatusBar, QAbstractItemView, QSizePolicy, QCompleter,
        QAction, QMenu, QToolButton,
        QTreeWidget, QTreeWidgetItem,
        QTableWidget, QTableWidgetItem,
        QHeaderView, QSizeGrip,
        QStyledItemDelegate, QStyle,
    )
    from PyQt5.QtCore  import Qt, QTimer, QSize, QRect, pyqtSignal, QFileSystemWatcher, QObject, QEvent
    from PyQt5.QtGui   import QColor, QFont, QBrush, QPixmap, QIcon, QCursor
    HAS_QT = True
except ImportError:
    HAS_QT = False
    print("PyQt5 not found. Install with: pip install PyQt5")
    sys.exit(1)

# ─── Helpers ─────────────────────────────────────────────────────────────────
def _sep():
    f = QFrame(); f.setObjectName("sep"); f.setFrameShape(QFrame.HLine); return f

def _heading(txt):
    l = QLabel(txt); l.setObjectName("heading"); return l

def _rgba(hex_color, alpha):
    """Convert #RRGGBB to rgba(r,g,b,alpha) — Qt stylesheets don't support 8-digit hex alpha."""
    h = hex_color.lstrip('#')
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r},{g},{b},{alpha:.2f})"

def _badge(text, color, bg=None):
    lbl = QLabel(text)
    bg_s = f"background:{bg};" if bg else f"background:{_rgba(color,0.13)};"
    lbl.setStyleSheet(f"{bg_s}color:{color};border:1px solid {_rgba(color,0.33)};"
                      "border-radius:4px;padding:1px 6px;font-size:11px;font-weight:bold;")
    return lbl

def _item_pixmap(icon_path, size=32):
    if icon_path and os.path.isfile(icon_path):
        pix = QPixmap(icon_path)
        if not pix.isNull():
            pix = make_transparent_pixmap(pix)
            return pix.scaled(size, size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
    return None

def _pokemon_pixmap(species_display, size=64):
    front, _ = pokemon_sprite(species_display)
    if front:
        pix = QPixmap(front)
        if not pix.isNull():
            # If height > width, it's an animation strip — crop to first frame only
            if pix.height() > pix.width():
                pix = pix.copy(0, 0, pix.width(), pix.width())
            pix = make_transparent_pixmap(pix)
            return pix.scaled(size, size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
    return None


# ─── Ball names (for MonEditorDialog ball selector) ───────────────────────────
_BALL_NAMES = [
    "", "Poke Ball", "Great Ball", "Ultra Ball", "Master Ball",
    "Premier Ball", "Heal Ball", "Net Ball", "Nest Ball", "Dive Ball",
    "Dusk Ball", "Timer Ball", "Quick Ball", "Repeat Ball", "Luxury Ball",
    "Level Ball", "Lure Ball", "Moon Ball", "Friend Ball", "Love Ball",
    "Fast Ball", "Heavy Ball", "Dream Ball", "Safari Ball", "Sport Ball",
    "Park Ball", "Beast Ball", "Cherish Ball",
]

# ─── Nature combo helpers ─────────────────────────────────────────────────────
_NEUTRAL_NATURES = ["Hardy", "Docile", "Bashful", "Quirky", "Serious"]
_GROUPED_NATURES = (
    _NEUTRAL_NATURES
    + [n for n in NATURES if n not in set(_NEUTRAL_NATURES)]
)

def _nature_item_text(nature):
    """Format nature for QComboBox display, e.g. 'Adamant  (+Atk / -SpA)'."""
    stat_short = ["", "Atk", "Def", "SpA", "SpD", "Spe"]
    bi, ri = _NATURE_BOOST.get(nature, (0, 0))
    if bi and ri:
        return f"{nature}  (+{stat_short[bi]} / -{stat_short[ri]})"
    return f"{nature}  (Neutral)"

def _fill_nature_combo(combo, current_nature=None):
    """Populate a QComboBox with organized natures (neutral first) + stat labels.
    Each item stores the bare nature name as Qt.UserRole data.
    """
    combo.blockSignals(True)
    combo.clear()
    for n in _GROUPED_NATURES:
        combo.addItem(_nature_item_text(n), n)
    if current_nature:
        for i in range(combo.count()):
            if combo.itemData(i) == current_nature:
                combo.setCurrentIndex(i)
                break
    combo.blockSignals(False)


# ══════════════════════════════════════════════════════════════════════════════
# FRAMELESS DIALOG BASE
# ══════════════════════════════════════════════════════════════════════════════
class _DialogTitleBar(QWidget):
    """Compact 36px title bar for pop-out dialogs: title text + close button."""

    def __init__(self, title, parent=None):
        super().__init__(parent)
        self.setFixedHeight(36)
        self._drag_pos = None
        lay = QHBoxLayout(self)
        lay.setContentsMargins(12, 0, 8, 0)
        lay.setSpacing(8)

        title_lbl = QLabel(title)
        title_lbl.setStyleSheet(
            "color:#cdd6f4; font-size:13px; font-weight:bold; background:transparent;")
        lay.addWidget(title_lbl)
        lay.addStretch()

        close_btn = QPushButton("✕")
        close_btn.setFixedSize(28, 28)
        close_btn.setStyleSheet(
            "QPushButton { background:transparent; border:none; border-radius:5px; "
            "color:#a6adc8; font-size:13px; font-weight:bold; }"
            "QPushButton:hover { background:#f38ba822; color:#f38ba8; }"
        )
        close_btn.clicked.connect(lambda: self.window().reject()
                                  if hasattr(self.window(), 'reject')
                                  else self.window().close())
        lay.addWidget(close_btn)
        self.setStyleSheet(
            "_DialogTitleBar { background:#181825; border-top-left-radius:10px; "
            "border-top-right-radius:10px; }"
        )

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self._drag_pos = e.globalPos() - self.window().frameGeometry().topLeft()

    def mouseMoveEvent(self, e):
        if self._drag_pos and e.buttons() == Qt.LeftButton:
            self.window().move(e.globalPos() - self._drag_pos)

    def mouseReleaseEvent(self, e):
        self._drag_pos = None


class _FramelessDialogBase(QDialog):
    """Base class for all party_god pop-out dialogs.
    Provides frameless window + custom title bar + rounded dark border.
    Subclasses call super().__init__(title, parent) then build their content
    into self._root_layout (a QVBoxLayout already set up with 12,10,12,12 margins).
    """

    def __init__(self, title, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_DeleteOnClose)

        # Outer rounded container
        self._outer = QWidget()
        self._outer.setObjectName("dlg_outer")
        self._outer.setStyleSheet(
            "QWidget#dlg_outer { background:#1e1e2e; border-radius:10px; "
            "border:1px solid #313244; }"
        )
        outer_lay = QVBoxLayout(self._outer)
        outer_lay.setContentsMargins(0, 0, 0, 0)
        outer_lay.setSpacing(0)

        # Title bar
        self._dlg_tb = _DialogTitleBar(title, self._outer)
        outer_lay.addWidget(self._dlg_tb)

        # Thin divider
        div = QFrame(); div.setFrameShape(QFrame.HLine)
        div.setStyleSheet("QFrame { background:#313244; max-height:1px; border:none; }")
        outer_lay.addWidget(div)

        # Content widget — subclasses add their widgets here
        self._dlg_content = QWidget()
        self._root_layout = QVBoxLayout(self._dlg_content)
        self._root_layout.setContentsMargins(12, 10, 12, 12)
        self._root_layout.setSpacing(8)
        outer_lay.addWidget(self._dlg_content, 1)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.addWidget(self._outer)


# ══════════════════════════════════════════════════════════════════════════════
# ITEM SELECTOR DIALOG
# ══════════════════════════════════════════════════════════════════════════════
class AbilitySelectorDialog(_FramelessDialogBase):
    """Select ability in Restricted (species slots) or Unrestricted (all) mode."""

    def __init__(self, species='', current_ability='', parent=None):
        super().__init__("Select Ability", parent)
        self.setMinimumSize(560, 420)
        self.resize(600, 460)
        self.selected = current_ability
        self._species = species
        self._restricted = True
        self._build_ui()
        self._populate()
        self._restore_selection(current_ability)

    def _build_ui(self):
        root = self._root_layout

        # Mode toggle
        mode_row = QHBoxLayout(); mode_row.setSpacing(0)
        self._restricted_btn = QPushButton("Restricted")
        self._unrestricted_btn = QPushButton("Unrestricted")
        for btn in (self._restricted_btn, self._unrestricted_btn):
            btn.setCheckable(True); btn.setFixedHeight(28)
        self._restricted_btn.setChecked(True)
        self._restricted_btn.clicked.connect(lambda: self._set_mode(True))
        self._unrestricted_btn.clicked.connect(lambda: self._set_mode(False))
        mode_row.addWidget(self._restricted_btn)
        mode_row.addWidget(self._unrestricted_btn)
        mode_row.addStretch()
        root.addLayout(mode_row)

        # Search bar (unrestricted only)
        self._search = QLineEdit()
        self._search.setPlaceholderText("Search abilities...")
        self._search.textChanged.connect(self._on_search)
        self._search.setVisible(False)
        root.addWidget(self._search)

        # Body: list + detail panel
        body = QHBoxLayout(); body.setSpacing(8)
        self._list = QListWidget()
        self._list.currentItemChanged.connect(self._on_selection_changed)
        body.addWidget(self._list, 1)

        detail_w = QWidget(); detail_w.setFixedWidth(210)
        detail_lay = QVBoxLayout(detail_w); detail_lay.setContentsMargins(8, 4, 4, 4)
        self._det_name = QLabel("")
        self._det_name.setWordWrap(True)
        self._det_name.setStyleSheet("font-size:14px; font-weight:bold; color:#cdd6f4;")
        self._det_desc = QLabel("")
        self._det_desc.setWordWrap(True)
        self._det_desc.setStyleSheet("color:#a6adc8; font-size:11px; line-height:1.4;")
        detail_lay.addWidget(self._det_name)
        sep = QFrame(); sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("background:#313244; max-height:1px; margin:4px 0;")
        detail_lay.addWidget(sep)
        detail_lay.addWidget(self._det_desc)
        detail_lay.addStretch()
        body.addWidget(detail_w)
        root.addLayout(body, 1)

        # Footer
        footer = QHBoxLayout()
        ok_btn = QPushButton("Select"); ok_btn.setObjectName("accent"); ok_btn.setFixedHeight(32)
        ok_btn.clicked.connect(self._accept)
        cancel_btn = QPushButton("Cancel"); cancel_btn.setFixedHeight(32)
        cancel_btn.clicked.connect(self.reject)
        footer.addStretch(); footer.addWidget(ok_btn); footer.addWidget(cancel_btn)
        root.addLayout(footer)

    def _set_mode(self, restricted):
        self._restricted = restricted
        self._restricted_btn.setChecked(restricted)
        self._unrestricted_btn.setChecked(not restricted)
        self._search.setVisible(not restricted)
        self._populate()

    def _populate(self):
        self._list.clear()
        info = load_ability_info()
        if self._restricted:
            base = get_dex_base_stats(self._species)
            abilities = base.get('abilities', ('', '', '')) if base else ('', '', '')
            while len(abilities) < 3: abilities = tuple(abilities) + ('',)
            slot_labels = ['Ability 1', 'Ability 2', 'Hidden Ability']
            added = set()
            for slot, ab in enumerate(abilities[:3]):
                if not ab: continue
                label = f"{slot_labels[slot]}: {ab}"
                if ab in added: continue  # skip duplicate abilities (e.g. mono-ability mons)
                added.add(ab)
                item = QListWidgetItem(label)
                item.setData(Qt.UserRole, ab)
                self._list.addItem(item)
            if self._list.count() == 0:
                placeholder = QListWidgetItem("No abilities found for this species")
                placeholder.setFlags(placeholder.flags() & ~Qt.ItemIsSelectable)
                self._list.addItem(placeholder)
        else:
            query = self._search.text().lower().strip()
            for ab in load_all_abilities():
                if query and query not in ab.lower(): continue
                item = QListWidgetItem(ab)
                item.setData(Qt.UserRole, ab)
                self._list.addItem(item)

    def _on_search(self):
        if not self._restricted:
            self._populate()

    def _restore_selection(self, ability_name):
        if not ability_name: return
        for i in range(self._list.count()):
            if self._list.item(i).data(Qt.UserRole) == ability_name:
                self._list.setCurrentRow(i)
                return

    def _on_selection_changed(self, item):
        if not item: return
        ab = item.data(Qt.UserRole)
        if not ab: return
        info = load_ability_info()
        d = info.get(ab.lower(), {})
        self._det_name.setText(d.get('name', ab))
        self._det_desc.setText(d.get('desc', ''))

    def _accept(self):
        item = self._list.currentItem()
        if item and item.data(Qt.UserRole):
            self.selected = item.data(Qt.UserRole)
        self.accept()


class ItemSelectorDialog(_FramelessDialogBase):
    """Item picker with a description detail panel on the right.

    Clicking an item shows its sprite, name, and description in the panel.
    The user can select the item from either the list footer buttons or
    the "Select This Item" button inside the detail panel.
    """
    def __init__(self, current="", parent=None):
        super().__init__("Select Item", parent)
        self.resize(720, 500)
        self.selected = current
        self.selected_key = current
        self._items = load_items()
        self._item_descs = load_item_descriptions()
        self._item_stats = load_item_stats()
        self._build_ui()
        self._populate(self._items)

    def _build_ui(self):
        lay = self._root_layout

        # ── Search + clear row ───────────────────────────────────────────────
        search_row = QHBoxLayout()
        self._search = QLineEdit(); self._search.setPlaceholderText("Search items…")
        self._search.setClearButtonEnabled(True)
        self._search.textChanged.connect(self._filter)
        no_btn = QPushButton("— No Item —"); no_btn.setFixedHeight(28)
        no_btn.clicked.connect(self._clear_item)
        search_row.addWidget(self._search); search_row.addWidget(no_btn)
        lay.addLayout(search_row)

        # ── Body: list (left) + detail panel (right) ─────────────────────────
        body = QHBoxLayout(); body.setSpacing(10)

        self._list = QListWidget()
        self._list.setIconSize(QSize(32, 32))
        self._list.setAlternatingRowColors(True)
        self._list.itemClicked.connect(self._on_item_clicked)
        self._list.itemDoubleClicked.connect(self._accept)
        body.addWidget(self._list, 1)

        # Detail panel
        detail_w = QWidget()
        detail_w.setFixedWidth(220)
        detail_w.setStyleSheet(
            "QWidget { background:#1e1e2e; border-radius:8px; border:1px solid #313244; }"
        )
        detail_lay = QVBoxLayout(detail_w)
        detail_lay.setContentsMargins(10, 12, 10, 10)
        detail_lay.setSpacing(8)

        self._det_sprite = QLabel()
        self._det_sprite.setFixedSize(64, 64)
        self._det_sprite.setAlignment(Qt.AlignCenter)
        self._det_sprite.setStyleSheet(
            "background:#181825; border-radius:8px; border:1px solid #313244;"
        )
        sprite_wrap = QWidget(); sprite_wrap.setStyleSheet("background:transparent; border:none;")
        sw_lay = QHBoxLayout(sprite_wrap); sw_lay.setContentsMargins(0,0,0,0)
        sw_lay.addStretch(); sw_lay.addWidget(self._det_sprite); sw_lay.addStretch()
        detail_lay.addWidget(sprite_wrap)

        self._det_name = QLabel("")
        self._det_name.setAlignment(Qt.AlignCenter)
        self._det_name.setWordWrap(True)
        self._det_name.setStyleSheet(
            "font-size:13px; font-weight:bold; color:#cdd6f4; background:transparent; border:none;"
        )
        detail_lay.addWidget(self._det_name)

        sep = QFrame(); sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("background:#313244; max-height:1px; border:none;")
        detail_lay.addWidget(sep)

        self._det_desc = QLabel("")
        self._det_desc.setWordWrap(True)
        self._det_desc.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self._det_desc.setStyleSheet(
            "color:#a6adc8; font-size:11px; font-style:italic; "
            "background:transparent; border:none;"
        )
        detail_lay.addWidget(self._det_desc, 1)

        self._det_stats = QLabel("")
        self._det_stats.setAlignment(Qt.AlignLeft)
        self._det_stats.setWordWrap(True)
        self._det_stats.setStyleSheet(
            "color:#f9e2af; font-size:11px; background:transparent; border:none;"
        )
        self._det_stats.setVisible(False)
        detail_lay.addWidget(self._det_stats)

        self._det_select_btn = QPushButton("Select This Item")
        self._det_select_btn.setObjectName("accent")
        self._det_select_btn.setFixedHeight(30)
        self._det_select_btn.setVisible(False)
        self._det_select_btn.clicked.connect(self._accept)
        detail_lay.addWidget(self._det_select_btn)

        body.addWidget(detail_w)
        lay.addLayout(body, 1)

        # ── Footer buttons ────────────────────────────────────────────────────
        btns = QHBoxLayout()
        ok_btn = QPushButton("Select"); ok_btn.setObjectName("accent")
        ok_btn.clicked.connect(self._accept)
        cancel_btn = QPushButton("Cancel"); cancel_btn.clicked.connect(self.reject)
        btns.addStretch(); btns.addWidget(cancel_btn); btns.addWidget(ok_btn)
        lay.addLayout(btns)

    def _populate(self, items):
        self._list.clear()
        for key, display, icon_path in items:
            item = QListWidgetItem(display)
            item.setData(Qt.UserRole, key)
            pix = _item_pixmap(icon_path, 32)
            if pix: item.setIcon(QIcon(pix))
            self._list.addItem(item)
            if key == self.selected or display.lower() == self.selected.lower():
                self._list.setCurrentItem(item)
                self._show_detail(key, display, icon_path)

    def _on_item_clicked(self, list_item):
        key = list_item.data(Qt.UserRole)
        tup = item_lookup(key) if key else None
        display   = tup[1] if tup else (list_item.text() if list_item else "")
        icon_path = tup[2] if tup else ""
        self._show_detail(key, display, icon_path)

    def _show_detail(self, key, display, icon_path):
        """Populate the right-side detail panel for the given item."""
        # Sprite (larger, 64px)
        pix = _item_pixmap(icon_path, 64)
        if pix:
            self._det_sprite.setPixmap(pix)
        else:
            self._det_sprite.clear()
            self._det_sprite.setText("?")

        self._det_name.setText(display or "")

        # Description from items.h
        desc = self._item_descs.get(key, "") if key else ""
        self._det_desc.setText(desc if desc else "(No description available)")

        # Cost + fling power
        st = self._item_stats.get(key, {}) if key else {}
        price = st.get('price', '')
        fling = st.get('fling_power', 0)
        lines = []
        if price and price != '0':
            lines.append(f"Buy: ₽{price}")
        if fling:
            lines.append(f"Fling: {fling}")
        self._det_stats.setText("  ·  ".join(lines))
        self._det_stats.setVisible(bool(lines))

        self._det_select_btn.setVisible(bool(key))

    def _filter(self, text):
        q = text.strip().lower()
        visible = [it for it in self._items if q in it[1].lower() or q in it[0].lower()]
        self._populate(visible)

    def _clear_item(self):
        self.selected = ""; self.selected_key = ""
        self.accept()

    def _accept(self):
        cur = self._list.currentItem()
        if cur:
            self.selected_key = cur.data(Qt.UserRole)
            tup = item_lookup(self.selected_key)
            self.selected = tup[1] if tup and tup[1] else self.selected_key
        self.accept()


# ══════════════════════════════════════════════════════════════════════════════
# MOVE SELECTOR DIALOG
# ══════════════════════════════════════════════════════════════════════════════
class MoveDetailDialog(_FramelessDialogBase):
    """Full detail popup for a single move: stats, description, and list of all Pokémon learners."""

    def __init__(self, move_name_or_key, parent=None):
        mv = move_lookup(move_name_or_key) or {}
        if not mv:
            from decomp_data import load_moves
            mv = load_moves().get(move_name_or_key, {})
        name = mv.get('name', move_name_or_key)
        super().__init__(f"{name}  —  Move Details", parent)
        self.setMinimumSize(540, 500)
        self.resize(580, 560)
        self._build_ui(mv)

    def _badge(self, text, color):
        lbl = QLabel(text)
        lbl.setStyleSheet(
            f"background:{_rgba(color,0.20)}; color:{color}; border:1px solid {_rgba(color,0.40)}; "
            "border-radius:4px; padding:2px 10px; font-size:12px; font-weight:bold;"
        )
        return lbl

    def _build_ui(self, mv):
        root = self._root_layout

        # ── Name ─────────────────────────────────────────────────────────────
        name = mv.get('name', '—')
        name_lbl = QLabel(name)
        name_lbl.setStyleSheet("font-size:22px; font-weight:bold; color:#cdd6f4;")
        root.addWidget(name_lbl)

        # ── Type + Category badges ────────────────────────────────────────────
        t   = mv.get('type','').replace('TYPE_','')
        cat = mv.get('category','')
        badge_row = QHBoxLayout(); badge_row.setSpacing(6)
        if t:
            badge_row.addWidget(self._badge(t.title(), type_color(t)))
        if cat:
            badge_row.addWidget(self._badge(cat_label(cat), cat_color(cat)))
        badge_row.addStretch()
        root.addLayout(badge_row)

        sep1 = QFrame(); sep1.setFrameShape(QFrame.HLine)
        sep1.setStyleSheet("background:#313244; max-height:1px; margin:2px 0;")
        root.addWidget(sep1)

        # ── Stats row ────────────────────────────────────────────────────────
        pw  = mv.get('power',0)
        acc = mv.get('accuracy',0)
        pp  = mv.get('pp',0)
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

        # ── Description ───────────────────────────────────────────────────────
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

        # ── Learners ─────────────────────────────────────────────────────────
        learners = load_move_learners()
        entries = learners.get(name.lower(), [])
        header = QLabel(f"Pokémon that can learn {name}  ({len(entries)} total)")
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
                # Color-code by method
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

        # ── Footer ────────────────────────────────────────────────────────────
        close_btn = QPushButton("Close"); close_btn.setFixedHeight(32)
        close_btn.clicked.connect(self.close)
        footer = QHBoxLayout()
        footer.addStretch(); footer.addWidget(close_btn)
        root.addLayout(footer)


class MoveSelectorDialog(_FramelessDialogBase):
    def __init__(self, species='', restricted=True, current="", parent=None):
        super().__init__("Select Move", parent)
        self.resize(700, 540)
        _mv_init = move_lookup(current) if current else {}
        self.selected = _mv_init.get('name', current) if _mv_init else current
        self.selected_move = self.selected
        self._species = species
        self._moves   = load_moves()
        self._learnsets = load_learnsets()
        self._build_ui()
        self._set_mode("restricted" if restricted else "unrestricted")

    def _build_ui(self):
        lay = self._root_layout

        # Mode toggle
        toggle_row = QHBoxLayout()
        self._restricted_btn   = QPushButton("Restricted")
        self._unrestricted_btn = QPushButton("Unrestricted")
        for btn in (self._restricted_btn, self._unrestricted_btn):
            btn.setCheckable(True); btn.setFixedHeight(30)
        self._restricted_btn.setChecked(True)
        self._restricted_btn.clicked.connect(lambda: self._set_mode("restricted"))
        self._unrestricted_btn.clicked.connect(lambda: self._set_mode("unrestricted"))
        clear_btn = QPushButton("— No Move —"); clear_btn.setFixedHeight(30)
        clear_btn.clicked.connect(self._clear_move)
        toggle_row.addWidget(self._restricted_btn)
        toggle_row.addWidget(self._unrestricted_btn)
        toggle_row.addStretch()
        toggle_row.addWidget(clear_btn)
        lay.addLayout(toggle_row)

        # Main content
        content = QHBoxLayout(); content.setSpacing(10)

        # Left: list area
        self._list_stack = QTabWidget()
        self._list_stack.setDocumentMode(True)

        # Restricted tabs
        self._levelup_list  = self._make_move_list()
        self._egg_list      = self._make_move_list()
        self._tm_list       = self._make_move_list()
        self._tutor_list    = self._make_move_list()
        self._list_stack.addTab(self._levelup_list, "Level Up")
        self._list_stack.addTab(self._egg_list,     "Egg")
        self._list_stack.addTab(self._tm_list,      "TM / HM")
        self._list_stack.addTab(self._tutor_list,   "Tutor")

        # Unrestricted tab (with search)
        unres_w = QWidget(); unres_lay = QVBoxLayout(unres_w); unres_lay.setContentsMargins(0,4,0,0)
        self._search = QLineEdit(); self._search.setPlaceholderText("Search moves…")
        self._search.setClearButtonEnabled(True)
        self._search.textChanged.connect(self._filter_unrestricted)
        self._unrestricted_list = self._make_move_list()
        unres_lay.addWidget(self._search)
        unres_lay.addWidget(self._unrestricted_list, 1)
        self._list_stack.addTab(unres_w, "All Moves")
        self._all_moves_tab_idx = 4

        content.addWidget(self._list_stack, 3)

        # Right: move detail card
        detail_w = QWidget(); detail_w.setFixedWidth(210)
        detail_w.setStyleSheet("background:#252536; border-radius:8px;")
        d_lay = QVBoxLayout(detail_w)
        d_lay.setContentsMargins(10, 10, 10, 10); d_lay.setSpacing(6)
        self._d_name = QLabel("—")
        self._d_name.setStyleSheet("font-weight:bold;font-size:14px;color:#cdd6f4;")
        self._d_name.setWordWrap(True)
        self._d_type = QLabel(""); self._d_cat = QLabel("")
        self._d_power= QLabel(""); self._d_acc = QLabel("")
        self._d_pp   = QLabel(""); self._d_desc= QLabel("")
        self._d_desc.setWordWrap(True)
        self._d_desc.setStyleSheet("color:#6c7086;font-size:11px;")
        d_lay.addWidget(self._d_name)
        badge_row = QHBoxLayout()
        badge_row.addWidget(self._d_type); badge_row.addWidget(self._d_cat); badge_row.addStretch()
        d_lay.addLayout(badge_row)
        d_lay.addWidget(_sep())
        for lbl in (self._d_power, self._d_acc, self._d_pp):
            lbl.setStyleSheet("color:#bac2de;font-size:12px;")
            d_lay.addWidget(lbl)
        d_lay.addWidget(_sep())
        d_lay.addWidget(self._d_desc)
        d_lay.addStretch()
        content.addWidget(detail_w, 0)
        lay.addLayout(content, 1)

        # Buttons
        btns = QHBoxLayout()
        self._details_btn = QPushButton("Move Details")
        self._details_btn.setToolTip("Open full detail popup for the highlighted move")
        self._details_btn.clicked.connect(self._open_move_details)
        ok_btn = QPushButton("Select Move"); ok_btn.setObjectName("accent")
        ok_btn.clicked.connect(self._accept)
        cancel_btn = QPushButton("Cancel"); cancel_btn.clicked.connect(self.reject)
        btns.addWidget(self._details_btn)
        btns.addStretch(); btns.addWidget(cancel_btn); btns.addWidget(ok_btn)
        lay.addLayout(btns)

        # Connect list selection signals
        for lst in (self._levelup_list, self._egg_list,
                    self._tm_list, self._tutor_list, self._unrestricted_list):
            lst.currentItemChanged.connect(self._on_move_highlighted)
            lst.itemDoubleClicked.connect(self._accept)
            lst.setContextMenuPolicy(Qt.CustomContextMenu)
            lst.customContextMenuRequested.connect(
                lambda pos, l=lst: self._show_move_context_menu(l, pos)
            )

    def _make_move_list(self):
        lst = QListWidget(); lst.setAlternatingRowColors(True)
        return lst

    def _set_mode(self, mode):
        self._restricted_btn.setChecked(mode == "restricted")
        self._unrestricted_btn.setChecked(mode == "unrestricted")
        if mode == "restricted":
            for i in range(4): self._list_stack.setTabVisible(i, True)
            self._list_stack.setTabVisible(4, False)
            self._populate_restricted()
        else:
            for i in range(4): self._list_stack.setTabVisible(i, False)
            self._list_stack.setTabVisible(4, True)
            self._populate_unrestricted()

    def _populate_restricted(self):
        ls_key = species_to_learnset_key(self._species)
        ls = self._learnsets.get(ls_key, {'levelup': [], 'egg': [], 'tm': [], 'tutor': []})

        # Level Up
        self._levelup_list.clear()
        for lvl, move_key in ls.get('levelup', []):
            mv = self._moves.get(move_key, {})
            label = f"Lv.{lvl:<3}  {mv.get('name', move_key)}"
            self._add_move_item(self._levelup_list, move_key, label)

        # Egg
        self._egg_list.clear()
        for move_key in ls.get('egg', []):
            mv = self._moves.get(move_key, {})
            self._add_move_item(self._egg_list, move_key, mv.get('name', move_key))

        # TM / HM
        self._tm_list.clear()
        for move_key in ls.get('tm', []):
            mv = self._moves.get(move_key, {})
            self._add_move_item(self._tm_list, move_key, mv.get('name', move_key))

        # Tutor
        self._tutor_list.clear()
        for move_key in ls.get('tutor', []):
            mv = self._moves.get(move_key, {})
            self._add_move_item(self._tutor_list, move_key, mv.get('name', move_key))

        # Auto-select current move (compare by display name)
        for lst in (self._levelup_list, self._egg_list, self._tm_list, self._tutor_list):
            for i in range(lst.count()):
                if lst.item(i).data(Qt.UserRole).lower() == self.selected.lower():
                    lst.setCurrentRow(i)

    def _populate_unrestricted(self, query=""):
        self._unrestricted_list.clear()
        q = query.strip().lower()
        for key, mv in sorted(self._moves.items(), key=lambda x: x[1].get('name','').lower()):
            name = mv.get('name', key)
            if q and q not in name.lower() and q not in key.lower(): continue
            self._add_move_item(self._unrestricted_list, key, name)
            if name.lower() == self.selected.lower():
                self._unrestricted_list.setCurrentRow(self._unrestricted_list.count()-1)

    def _add_move_item(self, lst, move_key, label):
        mv = self._moves.get(move_key, {})
        display_name = mv.get('name', move_key)
        t  = mv.get('type','').replace('TYPE_','').strip()
        color = type_color(t) if t else "#585b70"
        item = QListWidgetItem(label)
        item.setData(Qt.UserRole, display_name)   # store display name for PS round-trip
        bg = QColor(color); bg.setAlpha(55)
        item.setBackground(QBrush(bg))
        item.setForeground(QBrush(QColor("#ffffff")))
        lst.addItem(item)

    def _filter_unrestricted(self, text):
        self._populate_unrestricted(text)

    def _on_move_highlighted(self, item, _=None):
        if not item: return
        key = item.data(Qt.UserRole)   # display name
        mv  = move_lookup(key)
        if not mv: mv = self._moves.get(key, {})
        name = mv.get('name', key)
        t    = mv.get('type','').replace('TYPE_','')
        cat  = mv.get('category','')
        self._d_name.setText(name)
        tc = type_color(t)
        cc = cat_color(cat)
        self._d_type.setText(t.title() if t else '—')
        self._d_type.setStyleSheet(f"background:{_rgba(tc,0.13)};color:{tc};border:1px solid {_rgba(tc,0.33)};"
                                   "border-radius:3px;padding:1px 5px;font-size:11px;font-weight:bold;")
        self._d_cat.setText(cat_label(cat))
        self._d_cat.setStyleSheet(f"background:{_rgba(cc,0.13)};color:{cc};border:1px solid {_rgba(cc,0.33)};"
                                  "border-radius:3px;padding:1px 5px;font-size:11px;font-weight:bold;")
        pw = mv.get('power', 0)
        self._d_power.setText(f"Power:    {pw if pw else '—'}")
        acc = mv.get('accuracy', 0)
        self._d_acc.setText(f"Accuracy: {acc if acc else '—'}")
        self._d_pp.setText(f"PP:       {mv.get('pp', 0)}")
        self._d_desc.setText(mv.get('description',''))

    def _clear_move(self):
        self.selected = ""; self.selected_move = ""; self.accept()

    def _get_highlighted_move(self):
        """Return the display name of the currently highlighted move across all visible lists."""
        for lst in (self._levelup_list, self._egg_list,
                    self._tm_list, self._tutor_list, self._unrestricted_list):
            if not lst.isHidden():
                item = lst.currentItem()
                if item: return item.data(Qt.UserRole)
        return None

    def _open_move_details(self):
        name = self._get_highlighted_move()
        if name:
            dlg = MoveDetailDialog(name, parent=self)
            dlg.exec_()

    def _show_move_context_menu(self, lst, pos):
        item = lst.itemAt(pos)
        if not item: return
        name = item.data(Qt.UserRole)
        if not name: return
        menu = QMenu(self)
        act_details = menu.addAction("View Move Details")
        act_select  = menu.addAction("Select This Move")
        action = menu.exec_(lst.mapToGlobal(pos))
        if action == act_details:
            dlg = MoveDetailDialog(name, parent=self)
            dlg.exec_()
        elif action == act_select:
            lst.setCurrentItem(item)
            self._accept()

    def _accept(self):
        for lst in (self._levelup_list, self._egg_list,
                    self._tm_list, self._tutor_list, self._unrestricted_list):
            cur = lst.currentItem()
            if cur and not lst.isHidden():
                self.selected = cur.data(Qt.UserRole)
                self.selected_move = self.selected
                break
        self.accept()


# ══════════════════════════════════════════════════════════════════════════════
# TRAINER PIC SELECTOR DIALOG
# ══════════════════════════════════════════════════════════════════════════════
class TrainerPicSelectorDialog(_FramelessDialogBase):
    def __init__(self, current="", parent=None):
        super().__init__("Select Trainer Pic", parent)
        self.resize(640, 520)
        self.selected = current
        self._pics = load_trainer_pics()
        self._build_ui()

    def _build_ui(self):
        lay = self._root_layout

        search = QLineEdit(); search.setPlaceholderText("Search pics…")
        search.setClearButtonEnabled(True); search.textChanged.connect(self._filter)
        lay.addWidget(search)

        scroll = QScrollArea(); scroll.setWidgetResizable(True)
        self._grid_w = QWidget()
        self._grid   = QGridLayout(self._grid_w)
        self._grid.setSpacing(8)
        scroll.setWidget(self._grid_w)
        lay.addWidget(scroll, 1)

        btns = QHBoxLayout()
        cancel_btn = QPushButton("Cancel"); cancel_btn.clicked.connect(self.reject)
        btns.addStretch(); btns.addWidget(cancel_btn)
        lay.addLayout(btns)
        self._populate(self._pics)

    def _populate(self, pics):
        # Clear grid
        while self._grid.count():
            item = self._grid.takeAt(0)
            if item.widget(): item.widget().deleteLater()
        cols = 5
        for idx, (display, path) in enumerate(pics):
            btn = QToolButton()
            btn.setFixedSize(110, 110)
            btn.setObjectName("slot")
            btn.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
            btn.setIconSize(QSize(72, 72))
            pix = None
            if path and os.path.isfile(path):
                pix = QPixmap(path)
            if pix and not pix.isNull():
                btn.setIcon(QIcon(pix.scaled(72, 72, Qt.KeepAspectRatio, Qt.SmoothTransformation)))
            short = display if len(display) <= 13 else display[:12] + '…'
            btn.setText(short)
            btn.setToolTip(display)
            btn.clicked.connect(lambda _, d=display: self._select(d))
            if display.lower() == self.selected.lower():
                btn.setStyleSheet("QToolButton{background:#313244;border:2px solid #89b4fa;border-radius:8px;}")
            self._grid.addWidget(btn, idx // cols, idx % cols)

    def _filter(self, text):
        q = text.strip().lower()
        filtered = [(d,p) for d,p in self._pics if q in d.lower()]
        self._populate(filtered)

    def _select(self, display):
        self.selected = display; self.accept()


# ══════════════════════════════════════════════════════════════════════════════
# GENDER TOGGLE BUTTON
# ══════════════════════════════════════════════════════════════════════════════
class GenderToggleBtn(QPushButton):
    """Cycles ♂ → ♀ → (none) for gendered species; shows ◎ and disables for genderless."""
    gender_changed = pyqtSignal(str)   # emits "Male", "Female", or ""

    _STYLE_MALE = (
        "QPushButton { background:#1e3a5f; border:1px solid #89b4fa; border-radius:4px; "
        "color:#89b4fa; font-size:15px; font-weight:bold; padding:0; }"
        "QPushButton:hover { background:#25476e; }"
    )
    _STYLE_FEMALE = (
        "QPushButton { background:#3a1e2e; border:1px solid #f38ba8; border-radius:4px; "
        "color:#f38ba8; font-size:15px; font-weight:bold; padding:0; }"
        "QPushButton:hover { background:#4a2538; }"
    )
    _STYLE_NONE = (
        "QPushButton { background:#1e1e2e; border:1px solid #45475a; border-radius:4px; "
        "color:#585b70; font-size:13px; padding:0; }"
        "QPushButton:hover { background:#313244; }"
    )
    _STYLE_GENDERLESS = (
        "QPushButton { background:#1e1e2e; border:1px solid #313244; border-radius:4px; "
        "color:#45475a; font-size:13px; padding:0; }"
    )

    def __init__(self, parent=None):
        super().__init__(parent)
        self._gender      = ""       # "Male", "Female", or ""
        self._gender_type = "both"   # "both", "genderless", "male_only", "female_only"
        self.setFixedSize(34, 28)
        self.clicked.connect(self._cycle)
        self._refresh()

    def set_species(self, species):
        """Update allowed gender states based on species gender ratio from repo data."""
        base = get_dex_base_stats(species) if species else None
        gr   = base.get('gender_ratio', 127) if base else 127
        if gr == 255:
            self._gender_type = "genderless"
            self._gender = ""
        elif gr == 0:
            self._gender_type = "male_only"
            self._gender = "Male"
        elif gr == 254:
            self._gender_type = "female_only"
            self._gender = "Female"
        else:
            self._gender_type = "both"
        self.setEnabled(self._gender_type not in ("genderless",))
        self._refresh()

    def set_gender(self, gender):
        self._gender = gender
        self._refresh()

    def get_gender(self):
        return self._gender

    def _cycle(self):
        if self._gender_type == "genderless":
            return
        if self._gender_type == "male_only":
            self._gender = "Male"
        elif self._gender_type == "female_only":
            self._gender = "Female"
        else:
            self._gender = {"": "Male", "Male": "Female", "Female": ""}[self._gender]
        self._refresh()
        self.gender_changed.emit(self._gender)

    def _refresh(self):
        if self._gender_type == "genderless":
            self.setText("◎"); self.setStyleSheet(self._STYLE_GENDERLESS)
        elif self._gender == "Male":
            self.setText("♂"); self.setStyleSheet(self._STYLE_MALE)
        elif self._gender == "Female":
            self.setText("♀"); self.setStyleSheet(self._STYLE_FEMALE)
        else:
            self.setText("?"); self.setStyleSheet(self._STYLE_NONE)


# ══════════════════════════════════════════════════════════════════════════════
# SPECIES LIST SPRITE DELEGATE
# ══════════════════════════════════════════════════════════════════════════════
_species_sprite_cache: dict = {}   # module-level: name → QPixmap | None

class _SpriteItemDelegate(QStyledItemDelegate):
    """List-row delegate: draws a 32×32 transparent sprite before the item text.
    Sprites are loaded and processed lazily (only when the row scrolls into view)
    and cached for the session so repeated filter changes are instant."""

    ICON_W = 32
    ROW_H  = 40
    PAD    = 4

    def _pixmap(self, name: str):
        if name in _species_sprite_cache:
            return _species_sprite_cache[name]
        front, _ = pokemon_sprite(name)
        pix = None
        if front:
            raw = QPixmap(front)
            if not raw.isNull():
                if raw.height() > raw.width():
                    raw = raw.copy(0, 0, raw.width(), raw.width())
                raw = make_transparent_pixmap(raw)
                pix = raw.scaled(self.ICON_W, self.ICON_W,
                                 Qt.KeepAspectRatio, Qt.SmoothTransformation)
        _species_sprite_cache[name] = pix
        return pix

    def sizeHint(self, option, index):
        return QSize(option.rect.width(), self.ROW_H)

    def paint(self, painter, option, index):
        self.initStyleOption(option, index)
        style = option.widget.style() if option.widget else QApplication.style()
        # Draw standard panel background (selection, hover, alternating row colour)
        style.drawPrimitive(QStyle.PE_PanelItemViewItem, option, painter, option.widget)

        rect  = option.rect
        name  = index.data(Qt.UserRole) or ''
        label = index.data(Qt.DisplayRole) or name
        pix   = self._pixmap(name)

        # Sprite — centred vertically in the row
        if pix:
            ix = rect.left() + self.PAD
            iy = rect.top() + (rect.height() - pix.height()) // 2
            painter.drawPixmap(ix, iy, pix)

        # Text — offset right of sprite
        tx = rect.left() + self.ICON_W + self.PAD * 2
        tr = QRect(tx, rect.top(), rect.right() - tx, rect.height())
        if option.state & QStyle.State_Selected:
            painter.setPen(option.palette.highlightedText().color())
        else:
            painter.setPen(option.palette.text().color())
        painter.drawText(tr, Qt.AlignVCenter | Qt.AlignLeft, label)


# ══════════════════════════════════════════════════════════════════════════════
# SPECIES SELECTOR DIALOG
# ══════════════════════════════════════════════════════════════════════════════
class SpeciesSelectorDialog(_FramelessDialogBase):
    """Pick a Pokémon species: search bar, type filter, sprite + stat detail panel."""

    def __init__(self, current='', parent=None):
        super().__init__("Select Species", parent)
        self.resize(760, 580)
        self.selected = current   # display name e.g. "Sprigatito"

        # Build master list: (display_name, Pokemon|None)
        # Mega evolutions, Gigantamax, Primal Reversions, and Eternamax are excluded —
        # they are triggered automatically in battle by held item and cannot be
        # directly assigned as a party species. Dynamax is not used in this game.
        _BLOCKED_TAGS = ('_MEGA', '_GMAX', '_PRIMAL', '_ETERNAMAX')
        all_pkmn = load_all_pokemon()
        seen = set()
        self._entries = []
        for p in all_pkmn:
            if any(tag in p.key.upper() for tag in _BLOCKED_TAGS):
                continue
            if p.display_name not in seen:
                seen.add(p.display_name)
                self._entries.append((p.display_name, p))
        for name in load_species():
            if name not in seen:
                # Filter by key-style check for raw species strings
                name_upper = name.upper().replace(' ', '_').replace('-', '_')
                if any(tag in name_upper for tag in _BLOCKED_TAGS):
                    continue
                seen.add(name)
                self._entries.append((name, None))
        self._entries.sort(key=lambda x: x[0])
        # fast lookup: name → Pokemon
        self._pkmn_map = {n: p for n, p in self._entries}

        self._type_filter = None   # None = All
        self._search_text = ''
        self._filtered    = list(self._entries)

        self._build_ui()
        self._populate()
        self._restore_selection()

    # ── Build UI ──────────────────────────────────────────────────────────────
    def _build_ui(self):
        root = self._root_layout

        # Search row
        search_row = QHBoxLayout(); search_row.setSpacing(6)
        self._search_edit = QLineEdit()
        self._search_edit.setPlaceholderText("Search species\u2026")
        self._search_edit.setClearButtonEnabled(True)
        self._search_edit.textChanged.connect(self._on_search)
        clear_btn = QPushButton("\u2014 No Species \u2014"); clear_btn.setFixedHeight(28)
        clear_btn.clicked.connect(self._clear_species)
        search_row.addWidget(self._search_edit, 1)
        search_row.addWidget(clear_btn)
        root.addLayout(search_row)

        # Type filter row (scrollable)
        type_wrap = QWidget()
        type_lay  = QHBoxLayout(type_wrap)
        type_lay.setContentsMargins(0, 0, 0, 0)
        type_lay.setSpacing(4)
        self._type_btns = {}

        all_btn = QPushButton("All")
        all_btn.setCheckable(True); all_btn.setChecked(True)
        all_btn.setFixedHeight(24)
        all_btn.setStyleSheet(
            "QPushButton { background:#45475a; color:#cdd6f4; border:1px solid #585b70; "
            "border-radius:4px; padding:0 8px; font-size:11px; }"
            "QPushButton:checked { background:#89b4fa; color:#1e1e2e; border-color:#89b4fa; font-weight:bold; }"
        )
        all_btn.clicked.connect(lambda: self._set_type_filter(None))
        self._type_btns[None] = all_btn
        type_lay.addWidget(all_btn)

        for t in sorted(ALL_TYPES):
            c = TYPE_HEX.get(t, '#585b70')
            _h = c.lstrip('#')
            _r, _g, _b = int(_h[0:2],16), int(_h[2:4],16), int(_h[4:6],16)
            btn = QPushButton(t.title())
            btn.setCheckable(True)
            btn.setFixedHeight(24)
            btn.setStyleSheet(
                f"QPushButton {{ background:rgba({_r},{_g},{_b},0.13); color:{c}; "
                f"border:1px solid rgba({_r},{_g},{_b},0.33); "
                "border-radius:4px; padding:0 6px; font-size:11px; font-weight:bold; }"
                f"QPushButton:checked {{ background:{c}; color:#1e1e2e; border-color:{c}; }}"
            )
            btn.clicked.connect(lambda _, typ=t: self._set_type_filter(typ))
            self._type_btns[t] = btn
            type_lay.addWidget(btn)
        type_lay.addStretch()

        type_scroll = QScrollArea()
        type_scroll.setWidgetResizable(True)
        type_scroll.setWidget(type_wrap)
        type_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        type_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        type_scroll.setFrameShape(QFrame.NoFrame)
        type_scroll.setFixedHeight(34)
        root.addWidget(type_scroll)

        # Body: list + detail panel
        body = QHBoxLayout(); body.setSpacing(10)

        self._list = QListWidget()
        self._list.setAlternatingRowColors(True)
        self._list.setSelectionMode(QAbstractItemView.SingleSelection)
        self._list.currentItemChanged.connect(self._on_item_changed)
        self._list.itemDoubleClicked.connect(self._accept)
        self._list.setItemDelegate(_SpriteItemDelegate(self._list))
        body.addWidget(self._list, 1)

        # Detail panel (fixed width)
        detail_w = QWidget(); detail_w.setFixedWidth(210)
        detail_w.setStyleSheet(
            "QWidget { background:#181825; border-radius:8px; border:1px solid #313244; }"
        )
        det_lay = QVBoxLayout(detail_w)
        det_lay.setContentsMargins(10, 14, 10, 12)
        det_lay.setSpacing(6)

        self._det_sprite = QLabel()
        self._det_sprite.setFixedSize(96, 96)
        self._det_sprite.setAlignment(Qt.AlignCenter)
        self._det_sprite.setStyleSheet("background:transparent; border:none;")
        sw = QHBoxLayout(); sw.addStretch(); sw.addWidget(self._det_sprite); sw.addStretch()
        det_lay.addLayout(sw)

        self._det_name = QLabel("\u2014")
        self._det_name.setAlignment(Qt.AlignCenter)
        self._det_name.setWordWrap(True)
        self._det_name.setStyleSheet("font-size:14px; font-weight:bold; color:#cdd6f4; border:none; background:transparent;")
        det_lay.addWidget(self._det_name)

        self._det_types_row = QHBoxLayout()
        self._det_types_row.setSpacing(4)
        det_lay.addLayout(self._det_types_row)

        sep = QFrame(); sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("background:#313244; max-height:1px; border:none;")
        det_lay.addWidget(sep)

        _STAT_COLS = ["#FF5959","#F5AC78","#FAE078","#9DB7F5","#A7DB8D","#FA92B2"]
        self._det_stat_rows = []
        for i, stat in enumerate(STAT_NAMES):
            row = QHBoxLayout(); row.setSpacing(4)
            sl = QLabel(stat)
            sl.setFixedWidth(32)
            sl.setStyleSheet(f"color:{_STAT_COLS[i]}; font-size:10px; font-weight:bold; border:none; background:transparent;")
            sl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            bar = QProgressBar()
            bar.setRange(0, 255); bar.setValue(0)
            bar.setFixedHeight(9); bar.setTextVisible(False)
            bar.setStyleSheet(
                f"QProgressBar {{ background:#313244; border:none; border-radius:3px; }}"
                f"QProgressBar::chunk {{ background:{_STAT_COLS[i]}; border-radius:3px; }}"
            )
            vl = QLabel("\u2014")
            vl.setFixedWidth(26)
            vl.setStyleSheet("color:#a6adc8; font-size:10px; border:none; background:transparent;")
            vl.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            row.addWidget(sl); row.addWidget(bar, 1); row.addWidget(vl)
            det_lay.addLayout(row)
            self._det_stat_rows.append((bar, vl))

        self._det_bst = QLabel("")
        self._det_bst.setAlignment(Qt.AlignCenter)
        self._det_bst.setStyleSheet("color:#89b4fa; font-size:11px; font-weight:bold; border:none; background:transparent;")
        det_lay.addWidget(self._det_bst)
        det_lay.addStretch()
        body.addWidget(detail_w)

        root.addLayout(body, 1)

        # Footer
        footer = QHBoxLayout()
        ok_btn = QPushButton("Select"); ok_btn.setObjectName("accent"); ok_btn.setFixedHeight(32)
        ok_btn.clicked.connect(self._accept)
        cancel_btn = QPushButton("Cancel"); cancel_btn.setFixedHeight(32)
        cancel_btn.clicked.connect(self.reject)
        footer.addStretch(); footer.addWidget(cancel_btn); footer.addWidget(ok_btn)
        root.addLayout(footer)

    # ── Filtering ─────────────────────────────────────────────────────────────
    def _set_type_filter(self, typ):
        self._type_filter = typ
        for t, btn in self._type_btns.items():
            btn.setChecked(t == typ)
        self._apply_filters()

    def _on_search(self, text):
        self._search_text = text.lower().strip()
        self._apply_filters()

    def _apply_filters(self):
        q = self._search_text
        t = self._type_filter
        self._filtered = [
            (name, p) for name, p in self._entries
            if (not q or q in name.lower())
            and (t is None or (p and (p.type1 == t or p.type2 == t)))
        ]
        self._populate()
        self._restore_selection()

    # ── List management ───────────────────────────────────────────────────────
    def _populate(self):
        self._list.clear()
        for name, p in self._filtered:
            if p and p.type1:
                t2 = f"/{p.type2.title()}" if (p.type2 and p.type2 != p.type1) else ""
                label = f"{name}  \u00b7  {p.type1.title()}{t2}"
            else:
                label = name
            item = QListWidgetItem(label)
            item.setData(Qt.UserRole, name)
            self._list.addItem(item)

    def _restore_selection(self):
        if not self.selected: return
        for i in range(self._list.count()):
            if self._list.item(i).data(Qt.UserRole) == self.selected:
                self._list.setCurrentRow(i)
                self._list.scrollToItem(self._list.item(i))
                return

    # ── Detail panel ──────────────────────────────────────────────────────────
    def _on_item_changed(self, cur, _prev):
        if not cur:
            self._clear_detail(); return
        name = cur.data(Qt.UserRole)
        p    = self._pkmn_map.get(name)
        self._update_detail(name, p)

    def _update_detail(self, name, p):
        # Sprite
        front, _ = pokemon_sprite(name)
        if front:
            pix = QPixmap(front)
            if not pix.isNull():
                if pix.height() > pix.width():
                    pix = pix.copy(0, 0, pix.width(), pix.width())
                pix = make_transparent_pixmap(pix)
                self._det_sprite.setPixmap(
                    pix.scaled(96, 96, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            else:
                self._det_sprite.clear()
        else:
            self._det_sprite.clear()
        # Name
        self._det_name.setText(name)
        # Types — clear then rebuild
        while self._det_types_row.count():
            it = self._det_types_row.takeAt(0)
            if it.widget(): it.widget().deleteLater()
        if p and p.type1:
            types = [p.type1]
            if p.type2 and p.type2 != p.type1: types.append(p.type2)
            for typ in types:
                c = TYPE_HEX.get(typ, '#585b70')
                lbl = QLabel(typ.title())
                lbl.setStyleSheet(
                    f"background:{_rgba(c,0.20)}; color:{c}; border:1px solid {_rgba(c,0.40)}; "
                    "border-radius:4px; padding:2px 8px; font-size:11px; font-weight:bold;"
                )
                self._det_types_row.addWidget(lbl)
            self._det_types_row.addStretch()
        # Stats
        stats = [p.hp, p.atk, p.def_, p.spa, p.spd, p.spe] if p else [0]*6
        for i, (bar, vl) in enumerate(self._det_stat_rows):
            v = stats[i] if i < len(stats) else 0
            bar.setValue(v); vl.setText(str(v) if v else "\u2014")
        self._det_bst.setText(f"BST: {p.bst}" if p else "")

    def _clear_detail(self):
        self._det_sprite.clear()
        self._det_name.setText("\u2014")
        while self._det_types_row.count():
            it = self._det_types_row.takeAt(0)
            if it.widget(): it.widget().deleteLater()
        for bar, vl in self._det_stat_rows:
            bar.setValue(0); vl.setText("\u2014")
        self._det_bst.setText("")

    # ── Accept / Cancel ───────────────────────────────────────────────────────
    def _clear_species(self):
        self.selected = ""; self.accept()

    def _accept(self):
        cur = self._list.currentItem()
        if cur: self.selected = cur.data(Qt.UserRole)
        self.accept()


# ══════════════════════════════════════════════════════════════════════════════
# MON EDITOR DIALOG
# ══════════════════════════════════════════════════════════════════════════════
class MonEditorDialog(_FramelessDialogBase):
    def __init__(self, mon: TrainerMon, slot_idx: int, parent=None):
        super().__init__(f"Edit Pokémon — Slot {slot_idx + 1}", parent)
        self.resize(800, 620)
        self.mon = mon
        self._slot_idx = slot_idx
        self._species_list = load_species()
        self._items  = load_items()
        self._moves  = load_moves()
        self._build_ui()
        self._load_from_mon()

    def _build_ui(self):
        root = self._root_layout
        root.setSpacing(10)

        # ── Header ───────────────────────────────────────────────────────────
        hdr = QHBoxLayout(); hdr.setSpacing(14)
        self._sprite_lbl = QLabel()
        self._sprite_lbl.setFixedSize(96, 96)
        self._sprite_lbl.setAlignment(Qt.AlignCenter)
        self._sprite_lbl.setStyleSheet(
            "background:#181825;border-radius:8px;border:1px solid #313244;color:#585b70;")
        hdr.addWidget(self._sprite_lbl)

        meta = QVBoxLayout(); meta.setSpacing(6)
        sp_row = QHBoxLayout()
        sp_row.addWidget(QLabel("Species:"))
        self._species_btn = QPushButton("\u2014 Select Species \u2014")
        self._species_btn.setFixedHeight(32)
        self._species_btn.setMinimumWidth(230)
        self._species_btn.setIconSize(QSize(28, 28))
        self._species_btn.setStyleSheet(
            "QPushButton { background:#313244; border:1px solid #585b70; border-radius:6px; "
            "  color:#cdd6f4; font-size:13px; font-weight:bold; text-align:left; padding-left:8px; }"
            "QPushButton:hover { background:#45475a; border-color:#89b4fa; }"
        )
        self._species_btn.clicked.connect(self._open_species_selector)
        sp_row.addWidget(self._species_btn)
        sp_row.addWidget(QLabel("Lv."))
        self._level_spin = QSpinBox(); self._level_spin.setRange(1,100)
        self._level_spin.setFixedWidth(60)
        self._level_spin.valueChanged.connect(lambda _v: self._update_stats_display())
        sp_row.addWidget(self._level_spin)
        sp_row.addStretch()
        meta.addLayout(sp_row)

        nick_row = QHBoxLayout()
        nick_row.addWidget(QLabel("Nickname:"))
        self._nick_edit = QLineEdit(); self._nick_edit.setMaxLength(10)
        self._nick_edit.setFixedWidth(150); self._nick_edit.setPlaceholderText("(none)")
        nick_row.addWidget(self._nick_edit)
        self._gender_btn = GenderToggleBtn()
        self._gender_btn.gender_changed.connect(lambda _: None)  # handled in _apply
        nick_row.addWidget(self._gender_btn)
        self._shiny_btn = QPushButton("☆")
        self._shiny_btn.setFixedSize(34, 28)
        self._shiny_btn.setCheckable(True)
        self._shiny_btn.setStyleSheet(
            "QPushButton { background:#1e1e2e; border:1px solid #45475a; border-radius:4px; "
            "color:#585b70; font-size:14px; padding:0; }"
            "QPushButton:checked { background:#2e2a1a; border-color:#f9e2af; color:#f9e2af; }"
            "QPushButton:hover { background:#313244; }"
        )
        self._shiny_btn.setToolTip("Shiny")
        self._shiny_btn.toggled.connect(self._update_sprite)
        nick_row.addWidget(self._shiny_btn)
        nick_row.addStretch()
        meta.addLayout(nick_row)

        remove_btn = QPushButton("Remove Mon")
        remove_btn.setObjectName("danger")
        remove_btn.setFixedWidth(110)
        remove_btn.clicked.connect(self._remove_mon)
        meta.addWidget(remove_btn)
        meta.addStretch()
        hdr.addLayout(meta)

        # ── Header col 3: Item / Ability / Nature ─────────────────────────────
        right_meta = QVBoxLayout(); right_meta.setSpacing(5)

        hi_row = QHBoxLayout(); hi_row.setSpacing(6)
        hi_row.addWidget(QLabel("Item:"))
        self._item_sprite = QLabel()
        self._item_sprite.setFixedSize(24, 24)
        self._item_sprite.setAlignment(Qt.AlignCenter)
        self._item_btn = QPushButton("— No Item —")
        self._item_btn.setFixedHeight(28)
        self._item_btn.clicked.connect(self._open_item_selector)
        hi_row.addWidget(self._item_sprite); hi_row.addWidget(self._item_btn, 1)
        right_meta.addLayout(hi_row)

        ab_row = QHBoxLayout(); ab_row.setSpacing(6)
        ab_row.addWidget(QLabel("Ability:"))
        self._ability_btn = QPushButton("— No Ability —")
        self._ability_btn.setFixedHeight(28)
        self._ability_btn.clicked.connect(self._open_ability_selector)
        ab_row.addWidget(self._ability_btn, 1)
        right_meta.addLayout(ab_row)
        self._ability_desc_lbl = QTextEdit()
        self._ability_desc_lbl.setReadOnly(True)
        self._ability_desc_lbl.setFixedHeight(48)
        self._ability_desc_lbl.setFrameShape(QFrame.NoFrame)
        self._ability_desc_lbl.setStyleSheet(
            "QTextEdit { background:#181825; color:#a6adc8; font-size:11px; "
            "font-style:italic; border:1px solid #313244; border-radius:4px; padding:3px; }"
        )
        right_meta.addWidget(self._ability_desc_lbl)

        nat_row = QHBoxLayout(); nat_row.setSpacing(6)
        nat_row.addWidget(QLabel("Nature:"))
        self._nature_cb = QComboBox()
        self._nature_cb.setFixedWidth(160)
        _fill_nature_combo(self._nature_cb)
        self._nature_cb.currentIndexChanged.connect(self._update_stats_display)
        nat_row.addWidget(self._nature_cb); nat_row.addStretch()
        right_meta.addLayout(nat_row)

        right_meta.addStretch()
        hdr.addLayout(right_meta)
        hdr.addStretch()
        root.addLayout(hdr)
        root.addWidget(_sep())

        # ── Tabs ─────────────────────────────────────────────────────────────
        tabs = QTabWidget()

        # Tab 1: Moves
        moves_tab = QWidget()
        moves_lay = QVBoxLayout(moves_tab)
        moves_lay.setContentsMargins(10, 10, 10, 10); moves_lay.setSpacing(8)
        self._move_rows = []
        for i in range(4):
            row = QHBoxLayout(); row.setSpacing(8)
            lbl = QLabel(f"Move {i+1}:")
            lbl.setFixedWidth(55)
            lbl.setStyleSheet("color:#6c7086;font-size:12px;")
            btn = QPushButton("— No Move —")
            btn.setFixedHeight(34)
            btn.setStyleSheet("text-align:left;padding-left:10px;")
            type_lbl = QLabel(""); type_lbl.setFixedWidth(70)
            cat_lbl  = QLabel(""); cat_lbl.setFixedWidth(70)
            pow_lbl  = QLabel(""); pow_lbl.setFixedWidth(60)
            acc_lbl  = QLabel(""); acc_lbl.setFixedWidth(60)
            for ll in (type_lbl, cat_lbl, pow_lbl, acc_lbl):
                ll.setStyleSheet("color:#6c7086;font-size:11px;")
            btn.clicked.connect(lambda _, idx=i: self._open_move_selector(idx))
            row.addWidget(lbl); row.addWidget(btn, 1)
            row.addWidget(type_lbl); row.addWidget(cat_lbl)
            row.addWidget(pow_lbl); row.addWidget(acc_lbl)
            moves_lay.addLayout(row)
            self._move_rows.append((btn, type_lbl, cat_lbl, pow_lbl, acc_lbl))
        moves_lay.addStretch()
        tabs.addTab(moves_tab, "Moves")

        # Tab 2: Stats
        stats_tab = QWidget()
        stats_lay = QVBoxLayout(stats_tab)
        stats_lay.setContentsMargins(14, 12, 14, 12); stats_lay.setSpacing(6)

        # HP Type badge row
        hp_hdr_row = QHBoxLayout()
        hp_hdr_row.addWidget(QLabel("Hidden Power:"))
        self._hp_type_badge = QLabel("")
        self._hp_type_badge.setStyleSheet(
            "background:#1a1a2e;border:1px solid #313244;border-radius:4px;"
            "padding:2px 10px;font-size:12px;font-weight:bold;color:#cdd6f4;")
        hp_hdr_row.addWidget(self._hp_type_badge)
        hp_hdr_row.addStretch()
        stats_lay.addLayout(hp_hdr_row)
        stats_lay.addWidget(_sep())

        # pokemon.db label colors (per-stat identity), uniform bar color (PS style)
        _STAT_LABEL_COLORS = ["#FF5959","#F5AC78","#FAE078","#9DB7F5","#A7DB8D","#FA92B2"]
        _BAR_COLOR = "#89b4fa"

        # Stat grid header
        hdr_grid = QHBoxLayout(); hdr_grid.setSpacing(4)
        for txt, w in [("Stat",48),("Base",45),("IV",56),("",120),("At Lv.",50),("",140)]:
            lbl = QLabel(txt)
            lbl.setFixedWidth(w)
            lbl.setStyleSheet("color:#585b70; font-size:10px;")
            hdr_grid.addWidget(lbl)
        hdr_grid.addStretch()
        stats_lay.addLayout(hdr_grid)

        self._iv_spins      = []
        self._iv_bars       = []
        self._iv_name_lbls  = []
        self._base_lbls     = []
        self._cur_stat_lbls = []
        self._cur_stat_bars = []

        for i, (sname, lbl_color) in enumerate(zip(STAT_NAMES, _STAT_LABEL_COLORS)):
            row = QHBoxLayout(); row.setSpacing(4)

            # Stat name + nature modifier badge in one fixed-width label
            name_lbl = QLabel(sname)
            name_lbl.setFixedWidth(48)
            name_lbl.setStyleSheet(f"color:{lbl_color};font-size:12px;font-weight:bold;")
            self._iv_name_lbls.append(name_lbl)

            # Base stat value
            base_lbl = QLabel("—")
            base_lbl.setFixedWidth(45)
            base_lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            base_lbl.setStyleSheet("color:#585b70; font-size:12px;")
            self._base_lbls.append(base_lbl)

            # IV spinbox — square corners
            spin = QSpinBox(); spin.setRange(0, 31); spin.setFixedWidth(56)
            spin.setStyleSheet(
                "QSpinBox { background:#313244; border:1px solid #45475a; border-radius:2px; "
                "color:#cdd6f4; font-size:12px; padding:1px 2px; }"
                "QSpinBox::up-button, QSpinBox::down-button { width:14px; }"
            )
            spin.valueChanged.connect(lambda v, idx=i: self._iv_changed(idx, v))
            self._iv_spins.append(spin)

            # IV progress bar — square, single accent color
            iv_bar = QProgressBar(); iv_bar.setRange(0, 31); iv_bar.setFixedHeight(10)
            iv_bar.setFixedWidth(120); iv_bar.setTextVisible(False)
            iv_bar.setStyleSheet(
                f"QProgressBar{{background:#313244;border-radius:2px;border:none;}}"
                f"QProgressBar::chunk{{background:{_BAR_COLOR};border-radius:2px;}}")
            self._iv_bars.append(iv_bar)

            # Current stat label
            cur_lbl = QLabel("—")
            cur_lbl.setFixedWidth(50)
            cur_lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            cur_lbl.setStyleSheet(f"color:{lbl_color}; font-size:12px; font-weight:bold;")
            self._cur_stat_lbls.append(cur_lbl)

            # Current stat progress bar — square, single accent color
            cur_bar = QProgressBar(); cur_bar.setRange(0, 714); cur_bar.setFixedHeight(10)
            cur_bar.setFixedWidth(140); cur_bar.setTextVisible(False)
            cur_bar.setStyleSheet(
                f"QProgressBar{{background:#313244;border-radius:2px;border:none;}}"
                f"QProgressBar::chunk{{background:{_BAR_COLOR}bb;border-radius:2px;}}")
            self._cur_stat_bars.append(cur_bar)

            row.addWidget(name_lbl)
            row.addWidget(base_lbl)
            row.addWidget(spin)
            row.addWidget(iv_bar)
            row.addWidget(cur_lbl)
            row.addWidget(cur_bar)
            row.addStretch()
            stats_lay.addLayout(row)

        stats_lay.addWidget(_sep())

        # BST + total row
        bst_row = QHBoxLayout()
        bst_row.addWidget(QLabel("BST:"))
        self._bst_lbl = QLabel("—")
        self._bst_lbl.setStyleSheet("color:#a6adc8; font-size:12px;")
        bst_row.addWidget(self._bst_lbl)
        bst_row.addSpacing(24)
        bst_row.addWidget(QLabel("Total at Lv.:"))
        self._total_stat_lbl = QLabel("—")
        self._total_stat_lbl.setStyleSheet("color:#89b4fa; font-size:12px; font-weight:bold;")
        bst_row.addWidget(self._total_stat_lbl)
        bst_row.addStretch()
        stats_lay.addLayout(bst_row)

        # HP Type optimizer row
        hp_opt_row = QHBoxLayout()
        hp_opt_row.addWidget(QLabel("Set HP Type:"))
        self._hp_type_combo = QComboBox()
        self._hp_type_combo.addItems(_HP_TYPES)
        self._hp_type_combo.setFixedWidth(120)
        hp_opt_row.addWidget(self._hp_type_combo)
        opt_btn = QPushButton("Optimize IVs")
        opt_btn.setFixedHeight(28)
        opt_btn.clicked.connect(self._optimize_ivs_for_hp_type)
        hp_opt_row.addWidget(opt_btn)
        hp_opt_row.addStretch()
        stats_lay.addLayout(hp_opt_row)

        # Happiness
        hap_row = QHBoxLayout(); hap_row.setSpacing(6)
        hap_row.addWidget(QLabel("Happiness:"))
        self._happiness_spin = QSpinBox(); self._happiness_spin.setRange(1, 255)
        self._happiness_spin.setValue(255); self._happiness_spin.setFixedWidth(70)
        hap_row.addWidget(self._happiness_spin); hap_row.addStretch()
        stats_lay.addLayout(hap_row)

        # Ball
        ball_row = QHBoxLayout(); ball_row.setSpacing(6)
        ball_row.addWidget(QLabel("Ball:"))
        self._ball_cb = QComboBox()
        self._ball_cb.addItems(_BALL_NAMES)
        self._ball_cb.setFixedWidth(150)
        ball_row.addWidget(self._ball_cb); ball_row.addStretch()
        stats_lay.addLayout(ball_row)

        stats_lay.addStretch()
        tabs.addTab(stats_tab, "Stats / IVs")

        root.addWidget(tabs, 1)

        # ── Footer ────────────────────────────────────────────────────────────
        footer = QHBoxLayout()
        apply_btn = QPushButton("Apply Changes"); apply_btn.setObjectName("accent")
        apply_btn.setFixedHeight(34)
        apply_btn.clicked.connect(self._apply)
        close_btn = QPushButton("Close"); close_btn.setFixedHeight(34)
        close_btn.clicked.connect(self.close)
        footer.addStretch(); footer.addWidget(close_btn); footer.addWidget(apply_btn)
        root.addLayout(footer)

    # ── Species helpers ───────────────────────────────────────────────────────
    def _get_species(self):
        """Return current species display name."""
        return self._species_btn.property('species_name') or ''

    def _set_species(self, display_name):
        """Set species, update button icon/text, fire on_species_changed."""
        self._species_btn.setProperty('species_name', display_name or '')
        self._species_btn.setText(f"  {display_name}" if display_name else "\u2014 Select Species \u2014")
        # Icon: small sprite thumbnail on the button
        if display_name:
            front, _ = pokemon_sprite(display_name)
            if front:
                pix = QPixmap(front)
                if not pix.isNull():
                    if pix.height() > pix.width():
                        pix = pix.copy(0, 0, pix.width(), pix.width())
                    pix = make_transparent_pixmap(pix)
                    self._species_btn.setIcon(
                        QIcon(pix.scaled(28, 28, Qt.KeepAspectRatio, Qt.SmoothTransformation)))
                else:
                    self._species_btn.setIcon(QIcon())
            else:
                self._species_btn.setIcon(QIcon())
        else:
            self._species_btn.setIcon(QIcon())
        self._on_species_changed(display_name or '')

    def _open_species_selector(self):
        dlg = SpeciesSelectorDialog(current=self._get_species(), parent=self)
        if dlg.exec_() == QDialog.Accepted:
            self._set_species(dlg.selected)

    # ── Data loading ──────────────────────────────────────────────────────────
    def _set_ability_display(self, ability_name):
        """Update ability button text and description label."""
        self._ability_btn.setProperty('current_ability', ability_name)
        self._ability_btn.setText(ability_name or "— No Ability —")
        if ability_name:
            info = load_ability_info()
            desc = info.get(ability_name.lower(), {}).get('desc', '')
            self._ability_desc_lbl.setPlainText(desc)
        else:
            self._ability_desc_lbl.setPlainText("")

    def _open_ability_selector(self):
        mega_key = _get_mega_species(self._get_species(), self.mon.held_item)
        effective_species = mega_key or self._get_species()
        current = self._ability_btn.property('current_ability') or ''
        dlg = AbilitySelectorDialog(species=effective_species, current_ability=current, parent=self)
        if dlg.exec_() == QDialog.Accepted:
            self._set_ability_display(dlg.selected)
            self.mon.ability = dlg.selected

    def _load_from_mon(self):
        m = self.mon
        # Species
        self._set_species(m.species)

        self._level_spin.setValue(m.level)
        self._nick_edit.setText(m.nickname)
        self._gender_btn.set_species(m.species)
        self._gender_btn.set_gender(m.gender)
        self._shiny_btn.setChecked(m.shiny)

        # Nature
        _fill_nature_combo(self._nature_cb, m.nature)

        # IVs
        for i, spin in enumerate(self._iv_spins):
            spin.blockSignals(True)
            spin.setValue(m.ivs[i] if i < len(m.ivs) else 31)
            spin.blockSignals(False)
            self._iv_bars[i].setValue(spin.value())
        self._update_stats_display()

        # Moves
        moves = m.moves + [""] * (4 - len(m.moves))
        for i, (btn, type_lbl, cat_lbl, pow_lbl, acc_lbl) in enumerate(self._move_rows):
            self._update_move_row(i, moves[i])

        # Item / Ability (in header) / Happiness (in Stats tab)
        self._set_item_display(m.held_item)
        self._set_ability_display(m.ability)
        self._happiness_spin.setValue(m.happiness)
        ball_idx = self._ball_cb.findText(m.ball or "")
        self._ball_cb.setCurrentIndex(max(0, ball_idx))

        self._update_sprite()

    def _on_species_changed(self, text):
        self._gender_btn.set_species(text)
        self._update_sprite()
        self._update_stats_display()
        # move slots keep their current moves; user re-opens selector if needed

    def _update_sprite(self, *_args):
        species  = self._get_species()
        mega_key = _get_mega_species(species, self.mon.held_item) if self.mon else None
        effective = mega_key if mega_key else species
        is_shiny = self._shiny_btn.isChecked()
        front_path, _ = pokemon_sprite(effective)
        if front_path:
            from PyQt5.QtGui import QPixmap as _QP
            raw = _QP(front_path)
            if not raw.isNull():
                if raw.height() > raw.width():
                    raw = raw.copy(0, 0, raw.width(), raw.width())
                raw = make_transparent_pixmap(raw)
                if is_shiny:
                    raw = make_shiny_pixmap(front_path, raw)
                self._sprite_lbl.setPixmap(
                    raw.scaled(96, 96, Qt.KeepAspectRatio, Qt.SmoothTransformation))
                return
        self._sprite_lbl.clear()
        self._sprite_lbl.setText("?")

    def _iv_changed(self, idx, val):
        self._iv_bars[idx].setValue(val)
        self._update_stats_display()

    def _update_hidden_power(self):
        """Update only the HP type badge (called from _update_stats_display)."""
        ivs = [s.value() for s in self._iv_spins]
        hp_type = calc_hidden_power(ivs)
        color = type_color(hp_type)
        self._hp_type_badge.setText(f"  {hp_type}  ")
        self._hp_type_badge.setStyleSheet(
            f"background:{_rgba(color,0.13)};color:{color};border:1px solid {_rgba(color,0.33)};"
            "border-radius:4px;padding:2px 10px;font-size:12px;font-weight:bold;")

    def _update_stats_display(self):
        """Recalculate and refresh all stat displays (IV bars, calculated stats, nature labels)."""
        nature = self._nature_cb.currentData() or self._nature_cb.currentText()
        boost, lower = NATURE_MODS.get(nature, (0, 0))

        _STAT_LABEL_COLORS = ["#FF5959","#F5AC78","#FAE078","#9DB7F5","#A7DB8D","#FA92B2"]
        # Update stat name labels (nature modifier highlights)
        for i, lbl in enumerate(self._iv_name_lbls):
            base_color = _STAT_LABEL_COLORS[i]
            if i > 0 and i == boost:
                lbl.setText(STAT_NAMES[i] + " ▲")
                lbl.setStyleSheet(
                    "color:#a6e3a1; font-size:12px; font-weight:bold; "
                    "background:#1a2e1a; border-radius:3px; padding:0 2px;")
            elif i > 0 and i == lower:
                lbl.setText(STAT_NAMES[i] + " ▼")
                lbl.setStyleSheet(
                    "color:#f38ba8; font-size:12px; font-weight:bold; "
                    "background:#2e1a1a; border-radius:3px; padding:0 2px;")
            else:
                lbl.setText(STAT_NAMES[i])
                lbl.setStyleSheet(f"color:{base_color}; font-size:12px; font-weight:bold;")

        # Update IV bars
        ivs = [s.value() for s in self._iv_spins]
        for i, bar in enumerate(self._iv_bars):
            bar.setValue(ivs[i])

        # Update HP type badge
        self._update_hidden_power()

        # Get base stats — use mega form's stats if mega stone is held
        species = self._get_species()
        level   = self._level_spin.value()
        mega_key = _get_mega_species(species, self.mon.held_item)
        effective_species = mega_key if mega_key else species
        base    = get_dex_base_stats(effective_species)
        evs     = [0] * 6  # EVs not editable here; use 0 for display

        stat_keys_ordered = ('hp','atk','def_','spa','spd','spe')
        if base:
            self._bst_lbl.setText(str(base.get('bst', '—')))
            # Set base stat values
            base_vals = [base.get(k, 0) for k in stat_keys_ordered]
            for i, lbl in enumerate(self._base_lbls):
                lbl.setText(str(base_vals[i]))

            # Calculate current stats
            calc = calc_all_ingame_stats(effective_species, ivs, evs, level, nature)
            total = 0
            for i, key in enumerate(stat_keys_ordered):
                val = calc.get(key, 0)
                total += val
                self._cur_stat_lbls[i].setText(str(val))
                self._cur_stat_bars[i].setValue(val)
            self._total_stat_lbl.setText(str(total))
        else:
            self._bst_lbl.setText("—")
            self._total_stat_lbl.setText("—")
            for lbl in self._base_lbls:
                lbl.setText("—")
            for lbl in self._cur_stat_lbls:
                lbl.setText("—")
            for bar in self._cur_stat_bars:
                bar.setValue(0)

    def _optimize_ivs_for_hp_type(self):
        """Set IV spinboxes to optimal values for the selected HP type."""
        target = self._hp_type_combo.currentText()
        optimal = optimal_ivs_for_hp_type(target)
        for i, spin in enumerate(self._iv_spins):
            spin.blockSignals(True)
            spin.setValue(optimal[i])
            spin.blockSignals(False)
        self._update_stats_display()

    def _update_iv_labels(self):
        """Legacy alias — calls _update_stats_display."""
        self._update_stats_display()

    def _update_move_row(self, idx, move_key):
        btn, type_lbl, cat_lbl, pow_lbl, acc_lbl = self._move_rows[idx]
        if not move_key:
            btn.setText("— No Move —")
            btn.setStyleSheet("text-align:left;padding-left:10px;")
            for ll in (type_lbl, cat_lbl, pow_lbl, acc_lbl): ll.setText("")
            return
        mv = move_lookup(move_key)  # handles both display names and MOVE_ keys
        if not mv:
            mv = self._moves.get(move_key, {})
        name = mv.get('name', move_key)
        t    = mv.get('type','').replace('TYPE_','')
        cat  = mv.get('category','')
        pw   = mv.get('power',0)
        acc  = mv.get('accuracy',0)
        tc   = type_color(t)
        btn.setText(f"  {name}")
        btn.setStyleSheet(f"text-align:left;padding-left:10px;"
                          f"background:{_rgba(tc,0.13)};border:1px solid {_rgba(tc,0.33)};border-radius:6px;")
        type_lbl.setText(t.title())
        type_lbl.setStyleSheet(f"color:{tc};font-size:11px;font-weight:bold;")
        cat_lbl.setText(cat_label(cat))
        cc = cat_color(cat)
        cat_lbl.setStyleSheet(f"color:{cc};font-size:11px;")
        pow_lbl.setText(f"Pow {pw}" if pw else "Pow —")
        acc_lbl.setText(f"Acc {acc}%" if acc else "Acc —")

    def _open_move_selector(self, idx):
        species = self._get_species()
        moves   = self._get_current_moves()
        current = moves[idx] if idx < len(moves) else ""
        dlg = MoveSelectorDialog(current=current, species=species, parent=self)
        if dlg.exec_() == QDialog.Accepted:
            # Update in the move list
            while len(moves) < 4: moves.append("")
            moves[idx] = dlg.selected
            # Trim trailing empty
            while moves and not moves[-1]: moves.pop()
            self.mon.moves = moves
            self._update_move_row(idx, dlg.selected)

    def _get_current_moves(self):
        moves = list(self.mon.moves)
        while len(moves) < 4: moves.append("")
        return moves

    def _set_item_display(self, item_key):
        self.mon.held_item = item_key
        tup = item_lookup(item_key) if item_key else None
        if tup:
            _, display, icon_path = tup
        else:
            display = "— No Item —" if not item_key else item_key
            icon_path = ""
        self._item_btn.setText(f"  {display}")
        pix = _item_pixmap(icon_path, 32)
        if pix: self._item_sprite.setPixmap(pix)
        else:   self._item_sprite.clear()
        # Mega stone check — refresh stats and sprite/abilities
        self._update_stats_display()
        self._update_sprite()

    def _open_item_selector(self):
        dlg = ItemSelectorDialog(current=self.mon.held_item, parent=self)
        if dlg.exec_() == QDialog.Accepted:
            self._set_item_display(dlg.selected)

    def _remove_mon(self):
        self.mon.species = ""
        self.close()

    def _apply(self):
        m = self.mon
        m.species       = self._get_species()
        m.level         = self._level_spin.value()
        m.nickname      = self._nick_edit.text().strip()
        m.gender        = self._gender_btn.get_gender()
        m.shiny         = self._shiny_btn.isChecked()
        m.nature        = self._nature_cb.currentData() or self._nature_cb.currentText()
        m.ivs           = [s.value() for s in self._iv_spins]
        m.ability       = self._ability_btn.property('current_ability') or ''
        m.happiness     = self._happiness_spin.value()
        m.ball          = self._ball_cb.currentText()
        # held_item already saved via _set_item_display
        # moves already saved via _open_move_selector
        self.close()


# ══════════════════════════════════════════════════════════════════════════════
# MON DETAIL DIALOG  — thin wrapper around MonEditorDialog with a callback
# ══════════════════════════════════════════════════════════════════════════════
class MonDetailDialog(MonEditorDialog):
    """Opens MonEditorDialog and fires callback(mon) when Apply is clicked."""
    def __init__(self, mon: TrainerMon, slot_idx: int, callback, parent=None):
        self._callback = callback
        super().__init__(mon, slot_idx, parent)

    def _apply(self):
        super()._apply()
        if self._callback:
            self._callback(self.mon)


# ══════════════════════════════════════════════════════════════════════════════
# FANCY TOOLTIP
# ══════════════════════════════════════════════════════════════════════════════

class _FancyTooltip(QWidget):
    """Singleton dark-themed overlay tooltip.

    Show via ``_FancyTooltip.instance().show_tip(title, body, accent, badges)``.
    All four args are plain strings.  *accent* is a CSS hex color used as the
    left border and title accent.  *badges* is optional info line (type / cat /
    stats) shown between the title and description.

    Implementation note: on first use the widget reparents itself into the
    active top-level window so it becomes a child widget instead of a
    top-level window.  This is the only reliable way to avoid the
    QWindowsWindow::setGeometry minimum-height warnings caused by DWM
    enforcing a non-zero frame height on every top-level window type
    (Qt.ToolTip, Qt.Tool, Qt.Window, etc.).  A child widget has no DWM
    involvement and can be any size.
    """
    _instance = None

    @classmethod
    def instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        # Start as a plain frameless top-level; will be embedded on first show.
        super().__init__(None,
            Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.NoDropShadowWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self._hide_timer = QTimer(self)
        self._hide_timer.setSingleShot(True)
        self._hide_timer.timeout.connect(self.hide)
        self._embedded = False
        self._build()

    # ── Layout ────────────────────────────────────────────────────────────────

    def _build(self):
        self._frame = QFrame(self)
        self._frame.setObjectName("ftip_frame")
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(self._frame)

        lay = QVBoxLayout(self._frame)
        lay.setContentsMargins(11, 8, 13, 8)
        lay.setSpacing(4)

        self._title_lbl = QLabel()
        self._title_lbl.setObjectName("ftip_title")
        self._badges_lbl = QLabel()
        self._badges_lbl.setObjectName("ftip_badges")
        self._sep_line = QFrame()
        self._sep_line.setFrameShape(QFrame.HLine)
        self._sep_line.setObjectName("ftip_sep")
        self._body_lbl = QLabel()
        self._body_lbl.setObjectName("ftip_body")
        self._body_lbl.setWordWrap(True)
        self._body_lbl.setMaximumWidth(300)

        lay.addWidget(self._title_lbl)
        lay.addWidget(self._badges_lbl)
        lay.addWidget(self._sep_line)
        lay.addWidget(self._body_lbl)

    # ── Embedding ─────────────────────────────────────────────────────────────

    def _try_embed(self):
        """Reparent into the active top-level window as a child widget.

        After this call the widget is no longer top-level: DWM imposes no
        minimum height on child widgets, eliminating the geometry warnings.
        """
        if self._embedded:
            return
        win = QApplication.activeWindow()
        if win and win is not self:
            self.setParent(win)
            # After setParent the window flags are reset to Qt.Widget (child).
            # Re-apply the attributes that survive a reparent.
            self.setAttribute(Qt.WA_TranslucentBackground)
            self.setAttribute(Qt.WA_ShowWithoutActivating)
            self._embedded = True

    # ── Public API ────────────────────────────────────────────────────────────

    def show_tip(self, title: str, body: str,
                 accent: str = "#585b70", badges: str = ""):
        """Update content and show the tooltip near the cursor."""
        self._hide_timer.stop()

        self._frame.setStyleSheet(f"""
            QFrame#ftip_frame {{
                background: #181825;
                border: 1px solid #313244;
                border-left: 3px solid {accent};
                border-radius: 8px;
            }}
            QLabel#ftip_title {{
                color: {accent};
                font-size: 13px;
                font-weight: bold;
                background: transparent;
                padding: 0;
            }}
            QLabel#ftip_badges {{
                color: #bac2de;
                font-size: 11px;
                background: transparent;
                padding: 0;
            }}
            QFrame#ftip_sep {{
                background: #313244;
                border: none;
                max-height: 1px;
                margin: 0;
            }}
            QLabel#ftip_body {{
                color: #a6adc8;
                font-size: 11px;
                background: transparent;
                padding: 0;
            }}
        """)

        self._title_lbl.setText(title)
        self._badges_lbl.setText(badges)
        self._badges_lbl.setVisible(bool(badges))
        self._sep_line.setVisible(bool(body))
        self._body_lbl.setText(body)
        self._body_lbl.setVisible(bool(body))

        # Embed into main window on first show so DWM never touches this widget.
        self._try_embed()

        self.adjustSize()
        w = self.sizeHint().width()
        h = self.sizeHint().height()
        self.setFixedSize(w, h)  # lock size; prevents any DWM or layout inflation

        if self._embedded and self.parent():
            parent = self.parent()
            local = parent.mapFromGlobal(QCursor.pos())
            x = local.x() + 18
            y = local.y() + 12
            # Clamp so the tooltip stays fully inside the parent window
            x = max(4, min(x, parent.width()  - w - 4))
            y = max(4, min(y, parent.height() - h - 4))
        else:
            # Fallback: position as a top-level relative to the screen
            pos = QCursor.pos()
            x, y = pos.x() + 18, pos.y() + 12
            screen = QApplication.primaryScreen().availableGeometry()
            if x + w > screen.right():   x = pos.x() - w - 10
            if y + h > screen.bottom():  y = pos.y() - h - 10

        self.move(x, y)
        self.raise_()
        self.show()

    def schedule_hide(self, ms: int = 90):
        """Start the auto-hide timer (cancelled if show_tip fires first)."""
        self._hide_timer.start(ms)

    def cancel_hide(self):
        self._hide_timer.stop()


def _install_tip(widget, content_fn):
    """Install a hover tooltip on *widget*.

    *content_fn* is called with no args on each Enter event and must return
    either ``None`` (no tooltip) or a 4-tuple ``(title, body, accent, badges)``
    matching ``_FancyTooltip.show_tip``.

    Returns the installed ``QObject`` filter so the caller can keep a reference.
    """
    class _Filter(QObject):
        def eventFilter(self, obj, event):
            tip = _FancyTooltip.instance()
            t = event.type()
            if t == QEvent.Enter:
                result = content_fn()
                if result:
                    tip.cancel_hide()
                    tip.show_tip(*result)
                else:
                    tip.schedule_hide(90)
            elif t in (QEvent.Leave, QEvent.Hide):
                tip.schedule_hide(90)
            return False   # never consume the event

    f = _Filter(widget)
    widget.installEventFilter(f)
    return f


# ══════════════════════════════════════════════════════════════════════════════
# MON SLOT CARD  — single Pokémon card widget (~180px wide)
# ══════════════════════════════════════════════════════════════════════════════
class MonSlotCard(QFrame):
    """A vertical card representing one party slot."""
    slot_double_clicked = pyqtSignal(int)   # emits slot_idx  (edit filled / add to empty)
    slot_cleared        = pyqtSignal(int)   # emits slot_idx

    def __init__(self, slot_idx: int, parent=None):
        super().__init__(parent)
        self._slot_idx = slot_idx
        self._mon      = None
        self._moves_data = load_moves()
        self._items_data = load_items()
        self._normal_pix = None
        self._shiny_pix  = None
        self._front_path = ""
        self._build_ui()

    def _build_ui(self):
        self.setMinimumWidth(172)
        self.setCursor(Qt.PointingHandCursor)
        self.setStyleSheet(
            "MonSlotCard { background:#252536; border:1px solid #313244; border-radius:8px; }"
        )
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(6, 6, 6, 6)
        lay.setSpacing(4)

        # Header row: slot label + remove button
        hdr = QHBoxLayout(); hdr.setSpacing(4)
        self._slot_lbl = QLabel(f"Slot {self._slot_idx + 1}")
        self._slot_lbl.setStyleSheet("color:#585b70; font-size:11px;")
        self._clear_btn = QPushButton("✕")
        self._clear_btn.setFixedSize(20, 20)
        self._clear_btn.setStyleSheet(
            "QPushButton { background:transparent; border:none; color:#585b70; font-size:12px; padding:0; }"
            "QPushButton:hover { color:#f38ba8; }"
        )
        self._clear_btn.setToolTip("Remove Pokémon")
        self._clear_btn.clicked.connect(self._confirm_remove)
        hdr.addWidget(self._slot_lbl)
        hdr.addStretch()
        hdr.addWidget(self._clear_btn)
        lay.addLayout(hdr)

        # Sprite area
        self._sprite_lbl = QLabel()
        self._sprite_lbl.setMinimumSize(64, 64)
        self._sprite_lbl.setAlignment(Qt.AlignCenter)
        self._sprite_lbl.setStyleSheet(
            "background:#181825; border-radius:6px; border:1px solid #313244; color:#585b70;"
        )
        self._sprite_lbl.setText("?")
        self._sprite_lbl.setCursor(Qt.PointingHandCursor)
        sprite_wrapper = QWidget()
        sprite_wrapper.setStyleSheet("background:transparent;")
        sw_lay = QHBoxLayout(sprite_wrapper)
        sw_lay.setContentsMargins(0, 0, 0, 0)
        sw_lay.addStretch()
        sw_lay.addWidget(self._sprite_lbl)
        sw_lay.addStretch()
        lay.addWidget(sprite_wrapper)

        # Name + level (inline spinner for quick level edits)
        self._name_lbl = QLabel("— Empty —")
        self._name_lbl.setAlignment(Qt.AlignCenter)
        self._name_lbl.setStyleSheet("font-weight:bold; font-size:13px; color:#cdd6f4;")
        lay.addWidget(self._name_lbl)

        lv_row = QHBoxLayout(); lv_row.setSpacing(4); lv_row.setContentsMargins(0,0,0,0)
        lv_lbl = QLabel("Lv.")
        lv_lbl.setStyleSheet("font-size:11px; color:#585b70;")
        self._level_spin_card = QSpinBox()
        self._level_spin_card.setRange(1, 100)
        self._level_spin_card.setFixedHeight(20)
        self._level_spin_card.setStyleSheet(
            "QSpinBox { background:#1e1e2e; border:1px solid #313244; border-radius:4px; "
            "  font-size:11px; color:#a6e3a1; padding:0 2px; min-height:18px; }"
            "QSpinBox:hover { border-color:#585b70; }"
            "QSpinBox::up-button, QSpinBox::down-button { width:14px; }"
        )
        self._level_spin_card.valueChanged.connect(self._on_level_card_changed)
        lv_row.addStretch()
        lv_row.addWidget(lv_lbl)
        lv_row.addWidget(self._level_spin_card)
        lv_row.addStretch()
        lay.addLayout(lv_row)

        lay.addWidget(_sep())

        # Item row — icon + name using QPushButton.setIcon() (no overlay label needed)
        self._item_btn = QPushButton("— No Item —")
        self._item_btn.setFixedHeight(28)
        self._item_btn.setIconSize(QSize(20, 20))
        self._item_btn.setStyleSheet(
            "QPushButton { background:#1e1e2e; border:1px solid #313244; border-radius:4px; "
            "font-size:11px; color:#a6adc8; text-align:left; padding:4px 6px 4px 6px; }"
            "QPushButton:hover { background:#313244; border-color:#585b70; }"
        )
        self._item_btn.clicked.connect(self._on_item_clicked)
        _install_tip(self._item_btn, self._tip_item)
        lay.addWidget(self._item_btn)

        # Ability + Nature — grouped tightly
        ab_nat = QVBoxLayout(); ab_nat.setSpacing(2); ab_nat.setContentsMargins(0,0,0,0)

        self._ability_cb = QComboBox()
        self._ability_cb.setFixedHeight(20)
        self._ability_cb.setMaximumWidth(160)
        self._ability_cb.setStyleSheet(
            "QComboBox { background:#1e1e2e; border:1px solid #313244; border-radius:4px; "
            "  font-size:10px; color:#89dceb; padding-left:4px; }"
            "QComboBox:hover { border-color:#585b70; }"
            "QComboBox::drop-down { border:none; width:14px; }"
        )
        self._ability_cb.currentTextChanged.connect(self._on_ability_changed)
        _install_tip(self._ability_cb, self._tip_ability)
        ab_nat.addWidget(self._ability_cb)

        self._nature_cb = QComboBox()
        self._nature_cb.setFixedHeight(20)
        self._nature_cb.setStyleSheet(
            "QComboBox { background:#1e1e2e; border:1px solid #313244; border-radius:4px; "
            "  font-size:10px; color:#cba6f7; padding-left:4px; }"
            "QComboBox:hover { border-color:#585b70; }"
            "QComboBox::drop-down { border:none; width:14px; }"
        )
        _fill_nature_combo(self._nature_cb)
        self._nature_cb.currentIndexChanged.connect(self._on_nature_changed)
        _install_tip(self._nature_cb, self._tip_nature)
        ab_nat.addWidget(self._nature_cb)
        lay.addLayout(ab_nat)

        lay.addWidget(_sep())

        # 4 move buttons
        self._move_btns = []
        for i in range(4):
            btn = QPushButton("— No Move —")
            btn.setFixedHeight(26)
            btn.setStyleSheet(
                "QPushButton { background:#313244; border:1px solid #45475a; border-radius:4px; "
                "font-size:11px; color:#585b70; text-align:left; padding-left:6px; }"
                "QPushButton:hover { background:#45475a; }"
            )
            btn.clicked.connect(lambda _, idx=i: self._on_move_clicked(idx))
            _install_tip(btn, lambda idx=i: self._tip_move(idx))
            lay.addWidget(btn)
            self._move_btns.append(btn)

        # Install hover tooltips on the passive click-to-edit areas
        _install_tip(self._sprite_lbl, self._tip_card)
        _install_tip(self._name_lbl,   self._tip_card)

        lay.addStretch()

    def mousePressEvent(self, event):
        """Single-click anywhere on the card (background, sprite, labels) opens the detail popout.
        Clicks on interactive children (buttons, combos, spinbox) are consumed by those widgets
        and do NOT propagate here, so they remain fully functional."""
        if event.button() == Qt.LeftButton:
            self.slot_double_clicked.emit(self._slot_idx)
        super().mousePressEvent(event)

    # ── Card-level hover → "click to open" tooltip ───────────────────────────
    def enterEvent(self, event):
        result = self._tip_card()
        if result:
            _FancyTooltip.instance().cancel_hide()
            _FancyTooltip.instance().show_tip(*result)
        super().enterEvent(event)

    def leaveEvent(self, event):
        _FancyTooltip.instance().schedule_hide(90)
        super().leaveEvent(event)

    _BASE_CARD_W = 172  # design-reference card width

    def resizeEvent(self, event):
        """Scale the sprite label (and its pixmap) as the card grows with the window."""
        super().resizeEvent(event)
        new_w = event.size().width()
        scale = new_w / self._BASE_CARD_W
        sz = max(64, min(int(80 * scale), 200))
        if self._sprite_lbl.width() != sz:
            self._sprite_lbl.setFixedSize(sz, sz)
            if self._front_path:
                self._refresh_card_sprite(self._mon.shiny if self._mon else False)

    # ── Tooltip content functions ─────────────────────────────────────────────
    def _tip_card(self):
        """Content for the card background / sprite / name hover tooltip."""
        if self._mon and self._mon.species:
            return (
                "Open Pokémon Editor",
                "Click to open the advanced editor for this slot.",
                "#89b4fa",
                "",
            )
        return (
            "Empty Slot",
            "Click to add a Pokémon to this slot.",
            "#585b70",
            "",
        )

    def _tip_item(self):
        """Content for the held-item button hover tooltip."""
        if self._mon is None or not self._mon.held_item:
            return (
                "Held Item",
                "No item held. Click to pick one.",
                "#f9e2af",
                "",
            )
        tup = item_lookup(self._mon.held_item)
        if not tup:
            return (self._mon.held_item, "No description available.", "#f9e2af", "")
        key, display, _ = tup
        descs = load_item_descriptions()
        desc = descs.get(key, "") or "No description available."
        return (display, desc, "#f9e2af", "")

    def _tip_move(self, move_idx: int):
        """Content for a move button hover tooltip."""
        if self._mon is None:
            return None
        move_name = (self._mon.moves[move_idx]
                     if move_idx < len(self._mon.moves) else "")
        if not move_name:
            return (f"Move Slot {move_idx + 1}", "No move assigned. Click to pick one.",
                    "#585b70", "")
        mv = move_lookup(move_name)
        if not mv:
            return (move_name, "Unknown move.", "#585b70", "")
        t     = mv.get('type', '').replace('TYPE_', '').strip()
        color = type_color(t)
        cat   = cat_label(mv.get('category', ''))
        pwr   = mv.get('power', 0)
        acc   = mv.get('accuracy', 0)
        pp    = mv.get('pp', 0)
        desc  = mv.get('description', '') or "No description available."
        badges = (
            f"{t.title() or '—'}  ·  {cat}  ·  "
            f"Pwr: {pwr or '—'}  ·  Acc: {f'{acc}%' if acc else '—'}  ·  PP: {pp or '—'}"
        )
        return (mv.get('name', move_name), desc, color, badges)

    def _tip_ability(self):
        """Content for the ability combo-box hover tooltip."""
        ab_name = self._ability_cb.currentText().strip()
        if not ab_name:
            return ("Ability", "No ability selected.", "#89dceb", "")
        info = load_ability_info()
        ab = info.get(ab_name.lower())
        if not ab:
            return (ab_name, "No description available.", "#89dceb", "")
        return (ab['name'], ab.get('desc') or "No description available.", "#89dceb", "")

    def _tip_nature(self):
        """Content for the nature combo-box hover tooltip."""
        idx = self._nature_cb.currentIndex()
        nature = self._nature_cb.itemData(idx) if idx >= 0 else ""
        if not nature:
            return ("Nature", "No nature selected.", "#cba6f7", "")
        bi, ri = NATURE_MODS.get(nature, (0, 0))
        stat_short = ["", "Atk", "Def", "SpA", "SpD", "Spe"]
        if bi and ri:
            body = f"+10% {stat_short[bi]}  /  −10% {stat_short[ri]}"
        else:
            body = "Neutral — no stat modifications."
        return (nature, body, "#cba6f7", "")

    def _on_sprite_dbl_click(self, event):
        self.slot_double_clicked.emit(self._slot_idx)

    def _on_sprite_click(self, event):
        """Single-click on an empty slot opens the add-mon dialog."""
        if event.button() == Qt.LeftButton:
            self.slot_double_clicked.emit(self._slot_idx)

    def _confirm_remove(self):
        """Ask for confirmation before clearing a filled slot."""
        if self._mon is None:
            return
        name = self._mon.nickname or self._mon.species or "this Pokémon"
        reply = QMessageBox.question(
            self, "Remove Pokémon",
            f"Remove {name} from slot {self._slot_idx + 1}?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.slot_cleared.emit(self._slot_idx)

    def _show_context_menu(self, pos):
        menu = QMenu(self)
        if self._mon and self._mon.species:
            edit_act  = menu.addAction("✏  Edit Pokémon")
            menu.addSeparator()
            rem_act   = menu.addAction("✕  Remove Pokémon")
            rem_act.setStyleSheet("color:#f38ba8;")
            chosen = menu.exec_(self.mapToGlobal(pos))
            if chosen == edit_act:
                self.slot_double_clicked.emit(self._slot_idx)
            elif chosen == rem_act:
                self._confirm_remove()
        else:
            add_act = menu.addAction("＋  Add Pokémon")
            if menu.exec_(self.mapToGlobal(pos)) == add_act:
                self.slot_double_clicked.emit(self._slot_idx)

    def _on_ability_changed(self, text):
        if self._mon is not None and text:
            self._mon.ability = text

    def _on_nature_changed(self, index):
        if self._mon is not None and index >= 0:
            nature = self._nature_cb.itemData(index)
            if nature:
                self._mon.nature = nature

    def _on_level_card_changed(self, val):
        if self._mon:
            self._mon.level = val

    def _on_item_clicked(self):
        """Open ItemSelectorDialog to pick a held item."""
        if self._mon is None:
            return
        dlg = ItemSelectorDialog(current=self._mon.held_item, parent=self)
        if dlg.exec_() == QDialog.Accepted:
            self._mon.held_item = dlg.selected   # ItemSelectorDialog uses .selected
            self._refresh_item()
            # Reset to base species sprite/types before mega check
            front_path, _ = pokemon_sprite(self._mon.species)
            self._front_path = front_path or ""
            self._normal_pix = None
            self._shiny_pix  = None
            self._refresh_card_sprite(self._mon.shiny)
            _base = get_dex_base_stats(self._mon.species)
            self._apply_type_border(
                _base.get('type1','') if _base else '',
                _base.get('type2','') if _base else ''
            )
            # Then apply mega override if applicable
            self._refresh_mega(self._mon)

    def _on_move_clicked(self, move_idx):
        """Quick move pick via MoveSelectorDialog."""
        if self._mon is None:
            return
        dlg = MoveSelectorDialog(
            species=self._mon.species,
            restricted=True,
            current=self._mon.moves[move_idx] if move_idx < len(self._mon.moves) else "",
            parent=self
        )
        if dlg.exec_() == QDialog.Accepted:
            while len(self._mon.moves) <= move_idx:
                self._mon.moves.append("")
            self._mon.moves[move_idx] = dlg.selected_move
            self._refresh_moves()

    def load_mon(self, mon: TrainerMon):
        """Populate card with a TrainerMon (or None to show empty slot)."""
        self._mon = mon
        if mon is None or not mon.species:
            # ── Empty state ──────────────────────────────────────────────────
            self._sprite_lbl.clear()
            self._sprite_lbl.setText("＋")
            self._sprite_lbl.setStyleSheet(
                "background:#181825; border-radius:6px; border:2px dashed #45475a; "
                "color:#45475a; font-size:30px; font-weight:bold;"
            )
            self._sprite_lbl.setCursor(Qt.PointingHandCursor)
            self._clear_btn.hide()
            self._name_lbl.setText("Add Pokémon")
            self._name_lbl.setStyleSheet("font-weight:bold; font-size:11px; color:#45475a;")
            self._level_spin_card.blockSignals(True)
            self._level_spin_card.setValue(1)
            self._level_spin_card.blockSignals(False)
            self._level_spin_card.setEnabled(False)
            self._item_btn.setText("— No Item —")
            self._item_btn.setIcon(QIcon())
            self._ability_cb.blockSignals(True)
            self._ability_cb.clear()
            self._ability_cb.blockSignals(False)
            self._nature_cb.blockSignals(True)
            self._nature_cb.clear()
            self._nature_cb.blockSignals(False)
            for btn in self._move_btns:
                btn.setText("— —")
                btn.setStyleSheet(
                    "QPushButton { background:#1e1e2e; border:1px solid #313244; border-radius:4px; "
                    "font-size:10px; color:#313244; text-align:center; padding:0; }"
                )
            self._apply_type_border('', '')
            return

        # ── Filled state: restore sprite label behaviour ─────────────────────
        self._sprite_lbl.setStyleSheet(
            "background:#181825; border-radius:6px; border:1px solid #313244; color:#585b70;"
        )
        self._sprite_lbl.setCursor(Qt.PointingHandCursor)
        self._clear_btn.show()

        # Sprite (with shiny support)
        front_path, _ = pokemon_sprite(mon.species)
        self._front_path  = front_path or ""
        self._normal_pix  = None
        self._shiny_pix   = None
        self._refresh_card_sprite(mon.shiny)

        # Name + gender symbol (genderless gets ◎, gendered gets ♂/♀)
        base_name = mon.nickname if mon.nickname else mon.species.replace('SPECIES_','').replace('_',' ').title()
        _base_g   = get_dex_base_stats(mon.species)
        _gr       = _base_g.get('gender_ratio', 127) if _base_g else 127
        if _gr == 255:
            gender_sym = ""   # genderless — no symbol (clean)
        elif mon.gender == "Male":
            gender_sym = " \u2642"
        elif mon.gender == "Female":
            gender_sym = " \u2640"
        else:
            gender_sym = ""
        self._name_lbl.setText(base_name + gender_sym)
        self._name_lbl.setStyleSheet("font-weight:bold; font-size:12px; color:#cdd6f4;")

        # Level
        self._level_spin_card.blockSignals(True)
        self._level_spin_card.setValue(mon.level)
        self._level_spin_card.blockSignals(False)
        self._level_spin_card.setEnabled(True)

        # Item — use reverse lookup to handle both "Eviolite" and "ITEM_EVIOLITE" forms
        self._refresh_item()

        # Ability — populate restricted options then restore saved value
        self._ability_cb.blockSignals(True)
        self._ability_cb.clear()
        self._ability_cb.addItem("")
        base = get_dex_base_stats(mon.species)
        abilities = base.get('abilities', ('', '', '')) if base else ('', '', '')
        seen_abs = set()
        for ab in abilities:
            if ab and ab not in seen_abs:
                self._ability_cb.addItem(ab)
                seen_abs.add(ab)
        idx = self._ability_cb.findText(mon.ability)
        if idx >= 0:
            self._ability_cb.setCurrentIndex(idx)
        else:
            if mon.ability:
                self._ability_cb.addItem(mon.ability)
                self._ability_cb.setCurrentText(mon.ability)
        self._ability_cb.blockSignals(False)

        # Nature — refill combo and select current nature
        _fill_nature_combo(self._nature_cb, mon.nature or "Hardy")

        self._refresh_moves()
        # Type-colored border (left=type1, right=type2)
        _base = get_dex_base_stats(mon.species)
        self._apply_type_border(
            _base.get('type1','') if _base else '',
            _base.get('type2','') if _base else ''
        )
        # Mega stone override: update sprite/types/abilities if mega stone held
        self._refresh_mega(mon)

    def _refresh_card_sprite(self, shiny: bool):
        """Load (and cache) the normal or shiny sprite for the current mon."""
        path = self._front_path
        if not path:
            self._sprite_lbl.clear()
            self._sprite_lbl.setText("?")
            return
        if self._normal_pix is None:
            from PyQt5.QtGui import QPixmap as _QP
            raw = _QP(path)
            if not raw.isNull():
                if raw.height() > raw.width():
                    raw = raw.copy(0, 0, raw.width(), raw.width())
                raw = make_transparent_pixmap(raw)
                self._normal_pix = raw
        if shiny and self._shiny_pix is None and self._normal_pix:
            self._shiny_pix = make_shiny_pixmap(path, self._normal_pix)
        pix = (self._shiny_pix if shiny and self._shiny_pix else self._normal_pix)
        if pix:
            sz = self._sprite_lbl.width() or 80
            self._sprite_lbl.setPixmap(
                pix.scaled(sz, sz, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        else:
            self._sprite_lbl.clear()
            self._sprite_lbl.setText("?")

    def _refresh_item(self):
        """Update the item button display from self._mon.held_item."""
        if self._mon is None:
            return
        tup = item_lookup(self._mon.held_item) if self._mon.held_item else None
        if tup:
            _, display, icon_path = tup
            pix = _item_pixmap(icon_path, 20)
            self._item_btn.setIcon(QIcon(pix) if pix else QIcon())
            self._item_btn.setText(f"  {display}")
        else:
            self._item_btn.setIcon(QIcon())
            txt = self._mon.held_item if self._mon.held_item else "— No Item —"
            self._item_btn.setText(txt)

    def _refresh_mega(self, mon):
        """If mon holds the correct mega stone, update sprite/types/abilities to mega form."""
        mega_key = _get_mega_species(mon.species, mon.held_item)
        if not mega_key:
            return
        # Update sprite to mega form
        front_path, _ = pokemon_sprite(mega_key)
        if front_path:
            self._front_path = front_path
            self._normal_pix = None
            self._shiny_pix  = None
            self._refresh_card_sprite(mon.shiny)
        # Update type border and abilities from mega stats
        mega_base = get_dex_base_stats(mega_key)
        if mega_base:
            self._apply_type_border(
                mega_base.get('type1', ''),
                mega_base.get('type2', '')
            )
            self._ability_cb.blockSignals(True)
            self._ability_cb.clear()
            self._ability_cb.addItem("")
            seen = set()
            for ab in mega_base.get('abilities', ('', '', '')):
                if ab and ab not in seen:
                    self._ability_cb.addItem(ab)
                    seen.add(ab)
            idx = self._ability_cb.findText(mon.ability)
            if idx >= 0:
                self._ability_cb.setCurrentIndex(idx)
            elif mon.ability:
                self._ability_cb.addItem(mon.ability)
                self._ability_cb.setCurrentText(mon.ability)
            self._ability_cb.blockSignals(False)

    def _refresh_moves(self):
        if self._mon is None:
            return
        for i, btn in enumerate(self._move_btns):
            move_name = self._mon.moves[i] if i < len(self._mon.moves) else ""
            if move_name:
                # Use reverse lookup so display names ("Wing Attack") AND MOVE_ keys both work
                mv = move_lookup(move_name)
                name = mv.get('name', move_name)   # fallback: display as-is
                t = mv.get('type','').replace('TYPE_','').strip()
                color = type_color(t)   # returns "#585b70" (grey) when type unknown
                btn.setText(name)
                btn.setStyleSheet(
                    f"QPushButton {{ background:{color}; border:none; "
                    f"border-radius:4px; font-size:10px; font-weight:bold; color:#ffffff; "
                    f"text-align:center; padding:0; }}"
                    f"QPushButton:hover {{ background:{_rgba(color,0.75)}; }}"
                )
            else:
                btn.setText("— —")
                btn.setStyleSheet(
                    "QPushButton { background:#313244; border:1px solid #45475a; border-radius:4px; "
                    "font-size:10px; color:#585b70; text-align:center; padding:0; }"
                    "QPushButton:hover { background:#45475a; }"
                )

    def _apply_type_border(self, type1: str, type2: str):
        """Style card border using type colors — left=type1, right=type2."""
        c1 = type_color(type1) if type1 else "#313244"
        c2 = type_color(type2) if type2 else c1
        self.setStyleSheet(
            "MonSlotCard { "
            "background:#252536; border-radius:8px; "
            f"border-top:1px solid #45475a; border-bottom:1px solid #45475a; "
            f"border-left:3px solid {c1}; border-right:3px solid {c2};"
            " }"
        )

    def get_mon(self):
        return self._mon


# ══════════════════════════════════════════════════════════════════════════════
# TEAM TYPE ANALYSIS DIALOG
# ══════════════════════════════════════════════════════════════════════════════
class TeamTypeAnalysisDialog(_FramelessDialogBase):
    """Pop-out showing team defensive + offensive type analysis."""

    def __init__(self, party, parent=None):
        super().__init__("Team Type Analysis", parent)
        self.resize(820, 700)
        self._party = [m for m in party if m and m.species]
        self._moves_data = load_moves()
        self._build_ui()

    # ── Offensive coverage helper ─────────────────────────────────────────────

    def _calc_offensive(self):
        """Returns (coverage, holes, per_mon).

        coverage  : def_type → list of (mon_display, source_label, atk_type)
        holes     : def types with zero SE coverage across whole team
        per_mon   : mon_display → {'atk_types': set, 'def_covered': set}
        """
        coverage = {}
        per_mon  = {}

        for mon in self._party:
            base = get_dex_base_stats(mon.species)
            mon_types = set()
            if base:
                for k in ('type1', 'type2'):
                    if base.get(k): mon_types.add(base[k].upper())

            # Attacking types available: from moves + STAB types
            atk_sources = {}    # atk_type → first source label seen
            for mk in (mon.moves or []):
                if not mk: continue
                mv  = self._moves_data.get(mk.upper()) or self._moves_data.get(mk) or {}
                mt  = (mv.get('type') or '').upper()
                if mt and mt not in atk_sources:
                    atk_sources[mt] = mk.replace('MOVE_','').replace('_',' ').title()
            for t in mon_types:
                if t not in atk_sources:
                    atk_sources[t] = '(STAB)'

            def_covered = set()
            mon_display = mon.species.replace('SPECIES_','').replace('_',' ').title()
            for atk_type, source in atk_sources.items():
                for def_type, mult in _TYPE_CHART.get(atk_type, {}).items():
                    if mult >= 2:
                        def_covered.add(def_type)
                        coverage.setdefault(def_type, []).append(
                            (mon_display, source, atk_type))

            per_mon[mon_display] = {
                'atk_types':  set(atk_sources.keys()),
                'def_covered': def_covered,
            }

        holes = [t for t in ALL_TYPES if not coverage.get(t)]
        return coverage, holes, per_mon

    # ── Tab builders ─────────────────────────────────────────────────────────

    def _type_badge(self, type_name, height=20, pad="0 6px"):
        tc  = TYPE_HEX.get(type_name, "#585b70")
        lbl = QLabel(type_name.title())
        lbl.setFixedHeight(height)
        lbl.setAlignment(Qt.AlignCenter)
        lbl.setStyleSheet(
            f"background:{tc}; color:#ffffff; border-radius:3px; "
            f"font-size:11px; font-weight:bold; padding:{pad};")
        return lbl

    def _summary_pill(self, text, fg, bg=None):
        lbl = QLabel(f"  {text}  ")
        bg2 = bg or (fg + "22")
        lbl.setStyleSheet(
            f"color:{fg}; background:{bg2}; border:1px solid {fg}44; "
            f"border-radius:4px; font-size:11px; font-weight:bold; padding:3px 0;")
        return lbl

    def _build_defensive_tab(self):
        w   = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(14, 12, 14, 8)
        lay.setSpacing(10)

        profile = calc_team_type_profile(self._party)
        n       = len(self._party)

        def _danger(t):
            d = profile[t]
            return d['4x']*4 + d['2x']*2 - d['half'] - d['quarter']*2 - d['immune']*3

        n_crit   = sum(1 for t in ALL_TYPES if profile[t]['4x'] > 0)
        n_weak   = sum(1 for t in ALL_TYPES if profile[t]['4x'] == 0 and profile[t]['2x'] > 0)
        n_immune = sum(1 for t in ALL_TYPES if profile[t]['immune'] > 0)
        n_resist = sum(1 for t in ALL_TYPES if profile[t]['4x'] == 0 and profile[t]['2x'] == 0
                       and (profile[t]['half'] > 0 or profile[t]['quarter'] > 0))

        # Summary row
        sr = QHBoxLayout(); sr.setSpacing(8)
        sr.addWidget(self._summary_pill(f"{n_crit} critical (4×) weaknesses", "#f38ba8"))
        sr.addWidget(self._summary_pill(f"{n_weak} standard (2×) weaknesses", "#fab387"))
        sr.addWidget(self._summary_pill(f"{n_resist} resisted types", "#a6e3a1"))
        sr.addWidget(self._summary_pill(f"{n_immune} immunities", "#cba6f7"))
        sr.addStretch()
        lay.addLayout(sr)

        # Scrollable table
        scroll = QScrollArea(); scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("QScrollArea { background:transparent; border:none; }")
        table_w = QWidget()
        table_w.setStyleSheet("background:transparent;")
        tbl = QGridLayout(table_w)
        tbl.setHorizontalSpacing(6); tbl.setVerticalSpacing(3)
        tbl.setColumnStretch(7, 1)

        # Header row
        for col, (txt, w_px, align) in enumerate([
            ("Attacking Type", 120, Qt.AlignLeft),
            ("4×", 36, Qt.AlignCenter), ("2×", 36, Qt.AlignCenter),
            ("½×", 36, Qt.AlignCenter), ("¼×", 36, Qt.AlignCenter),
            ("Imm", 36, Qt.AlignCenter),
            ("Net Danger ←→ Resist", 160, Qt.AlignLeft),
        ]):
            h = QLabel(txt)
            h.setFixedWidth(w_px)
            h.setAlignment(align)
            h.setStyleSheet("font-size:10px; font-weight:bold; color:#6c7086;")
            tbl.addWidget(h, 0, col)

        # Data rows — sorted worst danger first, skip all-neutral rows
        sorted_types = sorted(ALL_TYPES, key=_danger, reverse=True)

        def _multiplied_names(atk, mult_key):
            """Return comma-separated species names taking mult_key against atk."""
            names = []
            for mon in self._party:
                base = get_dex_base_stats(mon.species)
                if not base: continue
                t1 = base.get('type1',''); t2 = base.get('type2','')
                ab = mon.ability or ((base.get('abilities',()) or ('',))[0])
                m  = _mon_type_effectiveness(atk, t1, t2, ab)
                threshold = {'4x':4,'2x':2,'half':0.5,'quarter':0.25,'immune':0}[mult_key]
                if abs(m - threshold) < 0.01:
                    names.append(mon.species.replace('SPECIES_','').replace('_',' ').title())
            return ', '.join(names)

        for row, atk in enumerate(sorted_types, 1):
            d   = profile[atk]
            net = _danger(atk)

            tbl.addWidget(self._type_badge(atk), row, 0)

            for col, (key, fg, bg) in enumerate([
                ('4x',      '#f38ba8', '#3d1a1e'),
                ('2x',      '#fab387', '#3d2a1a'),
                ('half',    '#a6e3a1', '#1a3d2a'),
                ('quarter', '#89dceb', '#1a2e3d'),
                ('immune',  '#cba6f7', '#2e1a3d'),
            ], 1):
                cnt = d[key]
                if cnt:
                    lbl = QLabel(str(cnt))
                    lbl.setAlignment(Qt.AlignCenter)
                    lbl.setFixedSize(32, 20)
                    lbl.setStyleSheet(
                        f"background:{bg}; color:{fg}; border:1px solid {fg}55; "
                        f"border-radius:3px; font-size:11px; font-weight:bold;")
                    lbl.setToolTip(_multiplied_names(atk, key))
                    tbl.addWidget(lbl, row, col)
                else:
                    lbl = QLabel("—")
                    lbl.setAlignment(Qt.AlignCenter)
                    lbl.setStyleSheet("color:#313244; font-size:11px;")
                    tbl.addWidget(lbl, row, col)

            # Net bar
            bar_host = QWidget(); bar_host.setFixedHeight(20)
            bh = QHBoxLayout(bar_host); bh.setContentsMargins(0,4,0,4); bh.setSpacing(2)
            if net > 0:
                c   = "#f38ba8" if net >= 4 else "#fab387"
                bar = QWidget()
                bar.setFixedHeight(12)
                bar.setFixedWidth(min(int(net / (n * 4) * 120), 120))
                bar.setStyleSheet(f"background:{c}; border-radius:3px;")
                bh.addWidget(bar)
                bh.addWidget(QLabel(f"  ⚠ {net:+.0f}") if net >= 4
                             else QLabel(f"  {net:+.0f}"))
            elif net < 0:
                bar = QWidget()
                bar.setFixedHeight(12)
                bar.setFixedWidth(min(int(abs(net) / (n * 4) * 120), 120))
                bar.setStyleSheet("background:#a6e3a1; border-radius:3px;")
                bh.addWidget(bar)
            bh.addStretch()
            tbl.addWidget(bar_host, row, 6)

        scroll.setWidget(table_w)
        lay.addWidget(scroll, 1)

        # Type spread
        lay.addWidget(_sep())
        spread_hdr = QLabel("Team Type Spread")
        spread_hdr.setStyleSheet("font-size:12px; font-weight:bold; color:#89b4fa;")
        lay.addWidget(spread_hdr)
        spread = {}
        for mon in self._party:
            base = get_dex_base_stats(mon.species)
            if not base: continue
            for t in (base.get('type1',''), base.get('type2','')):
                if t: spread[t] = spread.get(t, 0) + 1
        sr2 = QHBoxLayout(); sr2.setSpacing(4)
        for t, cnt in sorted(spread.items(), key=lambda x: -x[1]):
            tc   = TYPE_HEX.get(t, "#585b70")
            pill = QLabel(f" {t.title()} ×{cnt} ")
            pill.setStyleSheet(
                f"background:{tc}; color:#ffffff; border-radius:4px; "
                f"font-size:11px; font-weight:bold; padding:2px 4px;")
            sr2.addWidget(pill)
        sr2.addStretch()
        lay.addLayout(sr2)

        # Ability modifiers
        ab_notes = []
        for mon in self._party:
            if not mon.ability: continue
            ab_key = mon.ability.lower()
            if ab_key in _ABILITY_IMMUNITIES:
                sp = mon.species.replace('SPECIES_','').replace('_',' ').title()
                for t, m in _ABILITY_IMMUNITIES[ab_key].items():
                    desc = "immune to" if m == 0 else "½× vs"
                    ab_notes.append(f"  •  {sp}  ({mon.ability})  {desc}  {t.title()}")
        if ab_notes:
            lay.addWidget(_sep())
            ab_hdr = QLabel("Ability Modifiers")
            ab_hdr.setStyleSheet("font-size:12px; font-weight:bold; color:#89b4fa;")
            lay.addWidget(ab_hdr)
            for note in ab_notes:
                n = QLabel(note); n.setStyleSheet("font-size:11px; color:#a6adc8;")
                lay.addWidget(n)

        return w

    def _build_offensive_tab(self):
        w   = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(14, 12, 14, 8)
        lay.setSpacing(10)

        coverage, holes, per_mon = self._calc_offensive()
        covered  = [t for t in ALL_TYPES if t not in holes]
        n_cover  = len(covered)

        # Summary
        sr = QHBoxLayout(); sr.setSpacing(8)
        pct = int(n_cover / len(ALL_TYPES) * 100)
        sr.addWidget(self._summary_pill(
            f"{n_cover}/{len(ALL_TYPES)} types covered SE", "#a6e3a1"))
        if holes:
            sr.addWidget(self._summary_pill(
                f"{len(holes)} coverage holes", "#f38ba8"))
        sr.addStretch()
        lay.addLayout(sr)

        # ── Coverage grid — all 18 types ─────────────────────────────────────
        grid_hdr = QLabel("Super-Effective Coverage  (can the team land a SE hit on each type?)")
        grid_hdr.setStyleSheet("font-size:12px; font-weight:bold; color:#89b4fa;")
        lay.addWidget(grid_hdr)

        grid_w = QWidget()
        grid_l = QGridLayout(grid_w)
        grid_l.setHorizontalSpacing(6); grid_l.setVerticalSpacing(5)
        grid_w.setStyleSheet("background:transparent;")

        COLS = 6
        for idx, t in enumerate(ALL_TYPES):
            covered_t = t in coverage and bool(coverage[t])
            tc = TYPE_HEX.get(t, "#585b70")
            badge = QLabel(t.title())
            badge.setFixedSize(88, 22)
            badge.setAlignment(Qt.AlignCenter)
            if covered_t:
                badge.setStyleSheet(
                    f"background:{tc}; color:#ffffff; border-radius:4px; "
                    f"font-size:11px; font-weight:bold;")
                # Build tooltip: who covers it?
                sources = coverage[t][:4]
                tip_lines = [f"{mn} via {src} ({at.title()})" for mn, src, at in sources]
                if len(coverage[t]) > 4:
                    tip_lines.append(f"…and {len(coverage[t])-4} more")
                badge.setToolTip("\n".join(tip_lines))
            else:
                badge.setStyleSheet(
                    f"background:#1e1e2e; color:#585b70; border:1px solid #313244; "
                    f"border-radius:4px; font-size:11px; font-weight:bold;")
                badge.setToolTip("No SE coverage — coverage hole!")
            grid_l.addWidget(badge, idx // COLS, idx % COLS)

        lay.addWidget(grid_w)

        # ── Coverage holes ────────────────────────────────────────────────────
        if holes:
            lay.addWidget(_sep())
            holes_hdr = QLabel(f"Coverage Holes  ({len(holes)} types with no SE attack)")
            holes_hdr.setStyleSheet("font-size:12px; font-weight:bold; color:#f38ba8;")
            lay.addWidget(holes_hdr)
            hr = QHBoxLayout(); hr.setSpacing(4)
            for t in holes:
                hr.addWidget(self._type_badge(t))
            hr.addStretch()
            lay.addLayout(hr)

        # ── Per-mon coverage ──────────────────────────────────────────────────
        lay.addWidget(_sep())
        pm_hdr = QLabel("Per-Pokémon Attacking Coverage")
        pm_hdr.setStyleSheet("font-size:12px; font-weight:bold; color:#89b4fa;")
        lay.addWidget(pm_hdr)

        scroll = QScrollArea(); scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("QScrollArea { background:transparent; border:none; }")
        pm_w = QWidget(); pm_w.setStyleSheet("background:transparent;")
        pm_lay = QVBoxLayout(pm_w); pm_lay.setSpacing(4); pm_lay.setContentsMargins(0,0,0,0)

        for mon in self._party:
            mon_display = mon.species.replace('SPECIES_','').replace('_',' ').title()
            data = per_mon.get(mon_display, {})
            atk_types   = data.get('atk_types', set())
            def_covered = data.get('def_covered', set())

            row_w = QWidget()
            row_w.setStyleSheet(
                "background:#1e1e2e; border:1px solid #313244; border-radius:6px;")
            row_l = QHBoxLayout(row_w)
            row_l.setContentsMargins(10, 5, 10, 5); row_l.setSpacing(8)

            name_lbl = QLabel(mon_display)
            name_lbl.setFixedWidth(130)
            name_lbl.setStyleSheet("color:#cdd6f4; font-size:12px; font-weight:bold;")
            row_l.addWidget(name_lbl)

            # Attacking types available
            atk_lbl = QLabel("Atk types:")
            atk_lbl.setStyleSheet("color:#6c7086; font-size:10px;")
            row_l.addWidget(atk_lbl)
            for t in sorted(atk_types):
                row_l.addWidget(self._type_badge(t, height=18, pad="0 4px"))

            row_l.addSpacing(12)
            cov_lbl = QLabel(f"→  {len(def_covered)}/{len(ALL_TYPES)} SE")
            cov_lbl.setStyleSheet(
                f"color:{'#a6e3a1' if len(def_covered) >= 6 else '#f9e2af' if len(def_covered) >= 3 else '#f38ba8'}; "
                f"font-size:11px; font-weight:bold;")
            row_l.addWidget(cov_lbl)
            row_l.addStretch()
            pm_lay.addWidget(row_w)

        pm_lay.addStretch()
        scroll.setWidget(pm_w)
        lay.addWidget(scroll, 1)

        return w

    # ── Main UI ───────────────────────────────────────────────────────────────

    def _build_ui(self):
        root = self._root_layout
        root.setSpacing(8)

        if not self._party:
            root.addWidget(QLabel("No Pokémon in party yet."))
            btn = QPushButton("Close"); btn.setFixedWidth(80)
            btn.clicked.connect(self.accept)
            root.addWidget(btn)
            return

        tabs = QTabWidget()
        tabs.setStyleSheet(
            "QTabWidget::pane { border:1px solid #313244; background:#1e1e2e; margin-top:-1px; }"
            "QTabBar::tab { background:#181825; color:#a6adc8; padding:7px 20px; "
            "  border:1px solid #313244; border-bottom:none; border-radius:6px 6px 0 0; "
            "  margin-right:2px; font-size:12px; font-weight:bold; }"
            "QTabBar::tab:selected { background:#1e1e2e; color:#cdd6f4; "
            "  border-bottom:1px solid #1e1e2e; }"
            "QTabBar::tab:hover:!selected { background:#252536; }"
        )
        tabs.addTab(self._build_defensive_tab(), "Defensive")
        tabs.addTab(self._build_offensive_tab(), "Offensive")
        root.addWidget(tabs, 1)

        close_btn = QPushButton("Close"); close_btn.setFixedWidth(90)
        close_btn.clicked.connect(self.accept)
        cr = QHBoxLayout(); cr.addStretch(); cr.addWidget(close_btn)
        root.addLayout(cr)


# ══════════════════════════════════════════════════════════════════════════════
# PARTY CARDS WIDGET  — horizontal row of 6 MonSlotCard widgets
# ══════════════════════════════════════════════════════════════════════════════
class PartyCardsWidget(QWidget):
    """Horizontal party editor: 6 MonSlotCard widgets inside a QScrollArea."""
    party_changed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._trainer = None
        self._mons    = [None] * 6
        self._cards   = []
        self._setup_ui()

    def _setup_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setMinimumHeight(420)

        cards_w = QWidget()
        cards_lay = QHBoxLayout(cards_w)
        cards_lay.setContentsMargins(6, 6, 6, 6)
        cards_lay.setSpacing(8)

        for i in range(6):
            card = MonSlotCard(i)
            card.slot_double_clicked.connect(self._on_slot_double_clicked)
            card.slot_cleared.connect(self._on_slot_cleared)
            cards_lay.addWidget(card)
            self._cards.append(card)
        cards_lay.addStretch()

        scroll.setWidget(cards_w)
        outer.addWidget(scroll)

    def _on_slot_double_clicked(self, slot_idx):
        mon = self._mons[slot_idx]
        if mon is None:
            mon = TrainerMon()
            self._mons[slot_idx] = mon
        def _callback(updated_mon):
            if updated_mon.species:
                self._mons[slot_idx] = updated_mon
            else:
                self._mons[slot_idx] = None
            self._cards[slot_idx].load_mon(self._mons[slot_idx])
            self.party_changed.emit()
        dlg = MonDetailDialog(mon, slot_idx, _callback, self)
        dlg.exec_()

    def _on_slot_cleared(self, slot_idx):
        self._mons[slot_idx] = None
        self._cards[slot_idx].load_mon(None)
        self.party_changed.emit()

    def load_trainer(self, trainer):
        self._trainer = trainer
        self._mons = list(trainer.party) + [None] * (6 - len(trainer.party))
        self._mons = self._mons[:6]
        for i, card in enumerate(self._cards):
            card.load_mon(self._mons[i])

    def get_party(self):
        return [m for m in self._mons if m is not None and m.species]


# ══════════════════════════════════════════════════════════════════════════════
# AI FLAGS WIDGET
# ══════════════════════════════════════════════════════════════════════════════
class AIFlagsWidget(QGroupBox):
    """AI flags editor with always-visible profile buttons and a collapsible individual-flags grid."""

    _PROFILE_NAMES = ("Basic Trainer", "Smart Trainer", "Prediction")

    def __init__(self, parent=None):
        super().__init__("AI Flags", parent)
        self._chks            = {}
        self._profile_buttons = []   # list of (QPushButton, preset_name)
        self._flags_visible   = False
        self._build_ui()

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(6, 8, 6, 6); outer.setSpacing(4)

        # ── Always-visible row: profile buttons + clear ───────────────────────
        always_row = QHBoxLayout(); always_row.setSpacing(4)

        for name in self._PROFILE_NAMES:
            btn = QPushButton(name)
            btn.setCheckable(True)
            btn.setFixedHeight(28)
            btn.setStyleSheet(
                "QPushButton { font-size:11px; padding:4px 10px; background:#252536; "
                "  border:1px solid #45475a; border-radius:4px; color:#a6adc8; }"
                "QPushButton:checked { background:#1a2e1a; color:#a6e3a1; "
                "  border-color:#a6e3a1; }"
                "QPushButton:hover { border-color:#89b4fa; }"
            )
            btn.clicked.connect(lambda checked, n=name: self._on_profile_clicked(n, checked))
            always_row.addWidget(btn)
            self._profile_buttons.append((btn, name))

        sep_v = QFrame(); sep_v.setFrameShape(QFrame.VLine)
        sep_v.setStyleSheet("color:#45475a; max-width:1px;")
        always_row.addWidget(sep_v)

        clear_btn = QPushButton("Clear")
        clear_btn.setFixedHeight(28)
        clear_btn.setStyleSheet(
            "QPushButton { font-size:11px; padding:4px 10px; background:#252536; "
            "  border:1px solid #45475a; border-radius:4px; color:#f38ba8; }"
            "QPushButton:hover { background:#2e1a1a; border-color:#f38ba8; }"
        )
        clear_btn.clicked.connect(self._clear_all)
        always_row.addWidget(clear_btn)
        always_row.addStretch()

        # Toggle for individual flags
        self._toggle_btn = QPushButton("▶  Individual Flags")
        self._toggle_btn.setFixedHeight(28)
        self._toggle_btn.setStyleSheet(
            "QPushButton { font-size:10px; padding:4px 8px; background:transparent; "
            "  border:none; color:#6c7086; text-align:right; }"
            "QPushButton:hover { color:#a6adc8; }"
        )
        self._toggle_btn.clicked.connect(self._toggle_flags)
        always_row.addWidget(self._toggle_btn)

        outer.addLayout(always_row)

        # ── Collapsible individual-flags grid ─────────────────────────────────
        self._flags_widget = QWidget()
        self._flags_widget.setVisible(False)
        grid_outer = QVBoxLayout(self._flags_widget)
        grid_outer.setContentsMargins(0, 4, 0, 2); grid_outer.setSpacing(2)

        sep_h = QFrame(); sep_h.setFrameShape(QFrame.HLine)
        sep_h.setStyleSheet("background:#313244; max-height:1px; border:none;")
        grid_outer.addWidget(sep_h)

        grid = QGridLayout()
        grid.setHorizontalSpacing(2); grid.setVerticalSpacing(1)
        grid.setContentsMargins(0, 2, 0, 0)
        for idx, (display, _const) in enumerate(AI_FLAGS_ORDERED):
            chk = QCheckBox(display)
            chk.setStyleSheet("font-size:9px; spacing:2px;")
            chk.stateChanged.connect(
                lambda state, d=display: self._on_individual_flag_toggled(d, state))
            grid.addWidget(chk, idx // 5, idx % 5)
            self._chks[display] = chk
        grid_outer.addLayout(grid)
        outer.addWidget(self._flags_widget)

    # ── Toggle collapsed/expanded ─────────────────────────────────────────────
    def _toggle_flags(self):
        self._flags_visible = not self._flags_visible
        self._flags_widget.setVisible(self._flags_visible)
        self._toggle_btn.setText(
            "▼  Individual Flags" if self._flags_visible else "▶  Individual Flags"
        )

    # ── Profile button logic ──────────────────────────────────────────────────
    def _on_profile_clicked(self, name, checked):
        """Clicking a profile button applies or removes that profile's flags."""
        # Block signals while we manipulate checkboxes
        for chk in self._chks.values(): chk.blockSignals(True)

        if checked:
            # Deselect all other profile buttons visually
            for btn, pname in self._profile_buttons:
                if pname != name:
                    btn.blockSignals(True)
                    btn.setChecked(False)
                    btn.blockSignals(False)
            # Remove flags that belong to OTHER profiles (keep extras the user added)
            other_preset_flags = set()
            for pname in self._PROFILE_NAMES:
                if pname != name:
                    other_preset_flags.update(AI_PRESETS.get(pname, []))
            for flag, chk in self._chks.items():
                if flag in other_preset_flags:
                    chk.setChecked(False)
            # Apply this profile's flags
            for flag in AI_PRESETS.get(name, []):
                if flag in self._chks:
                    self._chks[flag].setChecked(True)
        else:
            # Unchecking: remove only the flags that belong to this profile
            for flag in AI_PRESETS.get(name, []):
                if flag in self._chks:
                    self._chks[flag].setChecked(False)

        for chk in self._chks.values(): chk.blockSignals(False)
        # Don't call _update_profile_highlights here — button states already set

    # Exclusive flag groups — enabling a flag from one group clears the other group
    _EXCLUSIVE_GROUPS = [
        set(AI_PRESETS["Prediction"]),
        set(AI_PRESETS["Smart Trainer"]),   # superset of Basic Trainer
    ]

    def _on_individual_flag_toggled(self, display_name, state):
        """Enforce mutual exclusivity: flags from Prediction vs Basic/Smart cannot coexist."""
        if state == Qt.Checked:
            # Determine which exclusive group this flag belongs to
            my_group  = next((g for g in self._EXCLUSIVE_GROUPS if display_name in g), None)
            if my_group is not None:
                # Uncheck all flags from every OTHER exclusive group
                for other_group in self._EXCLUSIVE_GROUPS:
                    if other_group is not my_group:
                        for flag in other_group:
                            if flag in self._chks:
                                self._chks[flag].blockSignals(True)
                                self._chks[flag].setChecked(False)
                                self._chks[flag].blockSignals(False)
        self._update_profile_highlights()

    def _update_profile_highlights(self):
        """Called when individual checkboxes change. Find best matching profile (most specific
        subset of active flags) and show only that one as selected."""
        active = set(d for d, chk in self._chks.items() if chk.isChecked())

        # Find the most specific profile whose entire flag set is a subset of active
        best_name  = None
        best_count = 0
        for _btn, pname in self._profile_buttons:
            pflags = set(AI_PRESETS.get(pname, []))
            if pflags and pflags.issubset(active) and len(pflags) > best_count:
                best_count = len(pflags)
                best_name  = pname

        for btn, pname in self._profile_buttons:
            btn.blockSignals(True)
            btn.setChecked(pname == best_name)
            btn.blockSignals(False)

    def _clear_all(self):
        for chk in self._chks.values(): chk.setChecked(False)
        for btn, _ in self._profile_buttons:
            btn.blockSignals(True); btn.setChecked(False); btn.blockSignals(False)

    # ── Data API ──────────────────────────────────────────────────────────────
    def get_flags(self):
        """Return list of display names for checked flags (or preset name if exactly matches)."""
        active = [d for d, chk in self._chks.items() if chk.isChecked()]
        for preset_name, preset_flags in AI_PRESETS.items():
            if set(active) == set(preset_flags):
                return [preset_name]
        return active

    def set_flags(self, flags_list):
        """Load flags from .party file (e.g. ['Basic Trainer'] or raw flag display names)."""
        expanded = []
        for f in flags_list:
            if f in AI_PRESETS:
                expanded.extend(AI_PRESETS[f])
            elif f in AI_FLAG_BY_DISPLAY:
                expanded.append(f)

        for chk in self._chks.values():
            chk.blockSignals(True); chk.setChecked(False); chk.blockSignals(False)
        for flag in expanded:
            if flag in self._chks:
                self._chks[flag].blockSignals(True)
                self._chks[flag].setChecked(True)
                self._chks[flag].blockSignals(False)

        # Ensure flags panel starts collapsed regardless of flags loaded
        self._flags_visible = False
        self._flags_widget.setVisible(False)
        self._toggle_btn.setText("▶  Individual Flags")

        self._update_profile_highlights()


# ══════════════════════════════════════════════════════════════════════════════
# TRAINER INFO CARD
# ══════════════════════════════════════════════════════════════════════════════
class TrainerInfoCard(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._classes = load_trainer_classes()
        self._pics    = load_trainer_pics()
        self._items   = load_items()
        self._item_btns = []
        self._build_ui()

    def _build_ui(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(8, 6, 8, 6); lay.setSpacing(4)

        # Row 1: key label + name + class + pic
        row1 = QHBoxLayout(); row1.setSpacing(8)
        self._key_lbl = QLabel("")
        self._key_lbl.setStyleSheet("color:#585b70;font-size:11px;")
        row1.addWidget(self._key_lbl)
        row1.addWidget(QLabel("Name:"))
        self._name_edit = QLineEdit(); self._name_edit.setFixedWidth(120)
        row1.addWidget(self._name_edit)
        row1.addWidget(QLabel("Class:"))
        self._class_cb = QComboBox()
        self._class_cb.addItems(sorted(self._classes))
        self._class_cb.setFixedWidth(180)
        self._class_cb.setMaxVisibleItems(20)
        row1.addWidget(self._class_cb)
        row1.addWidget(QLabel("Pic:"))
        self._pic_btn = QPushButton("")
        self._pic_btn.setFixedSize(58, 58)
        self._pic_btn.setObjectName("slot")
        self._pic_btn.clicked.connect(self._open_pic_selector)
        row1.addWidget(self._pic_btn)
        row1.addStretch()
        self._analysis_btn = QPushButton("⚔ Analysis")
        self._analysis_btn.setFixedHeight(34)
        self._analysis_btn.setFixedWidth(100)
        self._analysis_btn.setToolTip("Show team type weakness/resistance analysis")
        self._analysis_btn.clicked.connect(self._open_type_analysis)
        row1.addWidget(self._analysis_btn)
        lay.addLayout(row1)

        # Row 2: gender + music + battle type
        row2 = QHBoxLayout(); row2.setSpacing(10)
        row2.addWidget(QLabel("Gender:"))
        self._gender_cb = QComboBox(); self._gender_cb.addItems(GENDER_OPTIONS)
        self._gender_cb.setFixedWidth(80)
        row2.addWidget(self._gender_cb)
        row2.addWidget(QLabel("Music:"))
        self._music_cb = QComboBox(); self._music_cb.addItems(MUSIC_OPTIONS)
        self._music_cb.setFixedWidth(120)
        row2.addWidget(self._music_cb)
        row2.addWidget(QLabel("Battle:"))
        self._battle_cb = QComboBox(); self._battle_cb.addItems(BATTLE_OPTIONS)
        self._battle_cb.setFixedWidth(90)
        row2.addWidget(self._battle_cb)
        mugshot_lbl = QLabel("VS Color:")
        mugshot_lbl.setToolTip(
            "Mugshot color — the full-screen flash color shown on the VS battle\n"
            "intro screen when this trainer battle starts.\n"
            "Leave blank for no special intro flash."
        )
        row2.addWidget(mugshot_lbl)
        self._mugshot_cb = QComboBox(); self._mugshot_cb.addItems(MUGSHOT_OPTIONS)
        self._mugshot_cb.setFixedWidth(90)
        self._mugshot_cb.setToolTip(
            "Mugshot color — the full-screen flash color shown on the VS battle\n"
            "intro screen when this trainer battle starts.\n"
            "Leave blank for no special intro flash."
        )
        row2.addWidget(self._mugshot_cb)
        row2.addStretch()
        lay.addLayout(row2)

        # Row 3: trainer items (4 slots)
        row3 = QHBoxLayout(); row3.setSpacing(8)
        row3.addWidget(QLabel("Items:"))
        self._item_btns = []
        for i in range(4):
            btn = QPushButton("—")
            btn.setFixedSize(44, 44)
            btn.setObjectName("slot")
            btn.setToolTip(f"Trainer item slot {i+1}\nRight-click to clear")
            btn.clicked.connect(lambda _, idx=i: self._open_item_selector(idx))
            btn.setContextMenuPolicy(Qt.CustomContextMenu)
            btn.customContextMenuRequested.connect(
                lambda pos, idx=i, b=btn: self._clear_item(idx))
            row3.addWidget(btn)
            self._item_btns.append(btn)
        row3.addStretch()
        lay.addLayout(row3)

        # AI flags
        self._ai_widget = AIFlagsWidget()
        lay.addWidget(self._ai_widget)

    def _open_pic_selector(self):
        current = self._pic_btn.toolTip()
        dlg = TrainerPicSelectorDialog(current=current, parent=self)
        if dlg.exec_() == QDialog.Accepted and dlg.selected:
            self._set_pic(dlg.selected)

    def _set_pic(self, display):
        self._pic_btn.setToolTip(display)
        path = next((p for d,p in self._pics if d.lower()==display.lower()), "")
        if path and os.path.isfile(path):
            pix = QPixmap(path).scaled(52,52,Qt.KeepAspectRatio,Qt.SmoothTransformation)
            self._pic_btn.setIcon(QIcon(pix)); self._pic_btn.setIconSize(QSize(52,52))
            self._pic_btn.setText("")
        else:
            self._pic_btn.setIcon(QIcon()); self._pic_btn.setText(display[:8])

    def _open_item_selector(self, idx):
        current = self._item_btns[idx].toolTip()
        dlg = ItemSelectorDialog(current=current, parent=self)
        if dlg.exec_() == QDialog.Accepted:
            self._set_item_btn(idx, dlg.selected)

    def _set_item_btn(self, idx, item_key):
        btn = self._item_btns[idx]
        btn.setToolTip(item_key)
        if item_key:
            icon_path = next((p for k,d,p in self._items if k==item_key), "")
            pix = _item_pixmap(icon_path, 36)
            if pix:
                btn.setIcon(QIcon(pix)); btn.setIconSize(QSize(36,36)); btn.setText("")
            else:
                btn.setIcon(QIcon()); btn.setText(item_key[5:9] if item_key.startswith('ITEM_') else item_key[:4])
        else:
            btn.setIcon(QIcon()); btn.setText("—")

    def _clear_item(self, idx):
        self._set_item_btn(idx, "")

    def load_trainer(self, t: Trainer):
        self._key_lbl.setText(t.key)
        self._name_edit.setText(t.name)
        ci = self._class_cb.findText(t.trainer_class, Qt.MatchFixedString | Qt.MatchCaseSensitive)
        if ci >= 0:
            self._class_cb.setCurrentIndex(ci)
        elif t.trainer_class:
            self._class_cb.insertItem(0, t.trainer_class)
            self._class_cb.setCurrentIndex(0)
        self._set_pic(t.pic)
        gi = GENDER_OPTIONS.index(t.gender) if t.gender in GENDER_OPTIONS else 0
        self._gender_cb.setCurrentIndex(gi)
        mi = self._music_cb.findText(t.music)
        if mi >= 0: self._music_cb.setCurrentIndex(mi)
        bi = BATTLE_OPTIONS.index("Doubles" if t.double_battle else "Singles")
        self._battle_cb.setCurrentIndex(bi)
        mgi = MUGSHOT_OPTIONS.index(t.mugshot) if t.mugshot in MUGSHOT_OPTIONS else 0
        self._mugshot_cb.setCurrentIndex(mgi)
        # Items
        items_padded = (t.items + ["", "", "", ""])[:4]
        for i, it in enumerate(items_padded):
            self._set_item_btn(i, it)
        # AI
        self._ai_widget.set_flags(t.ai_flags)

    def save_to_trainer(self, t: Trainer):
        t.name          = self._name_edit.text().strip()
        t.trainer_class = self._class_cb.currentText()
        t.pic           = self._pic_btn.toolTip()
        t.gender        = self._gender_cb.currentText()
        t.music         = self._music_cb.currentText()
        t.double_battle = self._battle_cb.currentText() == "Doubles"
        t.mugshot       = self._mugshot_cb.currentText()
        t.items         = [btn.toolTip() for btn in self._item_btns if btn.toolTip()]
        t.ai_flags      = self._ai_widget.get_flags()

    def _open_type_analysis(self):
        """Walk up to TrainerEditorPanel to get the current party and open analysis dialog."""
        party = []
        p = self.parent()
        while p:
            if hasattr(p, '_party_panel'):
                party = p._party_panel.get_party()
                break
            p = p.parent()
        dlg = TeamTypeAnalysisDialog(party, parent=self)
        dlg.exec_()


# ══════════════════════════════════════════════════════════════════════════════
# TRAINER EDITOR PANEL  (right side of main splitter)
# ══════════════════════════════════════════════════════════════════════════════
class TrainerEditorPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._trainer = None
        self._build_ui()

    def _build_ui(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(6, 6, 6, 6); lay.setSpacing(6)

        self._info_card = TrainerInfoCard()
        lay.addWidget(self._info_card)
        lay.addWidget(_sep())

        party_lbl = _heading("PARTY")
        lay.addWidget(party_lbl)

        # ── Team stats bar ────────────────────────────────────────────────────
        self._stats_bar = QWidget()
        sb_lay = QHBoxLayout(self._stats_bar)
        sb_lay.setContentsMargins(4, 2, 4, 2); sb_lay.setSpacing(10)
        self._stats_bar.setStyleSheet("background:#181825; border-radius:4px;")

        sb_lay.addWidget(QLabel("Team stats:"))

        stat_colors_bar = ["#f38ba8","#fab387","#f9e2af","#a6e3a1","#89dceb","#89b4fa"]
        stat_names_bar  = ["HP","Atk","Def","SpA","SpD","Spe"]
        self._team_stat_lbls = {}
        for sname, color in zip(stat_names_bar, stat_colors_bar):
            name_lbl = QLabel(sname + ":")
            name_lbl.setStyleSheet(f"color:{color}; font-size:11px; font-weight:bold;")
            sb_lay.addWidget(name_lbl)
            val_lbl = QLabel("—")
            val_lbl.setStyleSheet(f"color:{color}; font-size:11px;")
            sb_lay.addWidget(val_lbl)
            self._team_stat_lbls[sname] = val_lbl

        sb_lay.addWidget(QLabel("Total:"))
        self._team_total_lbl = QLabel("—")
        self._team_total_lbl.setStyleSheet("color:#89b4fa; font-size:11px; font-weight:bold;")
        sb_lay.addWidget(self._team_total_lbl)
        sb_lay.addStretch()
        lay.addWidget(self._stats_bar)

        # ── Party cards ───────────────────────────────────────────────────────
        self._party_panel = PartyCardsWidget()
        self._party_panel.party_changed.connect(self._update_team_stats)
        lay.addWidget(self._party_panel)

        footer = QHBoxLayout()
        self._save_btn = QPushButton("Save Trainer to File")
        self._save_btn.setObjectName("accent")
        self._save_btn.setFixedHeight(36)
        self._save_btn.clicked.connect(self._save)
        footer.addStretch(); footer.addWidget(self._save_btn)
        lay.addLayout(footer)

    def _update_team_stats(self):
        """Sum ingame stats for all party members and display in the stats bar."""
        party = self._party_panel.get_party()
        stat_keys  = ('hp','atk','def_','spa','spd','spe')
        stat_names = ('HP','Atk','Def','SpA','SpD','Spe')
        totals = {k: 0 for k in stat_keys}
        levels  = []
        for mon in party:
            if not mon or not mon.species:
                continue
            levels.append(mon.level)
            effective = _get_mega_species(mon.species, mon.held_item) or mon.species
            calc = calc_all_ingame_stats(effective, mon.ivs, mon.evs, mon.level, mon.nature)
            for k in stat_keys:
                totals[k] += calc.get(k, 0)
        grand_total = sum(totals.values())
        avg_lv = int(sum(levels) / len(levels)) if levels else 0
        for sn, sk in zip(stat_names, stat_keys):
            lbl = self._team_stat_lbls.get(sn)
            if lbl:
                lbl.setText(str(totals[sk]) if totals[sk] else "—")
        self._team_total_lbl.setText(str(grand_total) if grand_total else "—")

    def _on_party_changed(self):
        self._update_team_stats()

    def load_trainer(self, t: Trainer):
        self._trainer = t
        self._info_card.load_trainer(t)
        self._party_panel.load_trainer(t)
        self._update_team_stats()

    def _save(self):
        if not self._trainer: return
        self._info_card.save_to_trainer(self._trainer)
        self._trainer.party = self._party_panel.get_party()
        # Propagate save to main window
        parent = self.parent()
        while parent and not hasattr(parent, '_save_party_file'):
            parent = parent.parent()
        if parent: parent._save_party_file()


# ══════════════════════════════════════════════════════════════════════════════
# TRAINER LIST PANEL  (left side of main splitter)
# ══════════════════════════════════════════════════════════════════════════════
class TrainerListPanel(QWidget):
    trainer_selected = pyqtSignal(int)  # index into trainer list

    def __init__(self, trainers, parent=None):
        super().__init__(parent)
        self._trainers       = trainers
        self._filtered       = []
        self._loc_map        = build_trainer_location_map()
        self._starter_filter = None   # None=all, 'TREECKO'/'TORCHIC'/'MUDKIP'
        self._setup_ui()
        self._populate()

    def _setup_ui(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(6, 6, 6, 4)
        lay.setSpacing(6)

        # Title
        title = QLabel("Party God"); title.setObjectName("title")
        lay.addWidget(title)

        # ── Rival / Starter filter row ────────────────────────────────────────
        starter_lbl = QLabel("Starter:")
        starter_lbl.setStyleSheet("color:#6c7086; font-size:11px;")
        starter_row = QHBoxLayout(); starter_row.setSpacing(4)
        starter_row.addWidget(starter_lbl)

        self._starter_btns = {}
        starters = [
            ('TREECKO', '🌿 Grass', '#78c850'),
            ('TORCHIC', '🔥 Fire',  '#f08030'),
            ('MUDKIP',  '💧 Water', '#6890f0'),
        ]
        for key, label, color in starters:
            btn = QPushButton(label)
            btn.setCheckable(True)
            btn.setFixedHeight(22)
            btn.setStyleSheet(
                f"QPushButton {{ font-size:10px; padding:2px 6px; "
                f"border:1px solid #45475a; border-radius:4px; color:#6c7086; }}"
                f"QPushButton:checked {{ background:{color}44; color:{color}; "
                f"border-color:{color}; font-weight:bold; }}"
                f"QPushButton:hover {{ border-color:{color}; }}"
            )
            btn.toggled.connect(lambda chk, k=key: self._on_starter_toggled(k, chk))
            self._starter_btns[key] = btn
            starter_row.addWidget(btn)
        starter_row.addStretch()
        lay.addLayout(starter_row)

        # Search
        self.search = QLineEdit()
        self.search.setPlaceholderText("Search trainers...")
        self.search.textChanged.connect(self._populate)
        lay.addWidget(self.search)

        # Tree widget
        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        self.tree.setAlternatingRowColors(True)
        self.tree.setStyleSheet(
            "QTreeWidget { background:#181825; border:none; color:#cdd6f4; "
            "alternate-background-color:#1e1e2e; }"
            "QTreeWidget::item { padding:3px 6px; }"
            "QTreeWidget::item:selected { background:#313244; }"
            "QTreeWidget::item:hover { background:#252536; }"
            "QTreeWidget::branch { background:#181825; }"
        )
        self.tree.itemClicked.connect(self._on_item_clicked)
        lay.addWidget(self.tree)

        # Add / Duplicate / Delete
        btn_row = QHBoxLayout(); btn_row.setSpacing(4)
        self.add_btn  = QPushButton("+ Add")
        self.dup_btn  = QPushButton("Dup")
        self.del_btn  = QPushButton("Del")
        self.del_btn.setObjectName("danger")
        for b in (self.add_btn, self.dup_btn, self.del_btn):
            b.setFixedHeight(28)
            b.setStyleSheet("font-size:11px; padding:2px 8px;")
            btn_row.addWidget(b)
        lay.addLayout(btn_row)

        self.add_btn.clicked.connect(self._add_trainer)
        self.dup_btn.clicked.connect(self._duplicate_trainer)
        self.del_btn.clicked.connect(self._delete_trainer)

    def _on_starter_toggled(self, key, checked):
        if checked:
            # Uncheck other starter buttons
            for k, btn in self._starter_btns.items():
                if k != key and btn.isChecked():
                    btn.blockSignals(True)
                    btn.setChecked(False)
                    btn.blockSignals(False)
            self._starter_filter = key
        else:
            self._starter_filter = None
        self._populate()

    def _should_hide(self, t):
        """Hide TRAINER_NONE and trainers with no party and default/empty name."""
        if t.key == 'TRAINER_NONE': return True
        if not t.party and not t.name: return True
        if t.trainer_class in ('Pkmn Trainer 1', '') and not t.party: return True
        return False

    def _display_name(self, t):
        """Return 'Class  Name' display string."""
        cls = t.trainer_class.title() if t.trainer_class else ''
        nm  = t.name.title() if t.name else \
              t.key.replace('TRAINER_','').replace('_',' ').title()
        if cls and nm and cls.lower() != nm.lower():
            return f"{cls}  {nm}"
        return nm or cls or t.key

    def _populate(self):
        q = self.search.text().strip().lower()
        sf = self._starter_filter   # e.g. 'TREECKO' or None
        self.tree.clear()
        self._filtered = []

        # Build location -> [(orig_idx, trainer, rival_info)] map
        loc_map = {}
        for i, t in enumerate(self._trainers):
            if self._should_hide(t): continue

            ri = rival_starter_info(t.key)   # None or (type, color, starter_name)

            # When a starter filter is active:
            # - show non-rival trainers normally
            # - show rival variants matching the filter, hide non-matching variants
            if sf and ri is not None:
                # Determine which starter suffix this rival has
                ku = t.key.upper()
                has_sf = ('_' + sf) in ku or ku.endswith('_' + sf)
                if not has_sf:
                    continue   # hide rival variants for other starters

            loc = self._loc_map.get(t.key, 'Other')
            if q and (q not in self._display_name(t).lower()
                      and q not in t.key.lower()
                      and q not in loc.lower()):
                continue
            loc_map.setdefault(loc, []).append((i, t, ri))

        locations = sorted(loc_map.keys(), key=lambda x: ('ZZZ' if x == 'Other' else x))

        for loc in locations:
            entries = loc_map[loc]
            parent_item = QTreeWidgetItem(self.tree, [f"  {loc}  ({len(entries)})"])
            parent_item.setData(0, Qt.UserRole, None)
            parent_item.setForeground(0, QColor('#89b4fa'))
            font = parent_item.font(0); font.setBold(True)
            parent_item.setFont(0, font)
            parent_item.setExpanded(False)

            for orig_idx, t, ri in sorted(entries, key=lambda x: self._display_name(x[1])):
                dname = self._display_name(t)

                if ri is not None:
                    # Rival entry — add type badge prefix
                    starter_type, color, starter_name = ri
                    label = f"  ◆ {dname}  [{starter_name}]"
                    child = QTreeWidgetItem(parent_item, [label])
                    child.setForeground(0, QColor(color))
                    child.setToolTip(0,
                        f"Rival trainer — encountered when player chose {starter_name} "
                        f"({starter_type} starter)")
                    # Bold if this variant matches current starter filter
                    if sf:
                        ku = t.key.upper()
                        is_match = ('_' + sf) in ku or ku.endswith('_' + sf)
                        f2 = child.font(0); f2.setBold(is_match); child.setFont(0, f2)
                else:
                    child = QTreeWidgetItem(parent_item, [f"  {dname}"])
                    child.setForeground(0, QColor('#cdd6f4'))

                child.setData(0, Qt.UserRole, orig_idx)
                self._filtered.append((orig_idx, t))

    def _on_item_clicked(self, item, col):
        idx = item.data(0, Qt.UserRole)
        if idx is not None:
            self.trainer_selected.emit(idx)

    def select_trainer(self, orig_idx):
        """Programmatically select trainer by original index."""
        root = self.tree.invisibleRootItem()
        for i in range(root.childCount()):
            loc_item = root.child(i)
            for j in range(loc_item.childCount()):
                ch = loc_item.child(j)
                if ch.data(0, Qt.UserRole) == orig_idx:
                    self.tree.setCurrentItem(ch)
                    loc_item.setExpanded(True)
                    return

    def refresh(self, trainers):
        self._trainers = trainers
        self._populate()

    def connect_selection(self, callback):
        """Legacy compatibility: callback receives trainer key string."""
        def _on_sel(idx):
            if 0 <= idx < len(self._trainers):
                callback(self._trainers[idx].key)
        self.trainer_selected.connect(_on_sel)

    def update_trainers(self, trainers):
        """Replace the trainer list and repopulate the tree (called on file reload)."""
        self._trainers = trainers
        self._populate()

    def rebuild_loc_map(self):
        """Rebuild trainer→map location mapping (called when map scripts change on disk)."""
        self._loc_map = build_trainer_location_map()
        self._populate()

    def _add_trainer(self):
        QMessageBox.information(self, "Coming Soon",
            "Adding new trainers will be available in a future update.\n\n"
            "To add a trainer now, edit  src/data/trainers.party  directly\n"
            "and the list will reload automatically.")

    def _duplicate_trainer(self):
        QMessageBox.information(self, "Coming Soon",
            "Trainer duplication will be available in a future update.\n\n"
            "To duplicate a trainer, copy its block in  src/data/trainers.party\n"
            "and the list will reload automatically.")

    def _delete_trainer(self):
        QMessageBox.information(self, "Coming Soon",
            "Trainer deletion will be available in a future update.\n\n"
            "To remove a trainer, delete its block from  src/data/trainers.party\n"
            "and the list will reload automatically.")


# ══════════════════════════════════════════════════════════════════════════════
# CUSTOM FRAMELESS TITLE BAR
# ══════════════════════════════════════════════════════════════════════════════
class TitleBar(QWidget):
    """Custom 72 px dark title bar with large icon, app name, min + close buttons."""

    def __init__(self, icon_path, title, parent=None):
        super().__init__(parent)
        self.setFixedHeight(72)
        self._drag_pos = None

        lay = QHBoxLayout(self)
        lay.setContentsMargins(16, 0, 12, 0)
        lay.setSpacing(12)

        # Large icon
        icon_lbl = QLabel()
        icon_lbl.setFixedSize(52, 52)
        icon_lbl.setAlignment(Qt.AlignCenter)
        if icon_path and os.path.isfile(icon_path):
            pix = QPixmap(icon_path).scaled(52, 52, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            icon_lbl.setPixmap(pix)
        lay.addWidget(icon_lbl)

        # Title
        title_lbl = QLabel(title)
        title_lbl.setStyleSheet(
            "color:#cdd6f4; font-size:16px; font-weight:bold; background:transparent;")
        lay.addWidget(title_lbl)
        lay.addStretch()

        # Window buttons
        for symbol, tip, slot in [("─", "Minimize",         self._minimize),
                                   ("□", "Maximize/Restore", self._toggle_maximize),
                                   ("✕", "Close",            self._close)]:
            btn = QPushButton(symbol)
            btn.setFixedSize(36, 36)
            btn.setToolTip(tip)
            btn.setStyleSheet(
                "QPushButton { background:transparent; border:none; border-radius:6px; "
                f"color:#a6adc8; font-size:14px; font-weight:bold; }}"
                "QPushButton:hover { background:#313244; color:#cdd6f4; }"
            )
            if tip == "Close":
                btn.setStyleSheet(
                    "QPushButton { background:transparent; border:none; border-radius:6px; "
                    "color:#a6adc8; font-size:14px; font-weight:bold; }"
                    "QPushButton:hover { background:#f38ba822; color:#f38ba8; }"
                )
            btn.clicked.connect(slot)
            lay.addWidget(btn)

        self.setStyleSheet(
            "TitleBar { background:#181825; border-top-left-radius:12px; "
            "border-top-right-radius:12px; }"
        )

    def _minimize(self):         self.window().showMinimized()
    def _close(self):            self.window().close()
    def _toggle_maximize(self):
        w = self.window()
        if w.isMaximized(): w.showNormal()
        else:               w.showMaximized()

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self._drag_pos = e.globalPos() - self.window().frameGeometry().topLeft()

    def mouseMoveEvent(self, e):
        if self._drag_pos and e.buttons() == Qt.LeftButton:
            self.window().move(e.globalPos() - self._drag_pos)

    def mouseReleaseEvent(self, e):
        self._drag_pos = None

    def mouseDoubleClickEvent(self, e):
        if e.button() == Qt.LeftButton:
            w = self.window()
            if w.isMaximized(): w.showNormal()
            else:               w.showMaximized()


# ══════════════════════════════════════════════════════════════════════════════
# MAIN WINDOW
# ══════════════════════════════════════════════════════════════════════════════
class MainWindow(QMainWindow):
    def __init__(self, header_comment, trainers):
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Window)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self._header_comment = header_comment
        self._trainers       = trainers
        self._trainer_map    = {t.key: t for t in trainers}
        self.setWindowTitle("Party God — Trainer Editor")
        self.resize(1440, 860)
        self.setMinimumSize(1440, 700)
        self._build_ui()

    def _build_ui(self):
        # Outer transparent widget — lets the OS composite the rounded corners
        outer = QWidget()
        outer.setObjectName("pg_outer")
        outer.setStyleSheet(
            "QWidget#pg_outer { background:#1e1e2e; border-radius:12px; "
            "border:1px solid #313244; }"
        )
        outer_lay = QVBoxLayout(outer)
        outer_lay.setContentsMargins(0, 0, 0, 0)
        outer_lay.setSpacing(0)

        # Title bar
        _icon_path = os.path.join(_HERE, "gfx", "party_god_icon.png")
        self._title_bar = TitleBar(_icon_path, "Party God — Trainer Editor", outer)
        outer_lay.addWidget(self._title_bar)

        # Thin divider
        div = QFrame(); div.setFrameShape(QFrame.HLine)
        div.setStyleSheet("QFrame { background:#313244; max-height:1px; border:none; }")
        outer_lay.addWidget(div)

        # Main content
        splitter = QSplitter(Qt.Horizontal)
        splitter.setHandleWidth(2)

        self._list_panel = TrainerListPanel(self._trainers)
        self._list_panel.setFixedWidth(255)
        self._list_panel.connect_selection(self._on_trainer_selected)
        splitter.addWidget(self._list_panel)

        self._editor = TrainerEditorPanel()
        splitter.addWidget(self._editor)
        splitter.setSizes([255, 1185])

        outer_lay.addWidget(splitter, 1)

        # Status bar row at the bottom (manual, since QMainWindow's built-in bar
        # won't sit inside our custom container)
        self._status_bar = QStatusBar()
        self._status_bar.setStyleSheet(
            "QStatusBar { background:#181825; color:#585b70; font-size:11px; "
            "border-bottom-left-radius:12px; border-bottom-right-radius:12px; "
            "border-top:1px solid #313244; }"
        )
        self._status_bar.showMessage(
            f"  {len(self._trainers)} trainers loaded from {PARTY_FILE}"
        )
        _grip = QSizeGrip(self._status_bar)
        _grip.setStyleSheet("background:transparent;")
        self._status_bar.addPermanentWidget(_grip)
        outer_lay.addWidget(self._status_bar)

        self.setCentralWidget(outer)

        # ── Live file watcher (trainers.party + map scripts) ─────────────────
        self._file_watcher = QFileSystemWatcher(self)
        if os.path.isfile(PARTY_FILE):
            self._file_watcher.addPath(PARTY_FILE)

        # Watch all data/maps/*/scripts.inc for trainer location changes
        _maps_dir = os.path.join(ROOT, 'data', 'maps')
        _scripts_watched = []
        if os.path.isdir(_maps_dir):
            for _map_name in sorted(os.listdir(_maps_dir)):
                _si = os.path.join(_maps_dir, _map_name, 'scripts.inc')
                if os.path.isfile(_si):
                    self._file_watcher.addPath(_si)
                    _scripts_watched.append(_si)

        # Debounce timers
        self._reload_timer = QTimer(self)
        self._reload_timer.setSingleShot(True)
        self._reload_timer.setInterval(800)
        self._reload_timer.timeout.connect(self._on_party_file_changed)

        self._loc_reload_timer = QTimer(self)
        self._loc_reload_timer.setSingleShot(True)
        self._loc_reload_timer.setInterval(1200)
        self._loc_reload_timer.timeout.connect(self._on_map_scripts_changed)

        def _on_file_changed(path):
            if path == PARTY_FILE or PARTY_FILE in path:
                self._reload_timer.start()
            else:
                # Re-add path in case editor replaced it
                if path not in self._file_watcher.files():
                    self._file_watcher.addPath(path)
                self._loc_reload_timer.start()

        self._file_watcher.fileChanged.connect(_on_file_changed)

        # Auto-select Youngster Calvin (or first visible trainer) on startup
        QTimer.singleShot(0, self._auto_select_first_trainer)

    def _auto_select_first_trainer(self):
        """Select Youngster Calvin on startup, falling back to the first visible trainer."""
        trainers = self._trainers
        # First pass: find a trainer whose key contains CALVIN
        for i, t in enumerate(trainers):
            if 'CALVIN' in t.key.upper():
                self._list_panel.select_trainer(i)
                self._editor.load_trainer(t)
                self._status_bar.showMessage(f"  {t.key}  ·  {t.name}  ·  {t.trainer_class}")
                return
        # Fallback: first non-hidden trainer
        from decomp_data import build_trainer_location_map
        for i, t in enumerate(trainers):
            if t.key != 'TRAINER_NONE' and t.party:
                self._list_panel.select_trainer(i)
                self._editor.load_trainer(t)
                self._status_bar.showMessage(f"  {t.key}  ·  {t.name}  ·  {t.trainer_class}")
                return

    def _on_party_file_changed(self):
        # Re-add path — some editors replace the file rather than modifying in place
        if PARTY_FILE not in self._file_watcher.files():
            self._file_watcher.addPath(PARTY_FILE)
        self._status_bar.showMessage("  ⟳  trainers.party changed on disk — reloading…")
        try:
            header, trainers = parse_trainers_party()
        except Exception as exc:
            self._status_bar.showMessage(f"  ✗  Reload error: {exc}")
            return
        # Remember the currently-selected trainer key
        current_key = None
        if self._editor._trainer:
            current_key = self._editor._trainer.key
        self._header_comment = header
        self._trainers       = trainers
        self._trainer_map    = {t.key: t for t in trainers}
        self._list_panel.update_trainers(trainers)
        # Re-load the selected trainer if it still exists
        if current_key and current_key in self._trainer_map:
            self._editor.load_trainer(self._trainer_map[current_key])
        self._status_bar.showMessage(
            f"  ✓  Reloaded {len(trainers)} trainers  (trainers.party updated on disk)"
        )

    def _on_map_scripts_changed(self):
        """Rebuild trainer location map when any map scripts.inc file changes."""
        # Re-add any watched paths that may have been replaced by editor
        _maps_dir = os.path.join(ROOT, 'data', 'maps')
        if os.path.isdir(_maps_dir):
            for _map_name in sorted(os.listdir(_maps_dir)):
                _si = os.path.join(_maps_dir, _map_name, 'scripts.inc')
                if os.path.isfile(_si) and _si not in self._file_watcher.files():
                    self._file_watcher.addPath(_si)
        self._list_panel.rebuild_loc_map()
        self._status_bar.showMessage("  \u27f3  Map scripts updated \u2014 trainer locations refreshed")

    def _on_trainer_selected(self, key):
        t = self._trainer_map.get(key)
        if t:
            self._editor.load_trainer(t)
            self._status_bar.showMessage(f"  {key}  ·  {t.name}  ·  {t.trainer_class}")

    def changeEvent(self, event):
        """Toggle border-radius on the outer container when the window is maximized/restored."""
        from PyQt5.QtCore import QEvent
        if event.type() == QEvent.WindowStateChange:
            outer = self.centralWidget()
            if outer:
                if self.isMaximized():
                    outer.setStyleSheet(
                        "QWidget#pg_outer { background:#1e1e2e; border-radius:0; border:none; }"
                    )
                else:
                    outer.setStyleSheet(
                        "QWidget#pg_outer { background:#1e1e2e; border-radius:12px; "
                        "border:1px solid #313244; }"
                    )
        super().changeEvent(event)

    _BASE_W = 1440  # design-reference window width

    def resizeEvent(self, event):
        """Scale fonts proportionally as the window grows/shrinks."""
        super().resizeEvent(event)
        w = max(event.size().width(), self._BASE_W)
        scale = w / self._BASE_W
        # Clamp to a sensible range so things don't go wild
        scale = max(1.0, min(scale, 2.5))
        def _sp(base): return int(round(base * scale))
        app = QApplication.instance()
        if app:
            scaled_style = f"""
QWidget          {{ font-size:{_sp(12)}px; }}
QPushButton      {{ font-size:{_sp(12)}px; padding:{_sp(4)}px {_sp(10)}px; }}
QLineEdit, QSpinBox, QComboBox {{ padding:{_sp(3)}px {_sp(8)}px; min-height:{_sp(22)}px; font-size:{_sp(12)}px; }}
QTabBar::tab     {{ padding:{_sp(5)}px {_sp(12)}px; font-size:{_sp(12)}px; }}
QListWidget::item{{ padding:{_sp(2)}px {_sp(5)}px; }}
QTreeWidget::item{{ padding:{_sp(2)}px {_sp(4)}px; }}
QGroupBox        {{ margin-top:{_sp(5)}px; padding-top:{_sp(4)}px; font-size:{_sp(10)}px; }}
QCheckBox        {{ font-size:{_sp(11)}px; }}
QLabel           {{ font-size:{_sp(12)}px; }}
QLabel#title     {{ font-size:{_sp(14)}px; }}
QLabel#heading   {{ font-size:{_sp(9)}px; }}
"""
            app.setStyleSheet(DARK_STYLE + scaled_style)

    def _save_party_file(self):
        try:
            # Apply current editor state to model first
            if self._editor._trainer:
                self._editor._info_card.save_to_trainer(self._editor._trainer)
                self._editor._trainer.party = self._editor._party_panel.get_party()
            write_trainers_party(self._trainers, self._header_comment)
            self._status_bar.showMessage(
                f"  ✓  Saved {len(self._trainers)} trainers to {PARTY_FILE}"
            )
        except Exception as exc:
            QMessageBox.critical(self, "Save Error", str(exc))


# ══════════════════════════════════════════════════════════════════════════════
# ENTRY POINT
# ══════════════════════════════════════════════════════════════════════════════
def main():
    print("Loading trainer data...", end=' ', flush=True)
    header_comment, trainers = parse_trainers_party()
    print(f"{len(trainers)} trainers loaded.")
    print("Loading reference data (moves, learnsets, items)...", end=' ', flush=True)
    load_moves(); load_items(); load_species()
    print("done.")

    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    # Compact overrides: 1px smaller text + tighter padding across board.
    # TitleBar children use explicit inline font-size so they are unaffected.
    _COMPACT = """
QWidget          { font-size:12px; }
QPushButton      { font-size:12px; padding:4px 10px; }
QLineEdit, QSpinBox, QComboBox { padding:3px 8px; min-height:22px; font-size:12px; }
QTabBar::tab     { padding:5px 12px; font-size:12px; }
QListWidget::item{ padding:2px 5px; }
QTreeWidget::item{ padding:2px 4px; }
QGroupBox        { margin-top:5px; padding-top:4px; font-size:10px; }
QCheckBox        { font-size:11px; }
QLabel           { font-size:12px; }
QLabel#title     { font-size:14px; }
QLabel#heading   { font-size:9px; }
"""
    app.setStyleSheet(DARK_STYLE + _COMPACT)
    _icon_path = os.path.join(_HERE, "gfx", "party_god_icon.png")
    if os.path.isfile(_icon_path):
        app.setWindowIcon(QIcon(_icon_path))
    win = MainWindow(header_comment, trainers)
    win.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
