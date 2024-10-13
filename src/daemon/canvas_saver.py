
import json
from os import remove
from pathlib import Path
import pty
import tempfile
import time
from typing import TYPE_CHECKING

from liblo import Address

import ray
from daemon_tools import RS, Terminal
from server_sender import ServerSender
from jack_renaming_tools import group_belongs_to_client
from patchcanvas_enums import (
    from_json_to_str, PortTypesViewFlag, GroupPos, ViewData,
    portgroups_mem_from_json, portgroups_memory_to_json,
    PortType, PortMode, PortgroupMem)

if TYPE_CHECKING:
    from session_signaled import SignaledSession


JSON_PATH = 'ray_canvas.json'

def _get_version_tuple_json_dict(json_contents: dict) -> tuple[int, int, int]:
    if 'version' in json_contents.keys():
        version_str: str = json_contents['version']
        try:
            version_list = [int(v) for v in version_str.split('.')]
        except:
            version_list = [int(v) for v in ray.VERSION.split('.')]
    else:
        version_list = [0, 12, 0]
    
    return tuple(version_list)


class CanvasSaver(ServerSender):
    def __init__(self, session: 'SignaledSession'):
        ServerSender.__init__(self)
        self.session = session

        self.views_session = dict[
            int, dict[PortTypesViewFlag, dict[str, GroupPos]]]()
        self.views_config = dict[
            int, dict[PortTypesViewFlag, dict[str, GroupPos]]]()
        self.view_datas_session = dict[int, ViewData]()
        self.view_datas_config = dict[int, ViewData]()

        self.portgroups = dict[
            PortType, dict[str, dict[PortMode, list[PortgroupMem]]]]()
        self._config_json_path = \
            Path(RS.settings.fileName()).parent / JSON_PATH

        if not self._config_json_path.exists():
            return

        with open(self._config_json_path, 'r') as f:
            json_contents = {}

            try:
                json_contents = json.load(f)
            except json.JSONDecodeError:
                Terminal.message(
                    f"Failed to load patchcanvas config file {f}")

            if isinstance(json_contents, dict):
                if 'views' in json_contents.keys():
                    self.write_view_from_json(
                        json_contents['views'], config=True)

                elif 'group_positions' in json_contents.keys():
                    gpos_list: list[GroupPos] = \
                        json_contents['group_positions']
                    gpos_version = _get_version_tuple_json_dict(json_contents)
                    self.views_config[1] = \
                        dict[PortTypesViewFlag, dict[str, GroupPos]]()
                    self.view_datas_config[1] = ViewData(PortTypesViewFlag.ALL)

                    for gpos_dict in gpos_list:
                        gpos = GroupPos.from_serialized_dict(
                            gpos_dict, version=gpos_version)
                        ptv = gpos.port_types_view
                        ptv_dict = self.views_config[1].get(ptv)
                        if ptv_dict is None:
                            ptv_dict = self.views_config[1][ptv] = \
                                dict[str, GroupPos]()

                        ptv_dict[gpos.group_name] = gpos

                if 'portgroups' in json_contents.keys():
                    self.portgroups = portgroups_mem_from_json(
                        json_contents['portgroups'])

    def write_view_from_json(self, json_list: list, config=False):
        if not isinstance(json_list, list):
            return {}

        if config:
            views_dict = self.views_config
            data_dict = self.view_datas_config
        else:
            views_dict = self.views_session
            data_dict = self.view_datas_session
        
        views_dict.clear()
        data_dict.clear()
        
        for view_dict in json_list:
            if not isinstance(view_dict, dict):
                continue

            view_num = view_dict.get('index')
            if not isinstance(view_num, int):
                continue
            
            views_dict[view_num] = dict[
                PortTypesViewFlag, dict[str, GroupPos]]()
            data_dict[view_num] = ViewData(PortTypesViewFlag.ALL)

            view_name = view_dict.get('name')
            if not isinstance(view_name, str):
                view_name = ''
            default_ptv = PortTypesViewFlag.from_config_str(
                view_dict.get('default_port_types', 'ALL'))
            is_white_list = view_dict.get('is_white_list')
            if not isinstance(is_white_list, bool):
                is_white_list = False
            
            data_dict[view_num].name = view_name
            data_dict[view_num].default_port_types_view = default_ptv
            data_dict[view_num].is_white_list = is_white_list
            
            ptv_str: str

            for ptv_str, ptv_dict in view_dict.items():
                ptv = PortTypesViewFlag.from_config_str(ptv_str)
                if ptv is PortTypesViewFlag.NONE:
                    continue
                
                views_dict[view_num][ptv] = dict[str, GroupPos]()
                
                group_name: str
                ptv_dict: dict
                for group_name, gpos_dict in ptv_dict.items():
                    if not isinstance(gpos_dict, dict):
                        continue
                    
                    gpos = GroupPos.from_new_dict(ptv, group_name, gpos_dict)
                    views_dict[view_num][ptv][group_name] = gpos

    def send_session_group_positions(self):
        server = self.get_server()
        if not server:
            return

        local_guis = list['Address']()
        distant_guis = list['Address']()
        for gui_addr in server.gui_list:
            if ray.are_on_same_machine(server.url, gui_addr.url):
                local_guis.append(gui_addr)
            else:
                distant_guis.append(gui_addr)

        if local_guis:
            views_dict = {'views': self.get_json_view_list()}

            for gui_addr in local_guis:
                with (tempfile.NamedTemporaryFile(delete=False, mode='w+')
                        as f):
                    json.dump(views_dict, f)

                    self.send(gui_addr,
                            '/ray/gui/patchbay/fast_temp_file_memory',
                            f.name)

        if distant_guis:
            for gui_addr in distant_guis:
                for view_number, view_dict in self.views_session.items():
                    for ptv, gps_dict in view_dict.items():
                        for group_name, group_pos in gps_dict.items():
                            self.send(
                                gui_addr,
                                '/ray/gui/patchbay/update_group_position',
                                view_number, *group_pos.to_arg_list())

    def get_json_view_list(self, config=False) -> list[dict]:
        if config:
            views_dict = self.views_config
            data_dict = self.view_datas_config            
        else:
            views_dict = self.views_session
            data_dict = self.view_datas_session
        
        out_list = list[dict]()
        
        for view_index, view_dict in views_dict.items():
            view = {}
            view['index'] = view_index
            view_data = data_dict.get('index')
            if view_data is not None:
                view['default_port_types_view'] = \
                    view_data.default_port_types_view.name
                view['is_white_list'] = view_data.is_white_list
            
            for ptv, ptv_dict in view_dict.items():
                view[ptv.name] = {}
                for group_name, group_pos in ptv_dict.items():
                    view[ptv.name][group_name] = group_pos.as_new_dict()
            
            out_list.append(view)
        
        return out_list

    def send_all_group_positions(self, src_addr: Address):
        if ray.are_on_same_machine(self.get_server_url(), src_addr.url):
            canvas_dict = dict[str, list]()
            canvas_dict['portgroups'] = portgroups_memory_to_json(
                self.portgroups)

            config_list = self.get_json_view_list(config=True)
            session_list = self.get_json_view_list(config=False)

            for view_dict in session_list:
                for cf_view_dict in config_list:
                    if cf_view_dict['index'] == view_dict['index']:
                        config_list.remove(cf_view_dict)
                        break
                config_list.append(view_dict)
            
            canvas_dict['views'] = config_list
            
            with tempfile.NamedTemporaryFile(delete=False, mode='w+') as f:
                json.dump(canvas_dict, f)
                self.send(src_addr,
                          '/ray/gui/patchbay/fast_temp_file_memory',
                          f.name)
            return
        
        i = 0

        for view_index, ptvs_dict in self.views_session.items():
            for ptv, gps_dict in ptvs_dict.items():
                for group_name, gpos in gps_dict.items():
                    self.send(
                        src_addr, '/ray/gui/patchbay/update_group_position',
                        view_index, *gpos.to_arg_list())
                    
                    i += 1
                    if i == 50:
                        # we need to slow big process of canvas memory
                        # to prevent loss OSC packets
                        time.sleep(0.020)
                        i = 0

        for view_index, ptvs_dict in self.views_config.items():
            ptvs_dict_sess = self.views_session.get(view_index)
            for ptv, gps_dict in ptvs_dict.items():
                gps_dict_sess = None
                if ptvs_dict_sess is not None:
                    gps_dict_sess = ptvs_dict_sess.get(ptv)
                
                for group_name, gpos in gps_dict.items():
                    if (gps_dict_sess is not None
                            and gps_dict_sess.get(group_name) is not None):
                        continue
                    
                    self.send(
                        src_addr, '/ray/gui/patchbay/update_group_position',
                        view_index, *gpos.to_arg_list())
                    
                    i += 1
                    if i == 50:
                        # we need to slow big process of canvas memory
                        # to prevent loss OSC packets
                        time.sleep(0.020)
                        i = 0

        for ptype_dict in self.portgroups.values():
            for gp_dict in ptype_dict.values():
                for pmode_list in gp_dict.values():
                    for pg_mem in pmode_list:
                        self.send(
                            src_addr, '/ray/gui/patchbay/update_portgroup',
                            *pg_mem.to_arg_list())

            i += 1
            if i == 50:
                time.sleep(0.020)

    def save_group_position(self, *args):
        view_num, ptv_int, group_name, *rest = args
        ptv = PortTypesViewFlag(ptv_int)
        
        ptvs_dict = self.views_session.get(view_num)
        if ptvs_dict is None:
            ptvs_dict = self.views_session[view_num] = \
                dict[PortTypesViewFlag, dict[str, GroupPos]]()
        
        ptv_dict = ptvs_dict.get(ptv)
        if ptv_dict is None:
            ptv_dict = ptvs_dict[ptv] = dict[str, GroupPos]()
            
        ptv_dict[group_name] = GroupPos.from_arg_list(args[1:])
        
        ptvs_dict_cf = self.views_config.get(view_num)
        if ptvs_dict_cf is None:
            ptvs_dict_cf = self.views_config[view_num] = \
                dict[PortTypesViewFlag, dict[str, GroupPos]]()
        
        ptv_dict_cf = ptvs_dict_cf.get(ptv)
        if ptv_dict_cf is None:
            ptv_dict_cf = ptvs_dict_cf[ptv] = dict[str, GroupPos]()
            
        ptv_dict_cf[group_name] = GroupPos.from_arg_list(args[1:])

    def load_json_session_canvas(self, session_path: Path):
        self.views_session.clear()
        self.view_datas_session.clear()

        session_canvas_file = session_path / f'.{JSON_PATH}'
        if not session_canvas_file.exists():
            return

        with open(session_canvas_file, 'r') as f:
            json_contents = {}
            gpos_list = list[dict]()

            try:
                json_contents = json.load(f)
            except json.JSONDecodeError:
                Terminal.message("Failed to load session canvas file %s" % f)

            session_version = (0, 15, 0)

            if isinstance(json_contents, dict):
                if 'views' in json_contents.keys():
                    self.write_view_from_json(json_contents['views'])
                
                elif 'group_positions' in json_contents.keys():
                    gpos_list : list[dict] = json_contents['group_positions']
                    session_version = _get_version_tuple_json_dict(
                        json_contents)

                    # affect all existing group positions to view 1
                    self.views_session[1] = \
                        dict[PortTypesViewFlag, dict[str, GroupPos]]()
                    self.view_datas_session[1] = ViewData(PortTypesViewFlag.ALL)

                    for gpos_dict in gpos_list:
                        gpos = GroupPos.from_serialized_dict(
                            gpos_dict, version=session_version)
                        gpos_list.append(gpos)
                        
                        self.views_session[1]
                        ptv_dict = self.views_session[1].get(gpos.port_types_view)
                        if ptv_dict is None:
                            ptv_dict = self.views_session[1][gpos.port_types_view] = \
                                dict[str, GroupPos]()
                        ptv_dict[gpos.group_name] = gpos

    def save_json_session_canvas(self, session_path: Path):
        session_json_path = session_path / f'.{JSON_PATH}'

        json_contents = {}
        json_contents['views'] = self.get_json_view_list()        
        json_contents['version'] = ray.VERSION

        with open(session_json_path, 'w+') as f:
            f.write(from_json_to_str(json_contents))

    def save_config_file(self):
        json_contents = {}
        json_contents['views'] = self.get_json_view_list(config=True)
        json_contents['portgroups'] = portgroups_memory_to_json(
            self.portgroups)
        json_contents['version'] = ray.VERSION

        with open(self._config_json_path, 'w+') as f:
            f.write(from_json_to_str(json_contents))

    def save_portgroup(self, *args):
        nw_pg_mem = PortgroupMem.from_arg_list(args)

        ptype_dict = self.portgroups.get(nw_pg_mem.port_type)
        if ptype_dict is None:
            ptype_dict = self.portgroups[nw_pg_mem.port_type] = \
                dict[str, dict[PortMode, list[PortgroupMem]]]()
        
        gp_dict = ptype_dict.get(nw_pg_mem.group_name)
        if gp_dict is None:
            gp_dict = ptype_dict[nw_pg_mem.group_name] = \
                dict[PortMode, list[PortgroupMem]]()
                
        pg_list = gp_dict.get(nw_pg_mem.port_mode)
        if pg_list is None:
            pg_list = gp_dict[nw_pg_mem.port_mode] = list[PortgroupMem]()        

        # remove any portgroup with a commmon port with the new one
        remove_list = list[PortgroupMem]()

        for pg_mem in pg_list:
            for port_name in pg_mem.port_names:
                if port_name in nw_pg_mem.port_names:
                    remove_list.append(pg_mem)
                    
        for pg_mem in remove_list:
            pg_list.remove(pg_mem)
        
        pg_list.append(nw_pg_mem)

    def client_jack_name_changed(
            self, old_jack_name: str, new_jack_name: str):
        server = self.session.get_server()
        
        for view_num, view_dict in self.views_session.items():
            for ptv, ptv_dict in view_dict.items():
                group_name_change_list = list[tuple(str, str)]()
                
                for group_name, group_pos in ptv_dict.items():
                    if group_belongs_to_client(group_name, old_jack_name):
                        new_group_name = group_name.replace(
                            old_jack_name, new_jack_name, 1)
                        group_name_change_list.append(
                            (group_name, new_group_name))
                        
                for old, new in group_name_change_list:
                    ptv_dict[new] = ptv_dict.pop(old)
                    ptv_dict[new].group_name = new
                    server.send_gui(
                        '/ray/gui/patchbay/update_group_position',
                        view_num, *ptv_dict[new].to_arg_list())                    
