from PyQt5.QtWidgets import QListWidget, QListWidgetItem, QFrame, QMenu, QBoxLayout
from PyQt5.QtGui import QIcon, QPixmap, QFont, QFontDatabase, QFontMetrics
from PyQt5.QtCore import pyqtSlot, QSize, pyqtSignal

import ray
from gui_server_thread import GuiServerThread
from gui_tools import (client_status_string, _translate, is_dark_theme,
                       RayIcon, split_in_two, get_app_icon)
import child_dialogs
import snapshots_dialog

import ui.preview_client_slot


class ClientSlot(QFrame):
    def __init__(self, list_widget: 'ListWidgetPreviewClients',
                 list_widget_item, client: ray.ClientData):
        QFrame.__init__(self)
        self.ui = ui.preview_client_slot.Ui_ClientSlotWidget()
        self.ui.setupUi(self)

        self.client = client

        self._list_widget = list_widget
        self._list_widget_item = list_widget_item
        self._icon_on = QIcon()
        self._icon_off = QIcon()

        self.ui.actionAddToTheCurrentSession.triggered.connect(
            self._add_to_the_current_session)
        self.ui.actionProperties.triggered.connect(
            self._properties_request)

        self._menu = QMenu(self)
        self._menu.addAction(self.ui.actionAddToTheCurrentSession)
        self._menu.addAction(self.ui.actionProperties)

        self.ui.iconButton.setMenu(self._menu)
        self.update_client_data()
        
        self._server_status = ray.ServerStatus.OFF

    @classmethod
    def to_daemon(cls, *args):
        server = GuiServerThread.instance()
        if server:
            server.to_daemon(*args)

    def _gray_icon(self, gray: bool):
        if gray:
            self.ui.iconButton.setIcon(self._icon_off)
        else:
            self.ui.iconButton.setIcon(self._icon_on)

    def _properties_request(self):
        self._list_widget.properties_request.emit(self.get_client_id())

    def _add_to_the_current_session(self):
        self._list_widget.add_to_session_request.emit(self.get_client_id())

    def set_launched(self, launched: bool):
        self._gray_icon(not launched)
        self.ui.ClientName.setEnabled(launched)

    def server_status_changed(self, server_status:int):
        self.ui.actionAddToTheCurrentSession.setEnabled(
            server_status == ray.ServerStatus.READY)

    def get_client_id(self):
        return self.client.client_id

    def update_disposition(self):
        default_font_size = 13
        font = self.ui.ClientName.font()
        main_size = QFontMetrics(font).width(self.client.prettier_name())

        layout_width = self._list_widget.width()

        scroll_bar = self._list_widget.verticalScrollBar()
        if scroll_bar.isVisible():
            layout_width -= scroll_bar.width()

        max_label_width = layout_width - 50

        if main_size <= max_label_width:
            self.ui.ClientName.setText(self.client.prettier_name())
            return

        # split title in two lines
        top, bottom = split_in_two(self.client.prettier_name())

        max_size = 0

        for text in (top, bottom):
            if not text:
                continue

            size = QFontMetrics(font).width(text)
            max_size = max(max_size, size)

        if max_size <= max_label_width:
            self.ui.ClientName.setText('\n'.join((top, bottom)))
            return

        # responsive design, put label at top of the controls
        # if there is not enought space for label

        max_label_width = layout_width - 50

        if main_size <= max_label_width:
            self.ui.ClientName.setText(self.client.prettier_name())
            return

        top, bottom = split_in_two(self.client.prettier_name())
        self.ui.ClientName.setText('\n'.join((top, bottom)))

    def update_client_data(self):
        # set main label and main disposition
        self.update_disposition()

        # set tool tip
        tool_tip = "<html><head/><body>"
        tool_tip += "<p><span style=\" font-weight:600;\">%s<br></span>" \
            % self.client.name
        tool_tip += "<span style=\" font-style:italic;\">%s</span></p>" \
            % self.client.description
        tool_tip += "<p></p>"
        tool_tip += "<p>%s : %s<br>" \
            % (_translate('client_slot', 'Protocol'),
               ray.protocol_to_str(self.client.protocol))
        tool_tip += "%s : %s<br>" \
            % (_translate('client_slot', 'Executable'),
               self.client.executable_path)
        tool_tip += "%s : %s</p>" \
            % (_translate('client_slot', 'client id'), self.client.client_id)
        tool_tip += "</body></html>"

        self.ui.ClientName.setToolTip(tool_tip)

        # set icon
        self._icon_on = get_app_icon(self.client.icon, self)
        self._icon_off = QIcon(self._icon_on.pixmap(32, 32, QIcon.Disabled))
        self._gray_icon(False)

    def contextMenuEvent(self, event):
        act_selected = self._menu.exec(self.mapToGlobal(event.pos()))
        event.accept()


class ClientItem(QListWidgetItem):
    def __init__(self, parent, client_data):
        QListWidgetItem.__init__(self, parent, QListWidgetItem.UserType + 1)

        self.sort_number = 0
        self.widget = ClientSlot(parent, self, client_data)

        parent.setItemWidget(self, self.widget)
        self.setSizeHint(QSize(100, 45))

    def __lt__(self, other):
        return self.sort_number < other.sort_number

    def __gt__(self, other):
        return self.sort_number > other.sort_number

    def get_client_id(self):
        return self.widget.get_client_id()


class ListWidgetPreviewClients(QListWidget):
    properties_request = pyqtSignal(str)
    add_to_session_request = pyqtSignal(str)

    def __init__(self, parent):
        QListWidget.__init__(self, parent)
        self._last_n = 0
        self.session = None
        self.server_status = ray.ServerStatus.OFF

    @classmethod
    def to_daemon(self, *args):
        server = GuiServerThread.instance()
        if server:
            server.to_daemon(*args)

    def server_status_changed(self, server_status:int):
        self.server_status = server_status
        for i in range(self.count()):
            item = self.item(i)
            item.widget.server_status_changed(server_status)

    def create_client_widget(self, client_data):
        item = ClientItem(self, client_data)
        item.sort_number = self._last_n
        item.widget.server_status_changed(self.server_status)
        self._last_n += 1
        return item.widget

    def remove_client_widget(self, client_id):
        for i in range(self.count()):
            item = self.item(i)
            if item.get_client_id() == client_id:
                widget = item.widget
                self.takeItem(i)
                del item
                break

    def mousePressEvent(self, event):
        if not self.itemAt(event.pos()):
            self.setCurrentRow(-1)

        QListWidget.mousePressEvent(self, event)


    def resizeEvent(self, event):
        QListWidget.resizeEvent(self, event)
        for i in range(self.count()):
            item = self.item(i)
            widget = self.itemWidget(item)
            if widget is not None:
                widget.update_disposition()


