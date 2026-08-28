"""Label panel widget — call, actions, confidence, and weapon controls.

Keyboard shortcuts:
  Call:       1=LEFT, 2=RIGHT, 3=NONE
  Confidence: Q=high, W=med, E=low
  Weapon:     set once via dropdown
"""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QButtonGroup,
    QComboBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QRadioButton,
    QVBoxLayout,
    QWidget,
)

from a1.rules.taxonomy import FoilAction, SabreAction

# Action lists by weapon
_FOIL_ACTIONS = [a.value for a in FoilAction]
_SABRE_ACTIONS = [a.value for a in SabreAction]


class LabelPanel(QWidget):
    """Panel for labeling one exchange: call, confidence, actions, weapon."""

    call_changed = Signal(str, str)
    actions_changed = Signal(list, list)
    weapon_changed = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._weapon = "foil"

        layout = QVBoxLayout()

        # --- Weapon selector ---
        weapon_group = QGroupBox("Weapon")
        weapon_layout = QHBoxLayout()
        self._weapon_combo = QComboBox()
        self._weapon_combo.addItems(["foil", "sabre", "epee"])
        self._weapon_combo.currentTextChanged.connect(self._on_weapon_changed)
        weapon_layout.addWidget(self._weapon_combo)
        weapon_group.setLayout(weapon_layout)
        layout.addWidget(weapon_group)

        # --- Call buttons ---
        call_group = QGroupBox("Call  (1=LEFT  2=RIGHT  3=NONE)")
        call_layout = QHBoxLayout()
        self._call_buttons = QButtonGroup(self)
        for i, label in enumerate(["LEFT", "RIGHT", "NONE"]):
            btn = QRadioButton(label)
            self._call_buttons.addButton(btn, i)
            call_layout.addWidget(btn)
        self._call_buttons.buttonClicked.connect(self._on_call_clicked)
        call_group.setLayout(call_layout)
        layout.addWidget(call_group)

        # --- Confidence buttons ---
        conf_group = QGroupBox("Confidence  (Q=high  W=med  E=low)")
        conf_layout = QHBoxLayout()
        self._conf_buttons = QButtonGroup(self)
        for i, label in enumerate(["high", "med", "low"]):
            btn = QRadioButton(label)
            self._conf_buttons.addButton(btn, i)
            conf_layout.addWidget(btn)
        conf_group.setLayout(conf_layout)
        layout.addWidget(conf_group)

        # --- Actions (left fencer) ---
        left_group = QGroupBox("Actions — Left Fencer")
        left_layout = QVBoxLayout()
        self._left_actions = QListWidget()
        self._left_actions.setSelectionMode(QListWidget.SelectionMode.MultiSelection)
        self._left_actions.addItems(_FOIL_ACTIONS)
        self._left_actions.itemSelectionChanged.connect(self._on_actions_selection_changed)
        left_layout.addWidget(self._left_actions)
        left_group.setLayout(left_layout)
        layout.addWidget(left_group)

        # --- Actions (right fencer) ---
        right_group = QGroupBox("Actions — Right Fencer")
        right_layout = QVBoxLayout()
        self._right_actions = QListWidget()
        self._right_actions.setSelectionMode(QListWidget.SelectionMode.MultiSelection)
        self._right_actions.addItems(_FOIL_ACTIONS)
        self._right_actions.itemSelectionChanged.connect(self._on_actions_selection_changed)
        right_layout.addWidget(self._right_actions)
        right_group.setLayout(right_layout)
        layout.addWidget(right_group)

        # --- Status ---
        self._status = QLabel("No label set")
        layout.addWidget(self._status)

        self.setLayout(layout)

    def get_call(self) -> tuple[str, str]:
        """Return (call, confidence) strings; empty string if not set."""
        call_btn = self._call_buttons.checkedButton()
        conf_btn = self._conf_buttons.checkedButton()
        call = call_btn.text() if call_btn else ""
        conf = conf_btn.text() if conf_btn else ""
        return call, conf

    def get_actions(self) -> tuple[list[str], list[str]]:
        """Return (left_actions, right_actions) as lists of selected action strings."""
        left = [item.text() for item in self._left_actions.selectedItems()]
        right = [item.text() for item in self._right_actions.selectedItems()]
        return left, right

    def get_weapon(self) -> str:
        """Return the currently selected weapon string."""
        return self._weapon

    def reset(self) -> None:
        """Clear all selections and reset status label."""
        self._call_buttons.setExclusive(False)
        for btn in self._call_buttons.buttons():
            btn.setChecked(False)
        self._call_buttons.setExclusive(True)
        self._conf_buttons.setExclusive(False)
        for btn in self._conf_buttons.buttons():
            btn.setChecked(False)
        self._conf_buttons.setExclusive(True)
        self._left_actions.clearSelection()
        self._right_actions.clearSelection()
        self._status.setText("No label set")

    def handle_key(self, key: str) -> bool:
        """Handle keyboard shortcuts. Returns True if the key was handled.

        Call:       1=LEFT, 2=RIGHT, 3=NONE
        Confidence: Q=high, W=med, E=low
        """
        call_map = {"1": 0, "2": 1, "3": 2}
        conf_map = {"q": 0, "w": 1, "e": 2}

        if key in call_map:
            self._call_buttons.buttons()[call_map[key]].setChecked(True)
            self._on_call_clicked()
            return True
        if key.lower() in conf_map:
            self._conf_buttons.buttons()[conf_map[key.lower()]].setChecked(True)
            self._on_call_clicked()
            return True
        return False

    def _on_actions_selection_changed(self) -> None:
        left, right = self.get_actions()
        self.actions_changed.emit(left, right)

    def _on_call_clicked(self) -> None:
        call, conf = self.get_call()
        if call and conf:
            self.call_changed.emit(call, conf)
            self._status.setText(f"Call: {call} ({conf})")

    def _on_weapon_changed(self, weapon: str) -> None:
        self._weapon = weapon
        if weapon == "foil":
            actions: list[str] = _FOIL_ACTIONS
        elif weapon == "sabre":
            actions = _SABRE_ACTIONS
        else:
            # Epee has no priority — it is the negative control; no actions to label
            actions = []
        self._left_actions.clear()
        self._right_actions.clear()
        if actions:
            self._left_actions.addItems(actions)
            self._right_actions.addItems(actions)
        self.weapon_changed.emit(weapon)
