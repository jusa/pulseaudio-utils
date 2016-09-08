#!/usr/bin/env python

import dbus
from dbus.types import *
import os
import sys

from dbus.mainloop.glib import DBusGMainLoop
from gi.repository import GObject as gobject

CORE_PATH = "/org/pulseaudio/core1"
CORE_IFACE = "org.PulseAudio.Core1"
DEVICE_IFACE = "org.PulseAudio.Core1.Device"
MAINVOLUME_PATH = "/com/meego/mainvolume2"
MAINVOLUME_IFACE = "com.Meego.MainVolume2"
METHOD_ALL = "GetAll"
MEMBER_STEPS = "StepsUpdated"
MEMBER_HIGH_VOLUME = "NotifyHighVolume"
MEMBER_TIMER = "NotifyListeningTime"
MEMBER_CALL = "CallStatus"
MEMBERS = [ MEMBER_STEPS, MEMBER_HIGH_VOLUME, MEMBER_TIMER, MEMBER_CALL ]
MAINVOLUME_SIGNAL = MAINVOLUME_IFACE + "." + MEMBER_STEPS
MAINVOLUME_HIGH_VOLUME = MAINVOLUME_IFACE + "." + MEMBER_HIGH_VOLUME
MAINVOLUME_TIMER = MAINVOLUME_IFACE + "." + MEMBER_TIMER
MAINVOLUME_CALL = MAINVOLUME_IFACE + "." + MEMBER_CALL

CARD_IFACE = "org.PulseAudio.Core1.Card"
CARD_PATH = "/org/pulseaudio/core1/card%s"
PROFILE_IFACE = "org.PulseAudio.Core1.CardProfile"
SINK_IFACE = "org.PulseAudio.Core1.Sink"
SOURCE_IFACE= "org.PulseAudio.Core1.Source"
PORT_IFACE = "org.PulseAudio.Core1.DevicePort"

MIN_VOL = 0
MAX_VOL = 65535

def print_help():
    print "%s Usage:" % sys.argv[0]
    print "     monitor         Monitor Mainvolume step changes"
    print "     get             Get current step value"
    print "     set <VALUE>     Set new step value"
    print ""

connection_ = None

def pulse_connection():
    global connection_
    if connection_ is not None:
        return connection_

    if 'PULSE_DBUS_SERVER' in os.environ:
        address = os.environ['PULSE_DBUS_SERVER']
    else:
        bus = dbus.SessionBus()
        server_lookup = bus.get_object("org.PulseAudio1", "/org/pulseaudio/server_lookup1")
        address = server_lookup.Get("org.PulseAudio.ServerLookup1", "Address", dbus_interface="org.freedesktop.DBus.Properties")

    connection_ = dbus.connection.Connection(address)
    return connection_

def getall():
    connection = pulse_connection()
    proxy = connection.get_object(object_path=MAINVOLUME_PATH)
    prop = dbus.Interface(proxy, dbus_interface=dbus.PROPERTIES_IFACE)
    for k in prop.GetAll(MAINVOLUME_IFACE):
        print "%s: %u " % (k, prop.Get(MAINVOLUME_IFACE, k)),
    print ""

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

def get_object_prop(path):
    connection = pulse_connection()
    proxy = connection.get_object(object_path=path)
    return dbus.Interface(proxy, dbus_interface=dbus.PROPERTIES_IFACE)

def card_signal_cb(*args, **keywords):

    s = keywords["msg"]

    path = s.get_path()
    iface = s.get_interface()
    member = s.get_member()
    print iface + " ",

    if len(args) == 0:
        print "Empty args"
        return

    if iface == CORE_IFACE:
        for i in args:
            print path + " " + member + ": " + i,
            if member == "NewCard":
                print get_card_property(i, "Name")
            else:
                print ""
            update_signals()

    if iface == CARD_IFACE:
        prop = get_object_prop(args[0])
        print path + " " + member + ": " + prop.Get(PROFILE_IFACE, "Name")

    if iface == SINK_IFACE or iface == SOURCE_IFACE or iface == DEVICE_IFACE:
        prop = get_object_prop(args[0])
        print path + " " + member + ": " + prop.Get(PORT_IFACE, "Name")

def get_card_property(path, propstr):
    connection = pulse_connection()
    proxy = connection.get_object(object_path=path)
    prop = dbus.Interface(proxy, dbus_interface=dbus.PROPERTIES_IFACE)
    return prop.Get(CARD_IFACE, propstr)

def add_card(path):
    connection = pulse_connection()
    core = connection.get_object(object_path=CORE_PATH)
    print "Adding card with path " + path,
    for s in ["ActiveProfileUpdated", "NewProfile", "ProfileRemoved"]:
	    core.ListenForSignal(CARD_IFACE + "." + s, [path], dbus_interface=CORE_IFACE)
    print get_card_property(path, "Name")

def update_signals(echo=False):
    connection = pulse_connection()
    core = connection.get_object(object_path=CORE_PATH)
    prop = dbus.Interface(core, dbus_interface=dbus.PROPERTIES_IFACE)
    cards = prop.Get(CORE_IFACE, "Cards")
    for s in ["ActiveProfileUpdated", "NewProfile", "ProfileRemoved"]:
        core.ListenForSignal(CARD_IFACE + "." + s, cards, dbus_interface=CORE_IFACE)
    
    for i in cards:
        card = get_object_prop(i)
        core.ListenForSignal(DEVICE_IFACE + ".ActivePortUpdated", card.Get(CARD_IFACE, "Sinks") + card.Get(CARD_IFACE, "Sources"), dbus_interface=CORE_IFACE)
        if echo:
            print "Adding card with path " + i + " " + get_card_property(i, "Name")

def monitor_card():
    DBusGMainLoop(set_as_default=True)
    connection = pulse_connection()
    connection.add_signal_receiver(card_signal_cb, message_keyword="msg")
    core = connection.get_object(object_path=CORE_PATH)
    update_signals(True)
    for s in ["NewCard", "CardRemoved"]:
        core.ListenForSignal(CORE_IFACE + "." + s, ["/org/pulseaudio/core1"], dbus_interface=CORE_IFACE)
    loop = gobject.MainLoop()
    loop.run()

def main():
    if len(sys.argv) < 2:
        print_help()
        return

    if sys.argv[1] == "card":
        monitor_card()
        return
    if sys.argv[1] == "monitor":
        getall()
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
