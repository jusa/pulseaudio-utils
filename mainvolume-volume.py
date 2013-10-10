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
MEMBER_STEPS = "StepsUpdated"
MEMBER_HIGH_VOLUME = "NotifyHighVolume"
MEMBER_TIMER = "NotifyListeningTime"
MEMBER_CALL = "CallStatus"
MEMBERS = [ MEMBER_STEPS, MEMBER_HIGH_VOLUME, MEMBER_TIMER, MEMBER_CALL ]
MAINVOLUME_SIGNAL = MAINVOLUME_IFACE + "." + MEMBER_STEPS
MAINVOLUME_HIGH_VOLUME = MAINVOLUME_IFACE + "." + MEMBER_HIGH_VOLUME
MAINVOLUME_TIMER = MAINVOLUME_IFACE + "." + MEMBER_TIMER
MAINVOLUME_CALL = MAINVOLUME_IFACE + "." + MEMBER_CALL
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

    path = s.get_path()
    iface = s.get_interface()
    member = s.get_member()

    if path != MAINVOLUME_PATH \
            or iface != MAINVOLUME_IFACE \
            or not member in MEMBERS:
        # This code should not get executed, except when the connection dies
        # (pulseaudio exits or something), in which case we get
        # a org.freedesktop.DBus.Local.Disconnected signal.
        print "Unexpected signal:", s.get_path(), s.get_interface(), s.get_member()
        return

    if member == MEMBER_STEPS:
        # args[0] is current step count as dbus.UInt32
        # args[1] is current active step as dbus.UInt32
        step_count = args[0]
        current_step = args[1]

        # Print the new steps with fancy formatting.
        print "StepsUpdated: Step count %d current step %d" % (step_count, current_step)

    if member == MEMBER_HIGH_VOLUME:
        # args[0] is safe step as dbus.UInt32
        safe_step = args[0]

        print "NotifyHighVolume: Safe step %d" % safe_step

    if member == MEMBER_TIMER:
        # args[0] is listening time in minutes as dbus.UInt32
        listening_time = args[0]

        print "NotifyListeningTime: Time listened %d" % listening_time

    if member == MEMBER_CALL:
        # args[0] is current call status as dbus.String
        call_status = args[0]

        print "CallStatus: Current call status %s" % call_status


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
    for m in MEMBERS:
        core.ListenForSignal(MAINVOLUME_IFACE + "." + m, [MAINVOLUME_PATH], dbus_interface=CORE_IFACE)

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
