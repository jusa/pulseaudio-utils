#!/usr/bin/env python3

import dbus
from dbus.types import *
import os
import sys

CORE_PATH = "/org/pulseaudio/core1"
CORE_IFACE = "org.PulseAudio.Core1"
DEVICE_IFACE = "org.PulseAudio.Core1.Device"
STREAM_RESTORE_PATH = "/org/pulseaudio/stream_restore1"
STREAM_RESTORE_IFACE = "org.PulseAudio.Ext.StreamRestore1"
MIN_VOL = 0
MAX_VOL = 65535


def print_help():
    print("Usage %s all/get/set" % sys.argv[0])
    print("")
    print("all                 - print all entries")
    print("get <name>          - print entry by name")
    print("set <name> <volume> - set volume for entry, volume limits %d - %d" % (MIN_VOL, MAX_VOL))
    print("")

def pulse_connection():
    if 'PULSE_DBUS_SERVER' in os.environ:
        address = os.environ['PULSE_DBUS_SERVER']
    else:
        bus = dbus.SessionBus()
        server_lookup = bus.get_object("org.PulseAudio1", "/org/pulseaudio/server_lookup1")
        address = server_lookup.Get("org.PulseAudio.ServerLookup1", "Address", dbus_interface="org.freedesktop.DBus.Properties")

    return dbus.connection.Connection(address)

def print_entry(conn, entry_path):
    entry = conn.get_object(object_path=entry_path)
    p = dbus.Interface(entry, dbus_interface=dbus.PROPERTIES_IFACE)
    ifentry = STREAM_RESTORE_IFACE + ".RestoreEntry"
    print("%s (%s)" % (p.Get(ifentry, "Name"), p.Get(ifentry, "Device")))
    volumes = p.Get(ifentry, "Volume")
    if len(volumes) == 0:
        print("(no volume entry)", end="")
    else:
        print("Mute: ", end="")
        if p.Get(ifentry, "Mute"):
            print("on", end="")
        else:
            print("off", end="")
    for v in volumes:
        if v[0] == 0:
            print(" Mono:", v[1], end="")
        if v[0] == 1:
            print(" Front left:", v[1], end="")
        if v[0] == 2:
            print(" Front right:", v[1], end="")
    print("")

def get_all(conn):
    proxy = conn.get_object(object_path=STREAM_RESTORE_PATH)
    prop = dbus.Interface(proxy, dbus_interface=dbus.PROPERTIES_IFACE)
    for i in prop.Get(STREAM_RESTORE_IFACE, "Entries"):
        print_entry(conn, i)

def get_by_name(conn, name):
    proxy = conn.get_object(object_path=STREAM_RESTORE_PATH)
    prop = dbus.Interface(proxy, dbus_interface=dbus.PROPERTIES_IFACE)
    iface = dbus.Interface(proxy, STREAM_RESTORE_IFACE)
    entry_path = iface.GetEntryByName(name)

    print_entry(conn, entry_path)

def set_by_name(conn, name, value):
    proxy = conn.get_object(object_path=STREAM_RESTORE_PATH)
    prop = dbus.Interface(proxy, dbus_interface=dbus.PROPERTIES_IFACE)
    iface = dbus.Interface(proxy, STREAM_RESTORE_IFACE)
    entry_path = iface.GetEntryByName(name)
    entry = conn.get_object(object_path=entry_path)
    p = dbus.Interface(entry, dbus_interface=dbus.PROPERTIES_IFACE)
    p.Set(STREAM_RESTORE_IFACE + ".RestoreEntry", "Volume", Array([(UInt32(0), UInt32(value))]))

    print_entry(conn, entry_path)


def main():
    if len(sys.argv) < 2:
        print_help()
        return

    conn = pulse_connection()

    if sys.argv[1] == "all":
        get_all(conn)
    elif sys.argv[1] == "get":
        if len(sys.argv) < 3:
            print_help()
            return
        get_by_name(conn, sys.argv[2])
    elif sys.argv[1] == "set":
        if len(sys.argv) < 4:
            print_help()
            return
        vol = int(sys.argv[3])
        if vol < MIN_VOL or vol > MAX_VOL:
            print_help()
            return
        set_by_name(conn, sys.argv[2], int(sys.argv[3]))

if __name__ == "__main__":
    main()
