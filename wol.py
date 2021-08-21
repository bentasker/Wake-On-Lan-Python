#!/usr/bin/env python3
#
# Based on wol.py from http://code.activestate.com/recipes/358449-wake-on-lan/
# Amended to use configuration file and hostnames
#
# Copyright (C) Fadly Tabrani, B Tasker
#
# Released under the PSF License See http://docs.python.org/2/license.html
#
#


import socket
import struct
import os
import sys
import configparser
import re


myconfig = {}


def wake_on_lan(host):
    """ Switches on remote computers using WOL. """
    global myconfig

    try:
      macaddress = myconfig[host]['mac']

    except:
      return False

    # Check mac address format
    found = re.fullmatch('^([A-F0-9]{2}(([:][A-F0-9]{2}){5}|([-][A-F0-9]{2}){5})|([\s][A-F0-9]{2}){5})|([a-f0-9]{2}(([:][a-f0-9]{2}){5}|([-][a-f0-9]{2}){5}|([\s][a-f0-9]{2}){5}))$', macaddress)
    #We must found 1 match , or the MAC is invalid
    if found:
	#If the match is found, remove mac separator [:-\s]
        macaddress = macaddress.replace(macaddress[2], '')
    else:
        raise ValueError('Incorrect MAC address format')

    # Pad the synchronization stream.
    data = ''.join(['FFFFFFFFFFFF', macaddress * 20])
    send_data = b''

    # Split up the hex values and pack.
    for i in range(0, len(data), 2):
        send_data = b''.join([send_data,
                             struct.pack('B', int(data[i: i + 2], 16))])

    # Broadcast it to the LAN.
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    sock.sendto(send_data, (myconfig['General']['broadcast'], 7))
    return True


def writeConfig(conf):
    """ Write configuration file to save local settings """
    global conf_path
    conf.write(open(conf_path+'/wol_config.ini', 'w'))


def loadConfig():
    """ Read in the Configuration file to get CDN specific settings """
    global conf_path
    global myconfig
    Config = configparser.ConfigParser()
    # Create conf path if does not exists
    if not os.path.exists(conf_path):
        os.makedirs(conf_path, exist_ok=True)
    # generate default config file if does not exists
    if not os.path.exists(conf_path+'/wol_config.ini'):
        # get broadcast ip dynamicly
        local_ip = socket.gethostbyname(socket.gethostname())
        local_ip = local_ip.rsplit('.', 1)
        local_ip[1] = '255'
        broadcast_ip = '.'.join(local_ip)
        # Load default values to new conf file
        Config['General'] = {'broadcast': broadcast_ip}
        # two examples for devices
        Config['myPC'] = {'mac': '00:2a:a0:cf:83:15'}
        Config['myLaptop'] = {'mac': '00:13:0d:e4:60:61'}
        writeConfig(Config)     # Generate default conf file
    Config.read(conf_path+"/wol_config.ini")
    sections = Config.sections()
    dict1 = {}
    for section in sections:
        options = Config.options(section)

        sectkey = section
        myconfig[sectkey] = {}

        for option in options:
            myconfig[sectkey][option] = Config.get(section, option)

    return myconfig     # Useful for testing

def usage():
	print('Usage: wol.py [hostname]')



if __name__ == '__main__':
        conf_path = os.path.expanduser('~/.config/bentasker.Wake-On-Lan-Python')
        conf = loadConfig()
        try:
                # Use macaddresses with any seperators.
                if sys.argv[1] == 'list':
                        print('Configured Hosts:')
                        for i in conf:
                                if i != 'General':
                                        print('\t',i)
                        print('\n')
                else:
                        if not wake_on_lan(sys.argv[1]):
                                print('Invalid Hostname specified')
                        else:
                                print('Magic packet should be winging its way')
        except:
                usage()
