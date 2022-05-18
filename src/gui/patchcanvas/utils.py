#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# PatchBay Canvas engine using QGraphicsView/Scene
# Copyright (C) 2010-2019 Filipe Coelho <falktx@falktx.com>
# Copyright (C) 2019-2022 Mathieu Picot <picotmathieu@gmail.com>
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation; either version 2 of
# the License, or any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# For a full copy of the GNU General Public License see the doc/GPL.txt file.

# ------------------------------------------------------------------------------------------------------------
# Imports (Global)

import logging

from PyQt5.QtCore import QPointF, QFile, QRectF
from PyQt5.QtGui import QIcon, QPalette
from PyQt5.QtWidgets import QWidget

# ------------------------------------------------------------------------------------------------------------
# Imports (Custom)

from .init_values import (
    CanvasItemType,
    canvas,
    IconType,
    PortMode,
    ConnectionObject,
    CallbackAct)

# ------------------------------------------------------------------------------------------------------------

_LOGGER = logging.getLogger(__name__)
_LOGGING_STR = ''

# decorator
def easy_log(func):
    ''' decorator for API callable functions.
        It makes debug logs and also a global logging string
        usable directly in the functions'''
    def wrapper(*args, **kwargs):
        args_strs = [str(arg) for arg in args]
        args_strs += [f"{k}={v}" for k, v in kwargs.items()]

        global _LOGGING_STR
        _LOGGING_STR = f"{func.__name__}({', '.join(args_strs)})"
        _LOGGER.debug(_LOGGING_STR)
        return func(*args, **kwargs)
    return wrapper

def get_new_group_positions()->tuple:
    def get_middle_empty_positions(scene_rect: QRectF)->tuple:
        if scene_rect.isNull():
            return ((0, 200))

        needed_x = 120
        needed_y = 120
        margin_x = 50
        margin_y = 10

        x = scene_rect.center().x() - needed_y / 2
        y = scene_rect.top() + 20

        y_list = []

        min_top = scene_rect.bottom()
        max_bottom = scene_rect.top()

        for group in canvas.group_list:
            for widget in group.widgets:
                if widget is None:
                    continue

                box_rect = widget.sceneBoundingRect()
                min_top = min(min_top, box_rect.top())
                max_bottom = max(max_bottom, box_rect.bottom())

                if box_rect.left() - needed_x <= x <= box_rect.right() + margin_x:
                    y_list.append(
                        (box_rect.top(), box_rect.bottom(), box_rect.left()))

        if not y_list:
            return (int(x), int(y))

        y_list.sort()
        available_segments = [[min_top, max_bottom, x]]

        for box_top, box_bottom, box_left in y_list:
            for segment in available_segments:
                seg_top, seg_bottom, seg_left = segment

                if box_bottom <= seg_top or box_top >= seg_bottom:
                    continue

                if box_top <= seg_top and box_bottom >= seg_bottom:
                    available_segments.remove(segment)
                    break

                if box_top > seg_top:
                    segment[1] = box_top
                    if box_bottom < seg_bottom:
                        available_segments.insert(
                            available_segments.index(segment) + 1,
                            [box_bottom, seg_bottom, box_left])
                        break

                segment[0] = box_bottom

        if not available_segments:
            return (int(x), int(max_bottom + margin_y))

        available_segments.sort()

        for seg_top, seg_bottom, seg_left in available_segments:
            if seg_bottom - seg_top >= 200:
                y = seg_top + margin_y
                x = seg_left
                break
        else:
            y = max_bottom + margin_y

        return (int(x), int(y))

    rect = canvas.scene.get_new_scene_rect()
    if rect.isNull():
        return ((200, 0), (400, 0), (0, 0))

    y = rect.bottom()

    return (get_middle_empty_positions(rect),
            (400, int(y)),
            (0, int(y)))

@easy_log
def get_new_group_pos(horizontal: bool):
    new_pos = QPointF(canvas.initial_pos)
    items = canvas.scene.items()

    break_loop = False
    while not break_loop:
        break_for = False
        for i, item in enumerate(items):
            if item and item.type() is CanvasItemType.BOX:
                if item.sceneBoundingRect().contains(new_pos):
                    if horizontal:
                        new_pos += QPointF(item.boundingRect().width() + 15, 0)
                    else:
                        new_pos += QPointF(0, item.boundingRect().height() + 15)
                    break_for = True
                    break

            if i >= len(items) - 1 and not break_for:
                break_loop = True

    return new_pos

@easy_log
def get_full_port_name(group_id: int, port_id: int) -> str:
    for port in canvas.port_list:
        if port.group_id == group_id and port.port_id == port_id:
            group_id = port.group_id
            for group in canvas.group_list:
                if group.group_id == group_id:
                    return group.group_name + ":" + port.port_name
            break
    
    _LOGGER.critical(f"{_LOGGING_STR} - unable to find port")
    return ""

@easy_log
def get_port_connection_list(group_id: int, port_id: int) -> list:
    conn_list = []

    for connection in canvas.connection_list:
        if (connection.group_out_id == group_id
                and connection.port_out_id == port_id):
            conn_list.append((connection.connection_id,
                              connection.group_in_id,
                              connection.port_in_id))
        elif (connection.group_in_id == group_id
                and connection.port_in_id == port_id):
            conn_list.append((connection.connection_id,
                              connection.group_out_id,
                              connection.port_out_id))

    return conn_list

def get_portgroup_position(group_id: int, port_id: int,
                           portgrp_id: int) -> tuple:
    if portgrp_id <= 0:
        return (0, 1)

    for portgrp in canvas.portgrp_list:
        if (portgrp.group_id == group_id
                and portgrp.portgrp_id == portgrp_id):
            for i in range(len(portgrp.port_id_list)):
                if port_id == portgrp.port_id_list[i]:
                    return (i, len(portgrp.port_id_list))
    return (0, 1)

def get_portgroup_name_from_ports_names(ports_names: list[str]):
    if len(ports_names) < 2:
        return ''

    portgrp_name_ends = (' ', '_', '.', '-', '#', ':', 'out', 'in', 'Out',
                         'In', 'Output', 'Input', 'output', 'input')

    # set portgrp name
    portgrp_name = ''

    for c in ports_names[0]:
        for eachname in ports_names:
            if not eachname.startswith(portgrp_name + c):
                break
        else:
            portgrp_name += c

    # reduce portgrp name until it ends with one of the characters
    # in portgrp_name_ends
    if not portgrp_name.endswith((' AUX', '_AUX')):
        check = False
        while not check:
            for x in portgrp_name_ends:
                if portgrp_name.endswith(x):
                    check = True
                    break

            if len(portgrp_name) == 0 or portgrp_name in ports_names:
                check = True

            if not check:
                portgrp_name = portgrp_name[:-1]
    
    return portgrp_name

def get_portgroup_name(group_id: int, ports_ids_list: list) -> str:
    # accept portgrp_id instead of ports_ids_list as second argument
    if isinstance(ports_ids_list, int):
        for portgrp in canvas.portgrp_list:
            if (portgrp.group_id == group_id
                    and portgrp.portgrp_id == ports_ids_list):
                ports_ids_list = portgrp.port_id_list
                break
    
    ports_names = []

    for port in canvas.port_list:
        if port.group_id == group_id and port.port_id in ports_ids_list:
            ports_names.append(port.port_name)

    return get_portgroup_name_from_ports_names(ports_names)

def get_port_print_name(group_id: int, port_id: int, portgrp_id: int) -> str:
    for portgrp in canvas.portgrp_list:
        if (portgrp.group_id == group_id
                and portgrp.portgrp_id == portgrp_id):
            portgrp_name = get_portgroup_name(
                group_id, portgrp.port_id_list)

            for port in canvas.port_list:
                if port.group_id == group_id and port.port_id == port_id:
                    return port.port_name.replace(portgrp_name, '', 1)

def get_portgroup_port_list(group_id: int, portgrp_id: int)->list:
    for portgrp in canvas.portgrp_list:
        if (portgrp.group_id == group_id
                and portgrp.portgrp_id == portgrp_id):
            return portgrp.port_id_list
    return []

def get_portgroup_full_name(group_id: int, portgrp_id: int) -> str:
    for portgrp in canvas.portgrp_list:
        if (portgrp.group_id == group_id
                and portgrp.portgrp_id == portgrp_id):
            group_name = ""
            for group in canvas.group_list:
                if group.group_id == group_id:
                    group_name = group.group_name
                    break
            else:
                return ""

            endofname = ''
            for port_id in portgrp.port_id_list:
                endofname += "%s/" % get_port_print_name(
                    group_id, port_id, portgrp.portgrp_id)
            portgrp_name = get_portgroup_name(
                group_id, portgrp.port_id_list)

            return "%s:%s %s" % (group_name, portgrp_name, endofname[:-1])

    return ""

def connection_matches(connection: ConnectionObject,
                       group_id_1: int, port_ids_list_1: list[int],
                       group_id_2: int, port_ids_list_2: list[int]) -> bool:
    if (connection.group_in_id == group_id_1
        and connection.port_in_id in port_ids_list_1
        and connection.group_out_id == group_id_2
        and connection.port_out_id in port_ids_list_2):
            return True
    elif (connection.group_in_id == group_id_2
          and connection.port_in_id in port_ids_list_2
          and connection.group_out_id == group_id_1
          and connection.port_out_id in port_ids_list_1):
            return True
    else:
        return False

def connection_concerns(connection: ConnectionObject,
                        group_id: int, port_ids_list: list[int]) -> bool:
    if (connection.group_in_id == group_id
            and connection.port_in_id in port_ids_list):
        return True
    elif (connection.group_out_id == group_id
          and connection.port_out_id in port_ids_list):
        return True
    else:
        return False

def get_group_icon(group_id: int, port_mode: int) -> QIcon:
    # port_mode is here reversed
    group_port_mode = PortMode.INPUT
    if port_mode is PortMode.INPUT:
        group_port_mode = PortMode.OUTPUT

    for group in canvas.group_list:
        if group.group_id == group_id:
            if not group.split:
                group_port_mode = PortMode.NULL

            return get_icon(
                group.icon_type, group.icon_name, group_port_mode)

    return QIcon()

def get_icon(icon_type: int, icon_name: str, port_mode: int) -> QIcon:
    if icon_type in (IconType.CLIENT, IconType.APPLICATION):
        icon = QIcon.fromTheme(icon_name)

        if icon.isNull():
            for ext in ('svg', 'svgz', 'png'):
                filename = ":app_icons/%s.%s" % (icon_name, ext)

                if QFile.exists(filename):
                    del icon
                    icon = QIcon()
                    icon.addFile(filename)
                    break
        return icon

    icon = QIcon()

    if icon_type == IconType.HARDWARE:
        icon_file = ":/scalable/pb_hardware.svg"

        if icon_name == "a2j":
            icon_file = ":/scalable/DIN-5.svg"
        elif port_mode is PortMode.INPUT:
            icon_file = ":/scalable/audio-headphones.svg"
        elif port_mode is PortMode.OUTPUT:
            icon_file = ":/scalable/microphone.svg"

        icon.addFile(icon_file)

    elif icon_type == IconType.INTERNAL:
        icon.addFile(":/scalable/%s" % icon_name)

    return icon

@easy_log
def connect_ports(group_id_1: int, port_id_1: int,
                  group_id_2: int, port_id_2:int):
    one_is_out = True

    for port in canvas.port_list:
        if port.group_id == group_id_1 and port.port_id == port_id_1:
            if port.port_mode is not PortMode.OUTPUT:
                one_is_out = False
            break
        elif port.group_id == group_id_2 and port.port_id == port_id_2:
            if port.port_mode is PortMode.OUTPUT:
                one_is_out = False
            break
    else:
        _LOGGER.critical(f"{_LOGGING_STR} - one port at least not found")
        return

    if one_is_out:
        canvas.callback(CallbackAct.PORTS_CONNECT,
                        group_id_1, port_id_1,
                        group_id_2, port_id_2)
    else:
        canvas.callback(CallbackAct.PORTS_CONNECT,
                        group_id_2, port_id_2,
                        group_id_1, port_id_1)

def get_portgroup_connection_state(group_id_1: int, port_id_list_1: list,
                                   group_id_2: int, port_id_list_2: list) -> int:
    # returns
    # 0 if no connection
    # 1 if connection is irregular
    # 2 if connection is correct

    group_out_id = 0
    group_in_id = 0
    out_port_id_list = []
    in_port_id_list = []

    for port in canvas.port_list:
        if (port.group_id == group_id_1
                and port.port_id in port_id_list_1):
            if port.port_mode is PortMode.OUTPUT:
                out_port_id_list = port_id_list_1
                group_out_id = group_id_1
            else:
                in_port_id_list = port_id_list_1
                group_in_id = group_id_1
        elif (port.group_id == group_id_2
                and port.port_id in port_id_list_2):
            if port.port_mode is PortMode.OUTPUT:
                out_port_id_list = port_id_list_2
                group_out_id = group_id_2
            else:
                in_port_id_list = port_id_list_2
                group_in_id = group_id_2

    if not (out_port_id_list and in_port_id_list):
        return 0

    has_connection = False
    miss_connection = False

    for out_index in range(len(out_port_id_list)):
        for in_index in range(len(in_port_id_list)):
            if (out_index % len(in_port_id_list)
                    == in_index % len(out_port_id_list)):
                for connection in canvas.connection_list:
                    if (connection.group_out_id == group_out_id
                            and connection.port_out_id == out_port_id_list[out_index]
                            and connection.group_in_id == group_in_id
                            and connection.port_in_id == in_port_id_list[in_index]):
                        has_connection = True
                        break
                else:
                    miss_connection = True
            else:
                for connection in canvas.connection_list:
                    if (connection.group_out_id == group_out_id
                            and connection.port_out_id == out_port_id_list[out_index]
                            and connection.group_in_id == group_in_id
                            and connection.port_in_id == in_port_id_list[in_index]):
                        # irregular connection exists
                        # we are sure connection is irregular
                        return 1

    if has_connection:
        if miss_connection:
            return 1
        else:
            return 2
    else:
        return 0

@easy_log
def connect_portgroups(group_id_1: int, portgrp_id_1: int,
                       group_id_2: int, portgrp_id_2: int,
                       disconnect=False):
    group_out_id = 0
    group_in_id = 0
    out_port_id_list = []
    in_port_id_list = []

    for portgrp in canvas.portgrp_list:
        if (portgrp.group_id == group_id_1
                and portgrp.portgrp_id == portgrp_id_1):
            if portgrp.port_mode is PortMode.OUTPUT:
                group_out_id = group_id_1
                out_port_id_list = portgrp.port_id_list
            else:
                group_in_id = group_id_1
                in_port_id_list = portgrp.port_id_list

        elif (portgrp.group_id == group_id_2
                and portgrp.portgrp_id == portgrp_id_2):
            if portgrp.port_mode is PortMode.OUTPUT:
                group_out_id = group_id_2
                out_port_id_list = portgrp.port_id_list
            else:
                group_in_id = group_id_2
                in_port_id_list = portgrp.port_id_list

    if not (out_port_id_list and in_port_id_list):
        _LOGGER.warning(f"{_LOGGING_STR} - empty port id list")
        return

    connected_indexes = []

    # disconnect irregular connections
    for connection in canvas.connection_list:
        if (connection.group_out_id == group_out_id
                and connection.port_out_id in out_port_id_list
                and connection.group_in_id == group_in_id
                and connection.port_in_id in in_port_id_list):
            out_index = out_port_id_list.index(connection.port_out_id)
            in_index = in_port_id_list.index(connection.port_in_id)

            if (out_index % len(in_port_id_list)
                    == in_index % len(out_port_id_list)
                    and not disconnect):
                # remember this connection already exists
                # and has not to be remade
                connected_indexes.append((out_index, in_index))
            else:
                canvas.callback(CallbackAct.PORTS_DISCONNECT,
                                connection.connection_id)

    if disconnect:
        return

    # finally connect the ports
    for out_index in range(len(out_port_id_list)):
        for in_index in range(len(in_port_id_list)):
            if (out_index % len(in_port_id_list)
                        == in_index % len(out_port_id_list)
                    and (out_index, in_index) not in connected_indexes):
                canvas.callback(
                    CallbackAct.PORTS_CONNECT,
                    group_out_id, out_port_id_list[out_index],
                    group_in_id, in_port_id_list[in_index])

@easy_log
def canvas_callback(action: CallbackAct, *args):
    canvas.callback(action, *args)

def is_dark_theme(widget: QWidget) -> bool:
    return bool(
        widget.palette().brush(QPalette.Active,
                               QPalette.WindowText).color().lightness()
        > 128)