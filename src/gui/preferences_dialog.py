from enum import IntEnum
from typing import TYPE_CHECKING
from PyQt5.QtWidgets import QApplication, QMessageBox
from PyQt5.QtCore import pyqtSlot

from child_dialogs import ChildDialog
from gui_tools import RS
import ray

import ui.settings

if TYPE_CHECKING:
    from main_window import MainWindow


_translate = QApplication.translate


class PreferencesTab(IntEnum):
    DAEMON = 0
    DISPLAY = 1
    SYSTRAY = 2
    DIALOGS = 3


class PreferencesDialog(ChildDialog):
    def __init__(self, parent: 'MainWindow'):
        super().__init__(parent)
        self.ui = ui.settings.Ui_dialogPreferences()
        self.ui.setupUi(self)
        
        self._main_win = parent
        wui = self._main_win.ui
            
        self._check_box_actions = {
            self.ui.checkBoxBookmarks: wui.actionBookmarkSessionFolder,
            self.ui.checkBoxAutoSnapshot: wui.actionAutoSnapshot,
            self.ui.checkBoxDesktopsMemory: wui.actionDesktopsMemory,
            self.ui.checkBoxSessionScripts: wui.actionSessionScripts,
            self.ui.checkBoxGuiStates: wui.actionRememberOptionalGuiStates,
            self.ui.checkBoxMenuBar: wui.actionShowMenuBar,
            self.ui.checkBoxMessages: wui.actionToggleShowMessages,
            self.ui.checkBoxJackPatchbay: wui.actionShowJackPatchbay,
            self.ui.checkBoxKeepFocus: wui.actionKeepFocus
        }
            
        for check_box, action in self._check_box_actions.items():
            check_box.setText(action.text())
            check_box.setIcon(action.icon())
            check_box.setToolTip(action.toolTip())
            check_box.setChecked(action.isChecked())
            check_box.stateChanged.connect(self._check_box_state_changed)
            action.changed.connect(self._action_changed)

        self.ui.pushButtonPatchbayPreferences.clicked.connect(
            self._main_win.session.patchbay_manager.show_options_dialog)
        
        self.ui.groupBoxSystray.toggled.connect(self._systray_changed)
        for check_box in (self.ui.checkBoxOnlySessionRunning,
                          self.ui.checkBoxReversedMenu,
                          self.ui.checkBoxShutdown):
            check_box.stateChanged.connect(self._systray_changed)
        
        self.ui.pushButtonReappear.clicked.connect(
            self._make_all_dialogs_reappear)
        self.ui.checkboxStartupDialogs.stateChanged.connect(
            self._show_startup_dialog)
        self._main_win.session.signaler.hiddens_changed.connect(
            self._hiddens_changed)

    @pyqtSlot()
    def _check_box_state_changed(self):
        sender = self.sender()
        for check_box, action in self._check_box_actions.items():
            if check_box is sender:
                action.setChecked(check_box.isChecked())
                break
    
    @pyqtSlot()
    def _action_changed(self):
        sender = self.sender()
        for checkbox, action in self._check_box_actions.items():
            if action is sender:
                checkbox.setChecked(action.isChecked())
                break
    
    @pyqtSlot()
    def _systray_changed(self):
        self._main_win.change_systray_options(
            self._get_systray_mode(),
            self.ui.checkBoxShutdown.isChecked(),
            self.ui.checkBoxReversedMenu.isChecked()
        )
    
    def _get_systray_mode(self) -> int:
        if self.ui.groupBoxSystray.isChecked():
            if self.ui.checkBoxOnlySessionRunning.isChecked():
                return ray.Systray.SESSION_ONLY
            return ray.Systray.ALWAYS
        return ray.Systray.OFF
    
    def _make_all_dialogs_reappear(self):
        button = QMessageBox.question(
            self,
            _translate('hidden_dialogs', 'Make reappear dialog windows'),
            _translate('hidden_dialogs',
                       'Do you want to make reappear all dialogs you wanted to hide ?'))
        
        if button == QMessageBox.Yes:
            RS.reset_hiddens()
    
    def _show_startup_dialog(self, yesno: int):
        RS.set_hidden(RS.HD_StartupRecentSessions, not yesno)
        
    def _hiddens_changed(self, hiddens: int):
        self.ui.pushButtonReappear.setEnabled(bool(hiddens > 0))
        self.ui.checkboxStartupDialogs.setChecked(
            not hiddens & RS.HD_StartupRecentSessions)
        
    def set_on_tab(self, tab: PreferencesTab):
        self.ui.tabWidget.setCurrentIndex(int(tab))