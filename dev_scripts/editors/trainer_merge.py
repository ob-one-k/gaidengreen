#!/usr/bin/env python3
"""
trainer_merge.py — Trainer Party File Merge Tool

Select a .party file, review a git-style diff against src/data/trainers.party,
then apply or cancel.
"""
from __future__ import annotations

import difflib
import shutil
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_LIB  = _HERE / "lib"
if str(_LIB) not in sys.path:
    sys.path.insert(0, str(_LIB))

from decomp_data import PARTY_FILE, DARK_STYLE  # noqa: E402

CANONICAL = Path(PARTY_FILE)

try:
    from PyQt5.QtCore    import Qt, QSize
    from PyQt5.QtGui     import QColor, QFont, QPixmap, QTextCharFormat, QTextCursor
    from PyQt5.QtWidgets import (
        QApplication, QFileDialog, QFrame, QHBoxLayout, QLabel,
        QMainWindow, QMessageBox, QPlainTextEdit, QPushButton,
        QSizeGrip, QStatusBar, QVBoxLayout, QWidget,
    )
except ImportError:
    print("PyQt5 not found.  Install with:  pip install PyQt5")
    sys.exit(1)

# ── Colours (Catppuccin Mocha) ─────────────────────────────────────────────────
_C_BG       = "#1e1e2e"
_C_SURFACE  = "#181825"
_C_OVERLAY  = "#313244"
_C_SUBTEXT  = "#6c7086"
_C_TEXT     = "#cdd6f4"
_C_BLUE     = "#89b4fa"
_C_GREEN    = "#a6e3a1"
_C_RED      = "#f38ba8"
_C_YELLOW   = "#f9e2af"
_C_CYAN     = "#89dceb"

# ── Diff line background tints (semi-transparent feel via solid dark mix) ──────
_BG_ADD  = "#1b2b1b"
_BG_REM  = "#2b1b1b"
_BG_HUNK = "#1a1a2e"

_COMPACT = """
QWidget        { font-size:12px; }
QPushButton    { font-size:12px; padding:5px 14px; }
QLabel         { font-size:12px; }
QStatusBar     { font-size:11px; }
"""


# ══════════════════════════════════════════════════════════════════════════════
# TITLE BAR
# ══════════════════════════════════════════════════════════════════════════════

class TitleBar(QWidget):
    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        self.setFixedHeight(64)
        self._drag_pos = None

        lay = QHBoxLayout(self)
        lay.setContentsMargins(16, 0, 12, 0)
        lay.setSpacing(10)

        icon_lbl = QLabel()
        icon_lbl.setFixedSize(44, 44)
        icon_lbl.setAlignment(Qt.AlignCenter)
        icon_path = str(_HERE / "gfx" / "trainer_merge_icon.png")
        pix = QPixmap(icon_path)
        if not pix.isNull():
            icon_lbl.setPixmap(
                pix.scaled(44, 44, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            )
        lay.addWidget(icon_lbl)

        title_lbl = QLabel(title)
        title_lbl.setStyleSheet(
            f"color:{_C_TEXT}; font-size:15px; font-weight:bold; background:transparent;"
        )
        lay.addWidget(title_lbl)
        lay.addStretch()

        for sym, tip, slot in [
            ("─", "Minimize",         lambda: self.window().showMinimized()),
            ("□", "Maximize/Restore", self._toggle_max),
            ("✕", "Close",            lambda: self.window().close()),
        ]:
            btn = QPushButton(sym)
            btn.setFixedSize(34, 34)
            btn.setToolTip(tip)
            close_style = (
                f"QPushButton {{ background:transparent; border:none; border-radius:5px; "
                f"color:{_C_SUBTEXT}; font-size:13px; font-weight:bold; }}"
                f"QPushButton:hover {{ background:#f38ba822; color:{_C_RED}; }}"
            ) if tip == "Close" else (
                f"QPushButton {{ background:transparent; border:none; border-radius:5px; "
                f"color:{_C_SUBTEXT}; font-size:13px; font-weight:bold; }}"
                f"QPushButton:hover {{ background:{_C_OVERLAY}; color:{_C_TEXT}; }}"
            )
            btn.setStyleSheet(close_style)
            btn.clicked.connect(slot)
            lay.addWidget(btn)

        self.setStyleSheet(
            f"TitleBar {{ background:{_C_SURFACE}; border-top-left-radius:12px; "
            f"border-top-right-radius:12px; }}"
        )

    def _toggle_max(self):
        w = self.window()
        w.showNormal() if w.isMaximized() else w.showMaximized()

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self._drag_pos = e.globalPos() - self.window().frameGeometry().topLeft()

    def mouseMoveEvent(self, e):
        if self._drag_pos and e.buttons() == Qt.LeftButton:
            self.window().move(e.globalPos() - self._drag_pos)

    def mouseReleaseEvent(self, _):
        self._drag_pos = None

    def mouseDoubleClickEvent(self, e):
        if e.button() == Qt.LeftButton:
            self._toggle_max()


# ══════════════════════════════════════════════════════════════════════════════
# DIFF ENGINE
# ══════════════════════════════════════════════════════════════════════════════

def _read(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    return text.replace("\r\n", "\n").replace("\r", "\n")


def compute_diff(src: Path, dst: Path):
    """Return list of (kind, text) tuples.
    kind: 'hunk' | 'add' | 'rem' | 'ctx' | 'header'
    """
    a_lines = _read(dst).splitlines(keepends=True)
    b_lines = _read(src).splitlines(keepends=True)
    raw = list(difflib.unified_diff(a_lines, b_lines, fromfile=dst.name, tofile=src.name, n=3))
    if not raw:
        return [], 0, 0

    added   = sum(1 for l in raw if l.startswith("+") and not l.startswith("+++"))
    removed = sum(1 for l in raw if l.startswith("-") and not l.startswith("---"))

    lines = []
    for line in raw:
        line = line.rstrip("\n")
        if line.startswith("@@"):
            lines.append(("hunk", line))
        elif line.startswith("+++") or line.startswith("---"):
            lines.append(("header", line))
        elif line.startswith("+"):
            lines.append(("add", line))
        elif line.startswith("-"):
            lines.append(("rem", line))
        else:
            lines.append(("ctx", line))

    return lines, added, removed


# ══════════════════════════════════════════════════════════════════════════════
# DIFF VIEWER WIDGET
# ══════════════════════════════════════════════════════════════════════════════

def _fmt(fg: str, bg: str | None = None, bold: bool = False) -> QTextCharFormat:
    f = QTextCharFormat()
    f.setForeground(QColor(fg))
    if bg:
        f.setBackground(QColor(bg))
    if bold:
        f.setFontWeight(QFont.Bold)
    return f


_FMT = {
    "header": _fmt(_C_SUBTEXT),
    "hunk":   _fmt(_C_CYAN,  _BG_HUNK, bold=True),
    "add":    _fmt(_C_GREEN, _BG_ADD),
    "rem":    _fmt(_C_RED,   _BG_REM),
    "ctx":    _fmt(_C_SUBTEXT),
    "empty":  _fmt(_C_SUBTEXT),
}


class DiffViewer(QPlainTextEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)
        self.setLineWrapMode(QPlainTextEdit.NoWrap)
        self.setStyleSheet(
            f"QPlainTextEdit {{ background:{_C_BG}; color:{_C_TEXT}; border:none; "
            f"font-family:'Cascadia Code','Consolas','Courier New',monospace; font-size:11px; }}"
        )

    def load(self, diff_lines: list):
        self.clear()
        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.End)

        if not diff_lines:
            fmt = _fmt(_C_SUBTEXT)
            cursor.setCharFormat(fmt)
            cursor.insertText("  No differences — files are identical.")
            self.setTextCursor(cursor)
            return

        for kind, text in diff_lines:
            fmt = _FMT.get(kind, _FMT["ctx"])
            cursor.setCharFormat(fmt)
            cursor.insertText(text + "\n")

        self.setTextCursor(cursor)
        self.moveCursor(QTextCursor.Start)


# ══════════════════════════════════════════════════════════════════════════════
# MAIN WINDOW
# ══════════════════════════════════════════════════════════════════════════════

class MainWindow(QMainWindow):
    def __init__(self, initial_file: str | None = None):
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Window)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setWindowTitle("Trainer Party Merge")
        self.resize(1100, 700)
        self.setMinimumSize(700, 450)

        self._src: Path | None = None
        self._has_diff = False

        self._build_ui()

        if initial_file:
            self._set_source(Path(initial_file))

    # ── UI ────────────────────────────────────────────────────────────────────

    def _build_ui(self):
        outer = QWidget()
        outer.setObjectName("tm_outer")
        outer.setStyleSheet(
            f"QWidget#tm_outer {{ background:{_C_BG}; border-radius:12px; "
            f"border:1px solid {_C_OVERLAY}; }}"
        )
        vlay = QVBoxLayout(outer)
        vlay.setContentsMargins(0, 0, 0, 0)
        vlay.setSpacing(0)

        # Title bar
        vlay.addWidget(TitleBar("Trainer Party Merge", outer))

        # Divider
        vlay.addWidget(self._divider())

        # File picker strip
        strip = QWidget()
        strip.setObjectName("strip")
        strip.setStyleSheet(f"QWidget#strip {{ background:{_C_SURFACE}; border:none; }}")
        slay = QHBoxLayout(strip)
        slay.setContentsMargins(16, 10, 16, 10)
        slay.setSpacing(10)

        slay.addWidget(QLabel("Source file:"))

        self._path_lbl = QLabel("No file selected")
        self._path_lbl.setStyleSheet(
            f"color:{_C_SUBTEXT}; background:{_C_OVERLAY}; border-radius:6px; "
            f"padding:4px 10px; font-size:11px;"
        )
        self._path_lbl.setMinimumWidth(200)
        slay.addWidget(self._path_lbl, 1)

        self._browse_btn = QPushButton("Browse…")
        self._browse_btn.setObjectName("accent")
        self._browse_btn.clicked.connect(self._browse)
        slay.addWidget(self._browse_btn)

        slay.addSpacing(20)

        target_lbl = QLabel(f"Target:  {CANONICAL}")
        target_lbl.setStyleSheet(f"color:{_C_TEXT}; font-size:11px;")
        slay.addWidget(target_lbl)

        vlay.addWidget(strip)
        vlay.addWidget(self._divider())

        # Diff viewer
        self._viewer = DiffViewer()
        vlay.addWidget(self._viewer, 1)

        vlay.addWidget(self._divider())

        # Bottom action bar
        bot = QWidget()
        bot.setObjectName("bot")
        bot.setStyleSheet(f"QWidget#bot {{ background:{_C_SURFACE}; border:none; }}")
        blay = QHBoxLayout(bot)
        blay.setContentsMargins(16, 10, 16, 10)
        blay.setSpacing(10)

        self._stat_lbl = QLabel("")
        self._stat_lbl.setStyleSheet(f"color:{_C_SUBTEXT}; font-size:11px;")
        blay.addWidget(self._stat_lbl)
        blay.addStretch()

        self._cancel_btn = QPushButton("Cancel")
        self._cancel_btn.clicked.connect(self.close)
        blay.addWidget(self._cancel_btn)

        self._apply_btn = QPushButton("Apply Merge")
        self._apply_btn.setObjectName("accent")
        self._apply_btn.setEnabled(False)
        self._apply_btn.clicked.connect(self._apply)
        blay.addWidget(self._apply_btn)

        vlay.addWidget(bot)

        # Status bar
        self._status = QStatusBar()
        self._status.setStyleSheet(
            f"QStatusBar {{ background:{_C_SURFACE}; color:{_C_SUBTEXT}; font-size:11px; "
            f"border-bottom-left-radius:12px; border-bottom-right-radius:12px; "
            f"border-top:1px solid {_C_OVERLAY}; }}"
        )
        grip = QSizeGrip(self._status)
        grip.setStyleSheet("background:transparent;")
        self._status.addPermanentWidget(grip)
        vlay.addWidget(self._status)

        self.setCentralWidget(outer)
        self._set_status("Select a .party file to begin.")

    @staticmethod
    def _divider() -> QFrame:
        f = QFrame()
        f.setFrameShape(QFrame.HLine)
        f.setStyleSheet(f"QFrame {{ background:{_C_OVERLAY}; max-height:1px; border:none; }}")
        return f

    # ── Logic ─────────────────────────────────────────────────────────────────

    def _set_status(self, msg: str):
        self._status.showMessage("  " + msg)

    def _browse(self):
        start = str(self._src.parent if self._src else _HERE)
        dlg = QFileDialog(self, "Select .party file to merge", start,
                          "Party files (*.party);;All files (*.*)")
        dlg.setOption(QFileDialog.DontUseNativeDialog, True)
        dlg.setFileMode(QFileDialog.ExistingFile)
        if dlg.exec_():
            files = dlg.selectedFiles()
            if files:
                self._set_source(Path(files[0]))

    def _set_source(self, src: Path):
        if not src.exists():
            QMessageBox.warning(self, "File Not Found", f"File not found:\n{src}")
            return
        if not CANONICAL.exists():
            QMessageBox.critical(self, "Missing Target",
                                 f"Target file not found:\n{CANONICAL}")
            return

        self._src = src
        self._path_lbl.setText(str(src))
        self._path_lbl.setStyleSheet(
            f"color:{_C_TEXT}; background:{_C_OVERLAY}; border-radius:6px; "
            f"padding:4px 10px; font-size:11px;"
        )
        self._set_status("Computing diff…")
        QApplication.processEvents()

        diff_lines, added, removed = compute_diff(src, CANONICAL)
        self._viewer.load(diff_lines)

        self._has_diff = bool(diff_lines)
        self._apply_btn.setEnabled(self._has_diff)

        if self._has_diff:
            self._stat_lbl.setText(
                f"<span style='color:{_C_GREEN};'>+{added} insertion{'s' if added != 1 else ''}</span>"
                f"&nbsp;&nbsp;"
                f"<span style='color:{_C_RED};'>-{removed} deletion{'s' if removed != 1 else ''}</span>"
            )
            self._stat_lbl.setTextFormat(Qt.RichText)
            self._set_status(
                f"Diff ready — {added} insertion(s), {removed} deletion(s). "
                f"Review above, then click Apply Merge."
            )
        else:
            self._stat_lbl.setText("No differences.")
            self._set_status("Files are identical — nothing to merge.")

    def _apply(self):
        if not self._src or not self._has_diff:
            return
        reply = QMessageBox.question(
            self, "Confirm Merge",
            f"Apply changes from:\n  {self._src}\n\nto:\n  {CANONICAL}\n\n"
            f"A backup will be saved as  {CANONICAL.name}.bak",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return

        bak = CANONICAL.with_suffix(".party.bak")
        shutil.copy2(CANONICAL, bak)
        shutil.copy2(self._src, CANONICAL)

        self._apply_btn.setEnabled(False)
        self._set_status(f"Merge applied.  Backup saved to  {bak.name}")
        QMessageBox.information(
            self, "Merge Complete",
            f"trainers.party updated successfully.\nBackup: {bak}",
        )

    # ── Window state ──────────────────────────────────────────────────────────

    def changeEvent(self, event):
        from PyQt5.QtCore import QEvent
        if event.type() == QEvent.WindowStateChange:
            outer = self.centralWidget()
            if outer:
                outer.setStyleSheet(
                    f"QWidget#tm_outer {{ background:{_C_BG}; border-radius:0; border:none; }}"
                    if self.isMaximized() else
                    f"QWidget#tm_outer {{ background:{_C_BG}; border-radius:12px; "
                    f"border:1px solid {_C_OVERLAY}; }}"
                )
        super().changeEvent(event)


# ══════════════════════════════════════════════════════════════════════════════
# ENTRY POINT
# ══════════════════════════════════════════════════════════════════════════════

def main():
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setStyleSheet(DARK_STYLE + _COMPACT)

    initial = sys.argv[1] if len(sys.argv) >= 2 else None
    win = MainWindow(initial_file=initial)
    win.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
