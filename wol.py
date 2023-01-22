#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright (C) Fadly Tabrani, B Tasker
#
# Released under the PSF License See http://docs.python.org/2/license.html
#
#

import typing as _t

import os

import inspect
import re
import socket
import struct
import sys

from configparser import ConfigParser
from dataclasses import dataclass
from itertools import chain
from pathlib import Path


_t_config = _t.Dict[str, _t.Dict[str, str]]


@dataclass(init=False)
class WakeOnLan(object):
    """
    A self-sufficient tool allowing to send a WOL magic packet.

    Usage:
        * As a standalone program, just launch the module.
        * From other python scripts:
            WakeOnLan()(*command_line_args)
    """

    new_config_dir = '~/.config/bentasker.Wake-On-Lan-Python'
    config_file_name = 'wol_config.ini'

    def __init__(self, *extra_search_paths, prefer_local_config=False, **config):
        super(WakeOnLan, self).__init__()
        self.config: _t_config = dict(config)
        self.__conf_dir = None

        module_dir = Path(inspect.getmodule(self.__class__).__file__).parent  # should work in inherited classes, too
        if prefer_local_config:
            default_paths = (self.new_config_dir, module_dir, )
            self.new_config_dir = module_dir
        else:
            default_paths = (module_dir, self.new_config_dir, )
        self.config_search_dirs = tuple(map(
            Path,
            chain(extra_search_paths, default_paths)  # paths as args are first to override the default ones
        ))

    @property
    def config_dir(self) -> Path:
        """
        On first call, detect and remember the config folder:
            * Find the first dir from `config_search_paths` that has the config file;
            * If none of them have one, use the default path from settings.
        """
        if self.__conf_dir:
            return self.__conf_dir

        found = None
        for conf_dir in self.config_search_dirs:
            assert isinstance(conf_dir, Path), f'Not a <Path> object: {conf_dir}'
            conf_dir = conf_dir.expanduser().absolute()
            if not conf_dir.is_dir():
                continue
            config_path = conf_dir / self.config_file_name
            if not config_path.is_file():
                continue

            try:
                with config_path.open('rt') as f:
                    _ = f.read(3)
                found = conf_dir
                break
            except OSError:
                continue

        self.__conf_dir = found if found else Path(self.new_config_dir).expanduser().absolute()
        return self.__conf_dir

    def wake_on_lan(self, host) -> bool:
        """Switches on remote computers using WOL."""
        config = self.config

        if host not in config:
            # Whilst it'd be nice to convert this to an exception
            # it's prob better to maintain b/c and avoid breaking
            # any existing wrappers
            return False
        
        if 'mac' not in config[host]:
            raise ValueError("MAC address not specified in config")

        mac_address = config[host]['mac']
        
        # Check mac address format
        found = re.fullmatch(
            '^([A-F0-9]{2}(([:][A-F0-9]{2}){5}|([-][A-F0-9]{2}){5})|([s][A-F0-9]{2}){5})|([a-f0-9]{2}(([:][a-f0-9]{2}){'
            '5}|([-][a-f0-9]{2}){5}|([s][a-f0-9]{2}){5}))$',
            mac_address)

        # We must found 1 match , or the MAC is invalid
        if found:
            # If the match is found, remove mac separator [:-\s]
            mac_address = mac_address.replace(mac_address[2], '')
        else:
            raise ValueError('Incorrect MAC address format')

        # Pad the synchronization stream.
        data = ''.join(['FFFFFFFFFFFF', mac_address * 20])
        send_data = b''

        # Split up the hex values and pack.
        for j in range(0, len(data), 2):
            send_data = b''.join([
                send_data,
                struct.pack('B', int(data[j: j + 2], 16))
            ])

        # Broadcast it to the LAN.
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.sendto(send_data, (config['General']['broadcast'], 7))
        return True

    def write_config(self, config_parser: ConfigParser) -> None:
        """Write configuration file to save local settings."""
        with (self.config_dir / self.config_file_name).open('w') as f:
            config_parser.write(f)

    def __get_config_parser(self, config_path: Path) -> ConfigParser:
        """Return a config parser (generate a default config file if it does not exist)"""
        config_parser = ConfigParser()

        if config_path.exists():
            return config_parser

        # Get broadcast ip dynamically
        local_ip = socket.gethostbyname(socket.gethostname())
        local_ip = local_ip.rsplit('.', 1)
        local_ip[1] = '255'
        broadcast_ip = '.'.join(local_ip)

        # Load default values to new config file
        config_parser['General'] = {'broadcast': broadcast_ip}

        # Two examples for devices
        config_parser['myPC'] = {'mac': '00:2a:a0:cf:83:15'}
        config_parser['myLaptop'] = {'mac': '00:13:0d:e4:60:61'}

        # Generate default config file
        self.write_config(config_parser)
        return config_parser

    def load_config(self) -> _t_config:
        """Read in the Configuration file to get CDN specific settings."""
        config_dir = self.config_dir
        config_path = config_dir / self.config_file_name
        config = self.config

        # Create config path if does not exists
        if not config_dir.exists():
            config_dir.mkdir(parents=True, exist_ok=True)

        config_parser = self.__get_config_parser(config_path)
        config_parser.read(str(config_path))
        sections = config_parser.sections()
        for section in sections:
            options = config_parser.options(section)

            sect_key = section
            config[sect_key] = {}

            for option in options:
                config[sect_key][option] = config_parser.get(section, option)

        return config  # Useful for testing

    @staticmethod
    def usage() -> None:
        print(
            'Usage: wol.py [-p] [hostname|list]\n'
            '\n'
            '-h            Print this text\n\n'
            '-p            Prompt for input before exiting\n'
            'list          List configured hosts\n'
            '[hostname]    hostname to wake (as listed in list)\n'
            '\n'
        )

    def __call__(self, *sys_args: str, load_config_from_file=True) -> None:
        
        # Allow the environment to override config dir location
        env_config_dir = os.getenv("WOL_CONFIG_DIR", False)
        if env_config_dir:
            # Convert to an absolute path
            self.__conf_dir = Path(env_config_dir).expanduser().absolute()
        
        config = self.load_config() if load_config_from_file else self.config

        if "-h" in sys_args or "--help" in sys_args:
            self.usage()
            return

        prompt = ("-p" in sys_args)
        try:
            arg = sys_args[-1]
            # Use MAC addresses with any separators.
            if arg == 'list':
                print('Configured Hosts:')
                for i in config:
                    if i != 'General':
                        mac = "Err: no mac configured"
                        if 'mac' in config[i]:
                            mac = config[i]['mac']
                        print('\t', i, '({})'.format(mac))
                print('\n')
            else:
                try:
                    if not self.wake_on_lan(arg):
                        print('Invalid Hostname specified')
                    else:
                        print(f'Magic packet should be winging its way to: {arg}')
                except Exception as e:
                    print(e)
        except IndexError:
            self.usage()

        finally:
            if prompt:
                input('Press ENTER to continue...')


if __name__ == '__main__':
    WakeOnLan()(*sys.argv)
