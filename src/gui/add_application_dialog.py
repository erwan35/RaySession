from PyQt5.QtCore import Qt, QSize
from PyQt5.QtWidgets import (QDialogButtonBox, QListWidgetItem, QFrame,
                             QMenu, QAction, QShortcut)
from PyQt5.QtGui import QIcon

import ray
import ui
import client_properties_dialog

from gui_tools import RS, _translate, is_dark_theme, get_app_icon
from child_dialogs import ChildDialog


TEMPLATE_NAME_DATA = Qt.UserRole
DISPLAY_NAME_DATA = Qt.UserRole +1

class TemplateSlot(QFrame):
    def __init__(self, list_widget, session,
                 name: str, factory: bool, client_data: ray.ClientData):
        QFrame.__init__(self)
        self.ui = ui.template_slot.Ui_Frame()
        self.ui.setupUi(self)

        self._factory = factory
        self._list_widget = list_widget
        self._name = name
        self._user_menu = QMenu()

        self.session = session
        self.client_data = client_data

        self.ui.toolButtonIcon.setIcon(
            get_app_icon(self.client_data.icon, self))
        
        self.ui.label.setText(name)
        
        self.ui.toolButtonUser.setVisible(not factory)

        act_remove_template = QAction(QIcon.fromTheme('edit-delete-remove'),
                                      _translate('menu', 'remove'),
                                      self._user_menu)
        act_remove_template.triggered.connect(self.remove_template)
        self._user_menu.addAction(act_remove_template)
        self.ui.toolButtonUser.setMenu(self._user_menu)

        self.ui.toolButtonFavorite.set_session(self.session)
        self.ui.toolButtonFavorite.set_template(
            self._name, self.client_data.icon, self._factory)

        if is_dark_theme(self):
            self.ui.toolButtonUser.setIcon(
                QIcon(':scalable/breeze-dark/im-user.svg'))
            self.ui.toolButtonFavorite.set_dark_theme()

    def update_client_data(self, *args):
        self.client_data.update(*args)
        self.ui.toolButtonIcon.setIcon(
            get_app_icon(self.client_data.icon, self))
        self.ui.toolButtonFavorite.set_template(
            self._name, self.client_data.icon, self._factory)

    def update_ray_hack_data(self, *args):
        if self.client_data.ray_hack is None:
            self.client_data.ray_hack = ray.RayHack.new_from(*args)
        self.client_data.ray_hack.update(*args)

    def update_ray_net_data(self, *args):
        if self.client_data.ray_net is None:
            self.client_data.ray_net = ray.RayNet.new_from(*args)
        self.client_data.ray_net.update(*args)

    def set_display_name(self, display_name: str):
        self.ui.label.setText(display_name)

    def get_display_name(self)->str:
        return self.ui.label.text()

    def remove_template(self):
        add_app_dialog = self._list_widget.parent()
        add_app_dialog.remove_template(self._name, self._factory)

    def set_as_favorite(self, yesno: bool):
        self.ui.toolButtonFavorite.set_as_favorite(yesno)

    def mouseDoubleClickEvent(self, event):
        self._list_widget.parent().accept()


class TemplateItem(QListWidgetItem):
    def __init__(self, parent, session, name, factory):
        QListWidgetItem.__init__(self, parent, QListWidgetItem.UserType + 1)

        self.client_data = ray.ClientData()
        self._widget = TemplateSlot(parent, session,
                                    name, factory, self.client_data)
        self.setData(TEMPLATE_NAME_DATA, name)
        self.setData(DISPLAY_NAME_DATA, name)
        parent.setItemWidget(self, self._widget)
        self.setSizeHint(QSize(100, 28))

        self.is_factory = factory

    def __lt__(self, other):
        self_name = self.data(DISPLAY_NAME_DATA)
        other_name = other.data(DISPLAY_NAME_DATA)
        
        if other_name is None or not other_name:
            return False

        if self_name == other_name:
            # make the user template on top
            return not self.is_factory

        return bool(self_name.lower() < other_name.lower())

    def matches_with(self, factory, name: str):
        return bool(bool(factory) == bool(self.is_factory)
                    and name == self.data(TEMPLATE_NAME_DATA))

    def update_client_data(self, *args):
        self._widget.update_client_data(*args)

    def update_ray_hack_data(self, *args):
        self._widget.update_ray_hack_data(*args)

    def update_ray_net_data(self, *args):
        self._widget.update_ray_net_data(*args)

    def set_display_name(self, display_name: str):
        self.setData(DISPLAY_NAME_DATA, display_name)
        self._widget.set_display_name(display_name)

    def get_display_name(self)->str:
        return self._widget.get_display_name()

    def set_as_favorite(self, yesno: bool):
        self._widget.set_as_favorite(yesno)


class RemoveTemplateDialog(ChildDialog):
    def __init__(self, parent, template_name):
        ChildDialog.__init__(self, parent)
        self.ui = ui.remove_template.Ui_Dialog()
        self.ui.setupUi(self)

        self.ui.label.setText(
            _translate(
                'add_app_dialog',
                '<p>Are you sure to want to remove<br>the template "%s" and all its files ?</p>')
                % template_name)

        self.ui.pushButtonCancel.setFocus()

class AddApplicationDialog(ChildDialog):
    def __init__(self, parent):
        ChildDialog.__init__(self, parent)
        self.ui = ui.add_application.Ui_DialogAddApplication()
        self.ui.setupUi(self)

        self.session = parent.session

        self.ui.checkBoxFactory.setChecked(RS.settings.value(
            'AddApplication/factory_box', True, type=bool))
        self.ui.checkBoxUser.setChecked(RS.settings.value(
            'AddApplication/user_box', True, type=bool))
        self.ui.checkBoxRayHack.setChecked(RS.settings.value(
            'AddApplication/ray_hack_box', True, type=bool))
        self.ui.widgetTemplateInfos.setVisible(False)

        self.ui.checkBoxFactory.stateChanged.connect(self._factory_box_changed)
        self.ui.checkBoxUser.stateChanged.connect(self._user_box_changed)
        self.ui.checkBoxNsm.stateChanged.connect(self._nsm_box_changed)
        self.ui.checkBoxRayHack.stateChanged.connect(self._ray_hack_box_changed)
        self.ui.pushButtonRefresh.clicked.connect(self._refresh_database)
        self._refresh_shortcut = QShortcut('F5', self)
        self._refresh_shortcut.activated.connect(self._refresh_database)

        self.ui.templateList.currentItemChanged.connect(
            self._current_item_changed)
        self.ui.templateList.setFocus(Qt.OtherFocusReason)
        self.ui.filterBar.textEdited.connect(self._update_filtered_list)
        self.ui.filterBar.up_down_pressed.connect(self._up_down_pressed)

        self.ui.buttonBox.button(QDialogButtonBox.Ok).setEnabled(False)

        self.user_menu = QMenu()
        act_remove_template = QAction(QIcon.fromTheme('edit-delete-remove'),
                                      _translate('menu', 'remove'),
                                      self.user_menu)
        act_remove_template.triggered.connect(self._remove_current_template)
        self.user_menu.addAction(act_remove_template)
        self.ui.toolButtonUser.setMenu(self.user_menu)
        self.ui.toolButtonFavorite.set_session(self.session)
        self.ui.widgetNonSaveable.setVisible(False)
        self.ui.toolButtonAdvanced.clicked.connect(
            self._tool_button_advanced_clicked)

        if is_dark_theme(self):
            self.ui.toolButtonUser.setIcon(
                QIcon(':scalable/breeze-dark/im-user.svg'))
            self.ui.toolButtonFavorite.set_dark_theme()
            self.ui.toolButtonNoSave.setIcon(
                QIcon(':scalable/breeze-dark/document-nosave.svg'))

        self.signaler.user_client_template_found.connect(
            self._add_user_templates)
        self.signaler.factory_client_template_found.connect(
            self._add_factory_templates)
        self.signaler.client_template_update.connect(
            self._update_client_template)
        self.signaler.client_template_ray_hack_update.connect(
            self._update_client_template_ray_hack)
        self.signaler.client_template_ray_net_update.connect(
            self._update_client_template_ray_net)
        self.signaler.favorite_added.connect(self._favorite_added)
        self.signaler.favorite_removed.connect(self._favorite_removed)

        self.to_daemon('/ray/server/list_user_client_templates')
        self.to_daemon('/ray/server/list_factory_client_templates')
        self.listing_finished = 0

        self.user_template_list = []
        self.factory_template_list = []

        self._server_will_accept = False
        self.has_selection = False

        self._server_status_changed(self.session.server_status)

        self.ui.filterBar.setFocus()

    def _favorite_added(self, template_name: str,
                        template_icon: str, factory: bool):
        for i in range(self.ui.templateList.count()):
            item = self.ui.templateList.item(i)
            if item is None:
                continue

            if (item.data(TEMPLATE_NAME_DATA) == template_name
                    and item.is_factory == factory):
                item.set_as_favorite(True)
                if item == self.ui.templateList.currentItem():
                    self.ui.toolButtonFavorite.set_as_favorite(True)
                break

    def _favorite_removed(self, template_name: str, factory: bool):
        for i in range(self.ui.templateList.count()):
            item = self.ui.templateList.item(i)
            if item is None:
                continue

            if (item.data(TEMPLATE_NAME_DATA) == template_name
                    and item.is_factory == factory):
                item.set_as_favorite(False)
                if item == self.ui.templateList.currentItem():
                    self.ui.toolButtonFavorite.set_as_favorite(False)
                break

    def _factory_box_changed(self, state):
        if not state:
            self.ui.checkBoxUser.setChecked(True)

        self._update_filtered_list()

    def _user_box_changed(self, state):
        if not state:
            self.ui.checkBoxFactory.setChecked(True)

        self._update_filtered_list()

    def _nsm_box_changed(self, state):
        if not state:
            self.ui.checkBoxRayHack.setChecked(True)

        self._update_filtered_list()

    def _ray_hack_box_changed(self, state):
        if not state:
            self.ui.checkBoxNsm.setChecked(True)

        self._update_filtered_list()

    def _refresh_database(self):
        self.ui.pushButtonRefresh.setEnabled(False)
        self.ui.templateList.clear()
        self.user_template_list.clear()
        self.factory_template_list.clear()
        self.to_daemon('/ray/server/clear_client_templates_database')
        self.to_daemon('/ray/server/list_user_client_templates')
        self.to_daemon('/ray/server/list_factory_client_templates')

    def _add_user_templates(self, template_list):
        for template_name in template_list:
            if template_name in self.user_template_list:
                continue

            self.user_template_list.append(template_name)

            item = TemplateItem(
                self.ui.templateList, self.session, template_name, False)
            
            if self.session.is_favorite(template_name, False):
                item.set_as_favorite(True)

            self.ui.templateList.addItem(item)

        self.ui.templateList.sortItems()

        self._update_filtered_list()

    def _add_factory_templates(self, template_list):
        for template_name in template_list:
            if template_name in self.factory_template_list:
                continue

            self.factory_template_list.append(template_name)

            item = TemplateItem(
                self.ui.templateList, self.session, template_name, True)
            
            if self.session.is_favorite(template_name, True):
                item.set_as_favorite(True)

            self.ui.templateList.addItem(item)

        self.ui.templateList.sortItems()

        self._update_filtered_list()
        
        if not template_list:
            self.ui.pushButtonRefresh.setEnabled(True)

    def _update_client_template(self, args):
        factory = bool(args[0])
        template_name = args[1]
        display_name = args[2]

        for i in range(self.ui.templateList.count()):
            item = self.ui.templateList.item(i)

            if item.matches_with(factory, template_name):
                if display_name:
                    item.set_display_name(display_name)
                item.update_client_data(*args[3:])
                if self.ui.templateList.currentItem() == item:
                    self._update_template_infos(item)
                break

    def _update_client_template_ray_hack(self, args):
        factory = bool(args[0])
        template_name = args[1]

        for i in range(self.ui.templateList.count()):
            item = self.ui.templateList.item(i)

            if item.matches_with(factory, template_name):
                item.update_ray_hack_data(*args[2:])
                if self.ui.templateList.currentItem() == item:
                    self._update_template_infos(item)
                break

    def _update_client_template_ray_net(self, args):
        factory = bool(args[0])
        template_name = args[1]

        for i in range(self.ui.templateList.count()):
            item = self.ui.templateList.item(i)

            if item.matches_with(factory, template_name):
                item.update_ray_net_data(*args[2:])
                if self.ui.templateList.currentItem() == item:
                    self._update_template_infos(item)
                break

    def _update_filtered_list(self, filt=''):
        filter_text = self.ui.filterBar.displayText()

        # show all items
        for i in range(self.ui.templateList.count()):
            self.ui.templateList.item(i).setHidden(False)

        # hide all non matching items
        for i in range(self.ui.templateList.count()):
            item = self.ui.templateList.item(i)
            template_name = item.data(TEMPLATE_NAME_DATA)

            if not filter_text.lower() in template_name.lower():
                item.setHidden(True)

            if item.is_factory and not self.ui.checkBoxFactory.isChecked():
                item.setHidden(True)

            if not item.is_factory and not self.ui.checkBoxUser.isChecked():
                item.setHidden(True)

            if item.client_data is not None:
                if (item.client_data.protocol == ray.Protocol.RAY_HACK
                        and not self.ui.checkBoxRayHack.isChecked()):
                    item.setHidden(True)

                if (item.client_data.protocol != ray.Protocol.RAY_HACK
                        and not self.ui.checkBoxNsm.isChecked()):
                    item.setHidden(True)

        # if selected item not in list, then select the first visible
        if (not self.ui.templateList.currentItem()
                or self.ui.templateList.currentItem().isHidden()):
            for i in range(self.ui.templateList.count()):
                if not self.ui.templateList.item(i).isHidden():
                    self.ui.templateList.setCurrentRow(i)
                    break

        if (not self.ui.templateList.currentItem()
                or self.ui.templateList.currentItem().isHidden()):
            if self.ui.filterBar.text():
                self.ui.filterBar.setStyleSheet(
                    "QLineEdit { background-color: red}")
            self.ui.templateList.setCurrentItem(None)
        else:
            self.ui.filterBar.setStyleSheet("")
            self.ui.templateList.scrollTo(self.ui.templateList.currentIndex())

    def _up_down_pressed(self, key):
        row = self.ui.templateList.currentRow()
        if key == Qt.Key_Up:
            if row == 0:
                return
            row -= 1
            while self.ui.templateList.item(row).isHidden():
                if row == 0:
                    return
                row -= 1
        elif key == Qt.Key_Down:
            if row == self.ui.templateList.count() - 1:
                return
            row += 1
            while self.ui.templateList.item(row).isHidden():
                if row == self.ui.templateList.count() - 1:
                    return
                row += 1
        self.ui.templateList.setCurrentRow(row)

    def _update_template_infos(self, item):
        self.ui.widgetTemplateInfos.setVisible(bool(item))
        self.ui.widgetNoTemplate.setVisible(not bool(item))

        if not item:
            return

        cdata = item.client_data
        self.ui.toolButtonIcon.setIcon(
            get_app_icon(cdata.icon, self))

        template_name = item.data(TEMPLATE_NAME_DATA)

        self.ui.labelTemplateName.setText(item.get_display_name())
        #self.ui.labelTemplateName.setText(template_name)
        self.ui.labelDescription.setText(cdata.description)
        self.ui.labelProtocol.setText(ray.protocol_to_str(cdata.protocol))
        self.ui.labelExecutable.setText(cdata.executable_path)
        self.ui.labelLabel.setText(cdata.label)
        self.ui.labelName.setText(cdata.name)

        for widget in (self.ui.labelProtocolTitle,
                       self.ui.labelProtocolColon,
                       self.ui.labelProtocol):
            widget.setVisible(bool(cdata.protocol != ray.Protocol.NSM))

        for widget in (self.ui.labelLabelTitle,
                       self.ui.labelLabelColon,
                       self.ui.labelLabel):
            widget.setVisible(bool(cdata.label))

        for widget in (self.ui.labelNameTitle,
                       self.ui.labelNameColon,
                       self.ui.labelName):
            widget.setVisible(bool(cdata.protocol == ray.Protocol.NSM))

        self.ui.toolButtonUser.setVisible(not item.is_factory)
        self.ui.toolButtonFavorite.set_template(
            item.data(TEMPLATE_NAME_DATA), cdata.icon, item.is_factory)
        self.ui.toolButtonFavorite.set_as_favorite(self.session.is_favorite(
            item.data(TEMPLATE_NAME_DATA), item.is_factory))

        self.ui.widgetNonSaveable.setVisible(bool(
            cdata.ray_hack is not None
            and cdata.protocol == ray.Protocol.RAY_HACK
            and cdata.ray_hack.no_save_level > 0))

        # little security
        # client_properties_dialog could crash if ray_hack has not been updated yet
        # (never seen this appears, but it could with slow systems)
        self.ui.toolButtonAdvanced.setEnabled(
            bool(cdata.protocol != ray.Protocol.RAY_HACK
                 or cdata.ray_hack is not None))

    def _current_item_changed(self, item, previous_item):
        self.has_selection = bool(item)
        self._update_template_infos(item)
        self._prevent_ok()

    def _tool_button_advanced_clicked(self):
        item = self.ui.templateList.currentItem()
        if item is None:
            return

        properties_dialog = client_properties_dialog.ClientPropertiesDialog.create(
            self, item.client_data)
        properties_dialog.update_contents()
        properties_dialog.set_for_template(item.data(TEMPLATE_NAME_DATA))
        properties_dialog.show()

    def _prevent_ok(self):
        self.ui.buttonBox.button(QDialogButtonBox.Ok).setEnabled(
            bool(self._server_will_accept and self.has_selection))

    def _remove_current_template(self):
        item = self.ui.templateList.currentItem()
        if not item:
            return

        self.remove_template(item.data(TEMPLATE_NAME_DATA), False)

    def _server_status_changed(self, server_status):
        self._server_will_accept = bool(
            server_status not in (
                ray.ServerStatus.OFF,
                ray.ServerStatus.CLOSE) and not self.server_copying)
        self._prevent_ok()

    def get_selected_template(self)->tuple:
        item = self.ui.templateList.currentItem()
        if item:
            return (item.data(TEMPLATE_NAME_DATA), item.is_factory)

    def remove_template(self, template_name, factory):
        dialog = RemoveTemplateDialog(self, template_name)
        dialog.exec()
        if not dialog.result():
            return

        self.to_daemon('/ray/server/remove_client_template', template_name)

        for i in range(self.ui.templateList.count()):
            item = self.ui.templateList.item(i)

            if (not item.is_factory
                    and template_name == item.data(TEMPLATE_NAME_DATA)):
                item.setHidden(True)
                if item == self.ui.templateList.currentItem():
                    self._update_template_infos(None)
                self.ui.templateList.removeItemWidget(item)
                break

    def save_check_boxes(self):
        RS.settings.setValue(
            'AddApplication/factory_box',
            self.ui.checkBoxFactory.isChecked())
        RS.settings.setValue(
            'AddApplication/user_box',
            self.ui.checkBoxUser.isChecked())
        RS.settings.setValue(
            'AddApplication/ray_hack_box',
            self.ui.checkBoxRayHack.isChecked())
        RS.settings.sync()
