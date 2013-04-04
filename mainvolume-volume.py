#!/usr/bin/env python

import dbus
from dbus.types import *
import os
import sys

from dbus.mainloop.glib import DBusGMainLoop
import gobject

CORE_PATH = "/org/pulseaudio/core1"
CORE_IFACE = "org.PulseAudio.Core1"
DEVICE_IFACE = "org.PulseAudio.Core1.Device"
MAINVOLUME_NAME = "module-nokia-mainvolume"
MAINVOLUME_PATH = "/com/meego/mainvolume1"
MAINVOLUME_IFACE = "com.Nokia.MainVolume1"
MEMBER = "StepsUpdated"
MAINVOLUME_SIGNAL = MAINVOLUME_IFACE + "." + MEMBER
MIN_VOL = 0
MAX_VOL = 65535

def print_help():
    print "%s Usage:" % sys.argv[0]
    print "     monitor         Monitor Mainvolume step changes"
    print "     get             Get current step value"
    print "     set <VALUE>     Set new step value"
    print ""

def pulse_connection():
    if 'PULSE_DBUS_SERVER' in os.environ:
        address = os.environ['PULSE_DBUS_SERVER']
    else:
        bus = dbus.SessionBus()
        server_lookup = bus.get_object("org.PulseAudio1", "/org/pulseaudio/server_lookup1")
        address = server_lookup.Get("org.PulseAudio.ServerLookup1", "Address", dbus_interface="org.freedesktop.DBus.Properties")

    return dbus.connection.Connection(address)

def getstep():
    connection = pulse_connection()
    proxy = connection.get_object(object_path=MAINVOLUME_PATH)
    prop = dbus.Interface(proxy, dbus_interface=dbus.PROPERTIES_IFACE)
    print "StepCount", prop.Get(MAINVOLUME_IFACE, "StepCount")
    print "CurrentStep", prop.Get(MAINVOLUME_IFACE, "CurrentStep")

def setstep(stepvalue):
    connection = pulse_connection()
    proxy = connection.get_object(object_path=MAINVOLUME_PATH)
    prop = dbus.Interface(proxy, dbus_interface=dbus.PROPERTIES_IFACE)
    prop.Set(MAINVOLUME_IFACE, "CurrentStep", stepvalue)

# All D-Bus signals are handled here. The SignalMessage object is passed in
# the keyword arguments with key "msg". We expect only VolumeUpdated signals.
def signal_cb(*args, **keywords):

    s = keywords["msg"]

    if s.get_path() == MAINVOLUME_PATH \
            and s.get_interface() == MAINVOLUME_IFACE \
            and s.get_member() == MEMBER:

        # args[0] is current step count as dbus.UInt32
        # args[1] is current active step as dbus.UInt32
        step_count = args[0]
        current_step = args[1]

        # Print the new steps with fancy formatting.
        print "StepsUpdated: Step count %d current step %d" % (step_count, current_step)

    else:
        # This code should not get executed, except when the connection dies
        # (pulseaudio exits or something), in which case we get
        # a org.freedesktop.DBus.Local.Disconnected signal.
        print "Unexpected signal:", s.get_path(), s.get_interface(), s.get_member()

def monitor():
    # We integrate with the GLib main loop implementation. That's the easiest way
    # to receive D-Bus signals asynchronously in Python.
    DBusGMainLoop(set_as_default=True)

    # Connect to PulseAudio dbus
    connection = pulse_connection()

    # Register the signal callback. By default only the signal arguments are passed
    # to the callback, but by setting the message_keyword here, we also get the
    # SignalMessage object which is useful for separating different signals from
    # each other.
    connection.add_signal_receiver(signal_cb, message_keyword="msg")

    # Use the Python D-Bus bindings magic to create a proxy object for the central
    # core object of Pulseaudio.
    core = connection.get_object(object_path=CORE_PATH)

    # The server won't send us any signals unless we explicitly tell it to send
    # them. Here we tell the server that we'd like to receive the StepsUpdated
    # signals.
    core.ListenForSignal(MAINVOLUME_SIGNAL, [MAINVOLUME_PATH], dbus_interface=CORE_IFACE)

    # Run forever, waiting for the signals to come.
    loop = gobject.MainLoop()
    loop.run()

def main():
    if len(sys.argv) < 2:
        print_help()
        return

    if sys.argv[1] == "monitor":
        monitor()
    elif sys.argv[1] == "get":
        getstep()
    elif sys.argv[1] == "set":
        if len(sys.argv) < 3:
            print_help()
            return
        setstep(UInt32(sys.argv[2]))

if __name__ == "__main__":
    main()
