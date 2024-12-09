
# Imports from standard library
import os
import sys
from typing import TYPE_CHECKING
import logging

# Imports from HoustonPatchbay
from patchbay.patchcanvas.patshared import GroupPos

# Imports from src/shared
from osclib import ServerThread, get_net_url, make_method, TCP
import ray

# Local imports
from gui_tools import CommandLineArgs
from gui_tcp_thread import GuiTcpThread

if TYPE_CHECKING:
    from gui_session import SignaledSession


_logger = logging.getLogger(__name__)
_instance = None


def ray_method(path, types):
    def decorated(func):
        @make_method(path, types)
        def wrapper(*args, **kwargs):
            t_thread, t_path, t_args, t_types, src_addr, rest = args
            if TYPE_CHECKING:
                assert isinstance(t_thread, GuiServerThread)

            _logger.debug(
                '\033[93mOSC::gui_receives\033[0m '
                f'{t_path}, {t_types}, {t_args}, {src_addr.url}')

            if t_thread.stopping:
                return

            response = func(*args[:-1], **kwargs)

            if not response is False:
                t_thread.signaler.osc_receive.emit(t_path, t_args)

            return response
        return wrapper
    return decorated


class GuiServerThread(ServerThread):
    def __init__(self):
        ServerThread.__init__(self)

        global _instance
        _instance = self

        # Try to prevent impossibility to stop server
        # while receiving messages
        self.stopping = False
        
        self._parrallel_copy_id_queue = []
        self._parrallel_new_session_name = ''

    def stop(self):
        self.stopping = True
        super().stop()

    def finish_init(self, session: 'SignaledSession'):
        self.session = session
        self.signaler = self.session.signaler
        self.daemon_manager = self.session.daemon_manager

        # all theses OSC messages are directly treated by
        # SignaledSession in gui_session.py
        # in the function with the the name of the message
        # with '/' replaced with '_'
        # for example /ray/gui/session/name goes to
        # _ray_gui_session_name

        for path_types in (
            ('/error', 'sis'),
            ('/minor_error', 'sis'),
            ('/ray/gui/server/disannounce', ''),
            ('/ray/gui/server/nsm_locked', 'i'),
            ('/ray/gui/server/options', 'i'),
            ('/ray/gui/server/message', 's'),
            ('/ray/gui/server/terminal_command', 's'),
            ('/ray/gui/session/name', 'ss'),
            ('/ray/gui/session/notes', 's'),
            ('/ray/gui/session/notes_shown', ''),
            ('/ray/gui/session/notes_hidden', ''),
            ('/ray/gui/session/is_nsm', ''),
            ('/ray/gui/session/renameable', 'i'),
            ('/ray/gui/client/new', ray.ClientData.sisi()),
            ('/ray/gui/client/update', ray.ClientData.sisi()),
            ('/ray/gui/client/ray_hack_update', 's' + ray.RayHack.sisi()),
            ('/ray/gui/client/switch', 'ss'),
            ('/ray/gui/client/status', 'si'),
            ('/ray/gui/client/dirty', 'si'),
            ('/ray/gui/client/has_optional_gui', 's'),
            ('/ray/gui/client/gui_visible', 'si'),
            ('/ray/gui/client/still_running', 's'),
            ('/ray/gui/trash/add', ray.ClientData.sisi()),
            ('/ray/gui/trash/ray_hack_update', 's' + ray.RayHack.sisi()),
            ('/ray/gui/trash/ray_net_update', 's' + ray.RayNet.sisi()),
            ('/ray/gui/trash/remove', 's'),
            ('/ray/gui/trash/clear', ''),
            ('/ray/gui/favorites/added', 'ssis'),
            ('/ray/gui/favorites/removed', 'si'),
            ('/ray/gui/preview/clear', ''),
            ('/ray/gui/preview/notes', 's'),
            ('/ray/gui/preview/client/update', ray.ClientData.sisi()),
            ('/ray/gui/preview/client/ray_hack_update', 's' + ray.RayHack.sisi()),
            ('/ray/gui/preview/client/ray_net_update', 's' + ray.RayNet.sisi()),
            ('/ray/gui/preview/client/is_started', 'si'),
            ('/ray/gui/preview/snapshot', 's'),
            ('/ray/gui/preview/session_size', 'h'),
            ('/ray/gui/script_info', 's'),
            ('/ray/gui/hide_script_info', ''),
            ('/ray/gui/script_user_action', 's'),
            ('/ray/gui/hide_script_user_action', '')):
                self.add_method(path_types[0], path_types[1],
                                self._generic_callback)

    @staticmethod
    def instance():
        return _instance

    def _generic_callback(self, path, args, types, src_addr):
        if self.stopping:
            return

        _logger.debug(
            '\033[93mOSC::gui_receives\033[0m '
            f'({path}, {args}, {types})')

        self.signaler.osc_receive.emit(path, args)

    @ray_method('/reply', None)
    def _reply(self, path, args: list, types: str, src_addr):
        if not (types and ray.types_are_all_strings(types)):
            return False

        new_args = args.copy()
        reply_path = new_args.pop(0)

        if reply_path == '/ray/server/list_sessions':
            self.signaler.add_sessions_to_list.emit(new_args)
        elif reply_path == '/ray/server/list_path':
            self.signaler.new_executable.emit(new_args)
        elif reply_path == '/ray/server/list_session_templates':
            self.signaler.session_template_found.emit(new_args)
        elif reply_path == '/ray/server/list_user_client_templates':
            self.signaler.user_client_template_found.emit(new_args)
        elif reply_path == '/ray/server/list_factory_client_templates':
            self.signaler.factory_client_template_found.emit(new_args)
        elif reply_path in ('/ray/session/list_snapshots',
                            '/ray/client/list_snapshots'):
            self.signaler.snapshots_found.emit(new_args)
        elif reply_path == '/ray/server/get_session_preview':
            self.signaler.session_preview_update.emit()
        elif reply_path == '/ray/server/rename_session':
            self.signaler.other_session_renamed.emit()
        elif reply_path == '/ray/session/duplicate_only':
            self.signaler.other_session_duplicated.emit()
        elif reply_path == '/ray/server/save_session_template':
            self.signaler.other_session_templated.emit()
        elif reply_path == '/ray/server/abort_parrallel_copy':
            self.signaler.parrallel_copy_aborted.emit()

    @ray_method('/ray/gui/server/announce', 'siisis')
    def _server_announce(self, path, args, types, src_addr):
        if self.daemon_manager.is_announced():
            return

        (version, server_status_int, options,
         session_root, is_net_free, tcp_url) = args
        
        tcp_server = GuiTcpThread.instance()
        if tcp_server is not None:
            tcp_server.set_daemon_tcp_url(tcp_url)

        if (self.session is not None
                and self.session.main_win is not None
                and self.session.main_win.waiting_for_patchbay):
            tcp_url = get_net_url(GuiTcpThread.instance().port, protocol=TCP)
            self.send(src_addr, '/ray/server/ask_for_patchbay', tcp_url)
            self.session.main_win.waiting_for_patchbay = False

        self.signaler.daemon_announce.emit(
            src_addr, version, ray.ServerStatus(server_status_int),
            ray.Option(options), session_root, is_net_free)

    @ray_method('/ray/gui/server/root', 's')
    def _server_root(self, path, args, types, src_addr):
        session_root = args[0]
        CommandLineArgs.change_session_root(session_root)
        self.signaler.root_changed.emit(session_root)

    @ray_method('/ray/gui/server/status', 'i')
    def _server_status(self, path, args, types, src_addr):
        self.signaler.server_status_changed.emit(ray.ServerStatus(args[0]))

    @ray_method('/ray/gui/server/copying', 'i')
    def _server_copying(self, path, args, types, src_addr):
        copying = args[0]
        self.signaler.server_copying.emit(bool(copying))

    @ray_method('/ray/gui/server/parrallel_copy_state', 'ii')
    def _server_parrallel_copy_state(self, path, args, types, src_addr):
        session_id, state = args

        if state:
            # copy is starting
            if self._parrallel_copy_id_queue:
                if session_id not in self._parrallel_copy_id_queue:
                    self._parrallel_copy_id_queue.append(session_id)
            else:
                self._parrallel_copy_id_queue.append(session_id)
                self.signaler.parrallel_copy_state.emit(*args)
        else:
            # copy is finished
            if session_id in self._parrallel_copy_id_queue:
                self._parrallel_copy_id_queue.remove(session_id)
                self.signaler.parrallel_copy_state.emit(*args)

    @ray_method('/ray/gui/server/parrallel_copy_progress', 'if')
    def _server_copy_progress(self, path, args, types, src_addr):
        session_id, progress = args

        if not self._parrallel_copy_id_queue:
            return
        
        if session_id == self._parrallel_copy_id_queue[0]:
            self.signaler.parrallel_copy_progress.emit(*args)

    @ray_method('/ray/gui/server/progress', 'f')
    def _server_progress(self, path, args, types, src_addr):
        progress = args[0]
        self.signaler.server_progress.emit(progress)

    @ray_method('/ray/gui/server/recent_sessions', None)
    def _server_recent_sessions(self, path, args, types, src_addr):
        for t in types:
            if t != 's':
                return False

    @ray_method('/ray/gui/session/auto_snapshot', 'i')
    def _session_auto_snapshot(self, path, args, types, src_addr):
        self.signaler.reply_auto_snapshot.emit(bool(args[0]))

    @ray_method('/ray/gui/session/sort_clients', None)
    def _session_sort_clients(self, path, args, types, src_addr):
        if not ray.types_are_all_strings(types):
            return False

    @ray_method('/ray/gui/listed_session/details', 'sihi')
    def _listed_session_details(self, path, args, types, src_addr):
        self.signaler.session_details.emit(*args)

    @ray_method('/ray/gui/listed_session/scripted_dir', 'si')
    def _listed_session_scripted_dir(self, path, args, types, src_addr):
        self.signaler.scripted_dir.emit(*args)

    @ray_method('/ray/gui/client_template_update', 'iss' + ray.ClientData.sisi())
    def _client_template_update(self, path, args, types, src_addr):
        self.signaler.client_template_update.emit(args)

    @ray_method('/ray/gui/client_template_ray_hack_update', 'is' + ray.RayHack.sisi())
    def _client_template_ray_hack_update(self, path, args, types, src_addr):
        self.signaler.client_template_ray_hack_update.emit(args)

    @ray_method('/ray/gui/client_template_ray_net_update', 'is' + ray.RayNet.sisi())
    def _client_template_ray_net_update(self, path, args, types, src_addr):
        self.signaler.client_template_ray_net_update.emit(args)

    @ray_method('/ray/gui/client/progress', 'sf')
    def _client_progress(self, path, args, types, src_addr):
        self.signaler.client_progress.emit(*args)
        return True

    def send(self, *args):
        _logger.debug(f'\033[95mOSC::gui sends\033[0m {args[1:]}')
        super().send(*args)

    def to_daemon(self, *args):
        self.send(self.daemon_manager.address, *args)

    def announce(self):
        _logger.debug('raysession_sends announce')

        NSM_URL = os.getenv('NSM_URL')
        if not NSM_URL:
            NSM_URL = ''

        tcp_server = GuiTcpThread.instance()
        tcp_url = get_net_url(tcp_server.port, protocol=TCP)

        self.send(self.daemon_manager.address, '/ray/server/gui_announce',
                  ray.VERSION, int(CommandLineArgs.under_nsm),
                  NSM_URL, os.getpid(),
                  CommandLineArgs.net_daemon_id, tcp_url)

    def disannounce(self, src_addr):
        self.send(src_addr, '/ray/server/gui_disannounce')

    def open_session(self, session_name, save_previous=1, session_template=''):
        self.to_daemon('/ray/server/open_session', session_name,
                      save_previous, session_template)

    def save_session(self):
        self.to_daemon('/ray/session/save')

    def close_session(self):
        self.to_daemon('/ray/session/close')

    def abort_session(self):
        self.to_daemon('/ray/session/abort')

    def duplicate_a_session(self, session_name:str, new_session_name:str):
        self._parrallel_new_session_name = new_session_name
        self.to_daemon('/ray/gui/session/duplicate_only',
                       session_name, new_session_name,
                       CommandLineArgs.session_root)

    def get_parrallel_copy_id(self)->int:
        ''' used by open session dialog to know
        if a parrallel copy is running '''
        if not self._parrallel_copy_id_queue:
            return 0

        return self._parrallel_copy_id_queue[0]

    def get_parrallel_new_session_name(self)->str:
        return self._parrallel_new_session_name

