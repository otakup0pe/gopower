#!/usr/bin/env python3
"""
The gopower_cli module / command allows minimal interaction with Go Power
brand solar charge controllers that have bluetooth. This tool is currently
limited to polling some stats and writing them out as a text file that
is compatible with the Prometheus node exporter.
"""

import argparse
import os
import signal
import subprocess
import sys

from bluepy import btle
from bluepy.btle import Peripheral, BTLEDisconnectError

PROM=os.environ.get('GOPOWER_PROMFILE', '/var/run/promnode/textfiles/gopower.prom')
GP_NOT_CHAR = "0000fff1-0000-1000-8000-00805f9b34fb"
GP_INT_CHAR = "0000fff2-0000-1000-8000-00805f9b34fb"

def get_addr(args):
    if not args['addr']:
        if 'GOPOWER_ADDR' not in os.environ:
            raise ValueError('Unable to determine GoPower addr')

        return os.environ['GOPOWER_ADDR']

    return args['addr']

def cleanup(cli_args, controller):
    """
    Session Cleanup

    Attempt to cleanup and write prometheus text file if needed
    """
    def actual_cleanup(*args):
        if controller:
            controller.disconnect()

        if cli_args['action'] == 'prom':
            prom_write()

    return actual_cleanup

def prom_write(delegate = None):
    with open(PROM, 'w') as prom_h:
        if delegate:
            prom_h.write("# HELP gopower_status whether or not bluetooth connection was succesful\n")
            prom_h.write("# TYPE gopower_status gauge\n")
            prom_h.write("gopower_status{location=\"trailer\"} 1\n")
            prom_h.write("# HELP gopower_voltage voltage reported by gopower device\n")
            prom_h.write("# TYPE gopower_voltage gauge\n")
            prom_h.write("gopower_voltage{location=\"trailer\"} %s\n" % delegate.voltage)
            prom_h.write("# HELP gopower_amp_hours retrieved amp hour value that may roll over\n")
            prom_h.write("# TYPE gopower_amp_hours counter\n")
            prom_h.write("gopower_amp_hours{location=\"trailer\"} %s\n" % delegate.amp_hours)
            prom_h.write("# HELP gopower_sunbeams amps in from fighting the sun\n")
            prom_h.write("# TYPE gopower_sunbeams gauge\n")
            prom_h.write("gopower_sunbeams{location=\"trailer\"} %s\n" % delegate.sunbeams)
            prom_h.write("# HELP gopower_battery battery level as percentage\n")
            prom_h.write("# TYPE gopower_battery gauge\n")
            prom_h.write("gopower_battery{location=\"trailer\"} %s\n" % delegate.battery)
        else:
            prom_h.write("# HELP gopower_status whether or not bluetooth connection was succesful\n")
            prom_h.write("# TYPE gopower_status gauge\n")
            prom_h.write("gopower_voltage{location=\"trailer\"} 0\n")


class GPDelegate(btle.DefaultDelegate):

    def __init__(self):
        self.voltage = 0
        self.amp_hours = 0
        self.sunbeams = 0
        self.battery = 0
        self.buff = None
        btle.DefaultDelegate.__init__(self)

    def handleNotification(self, handle, data):
        if self.buff:

            self.buff += data.decode('ascii')
        else:
            self.buff = data.decode('ascii')

        if self.buff[-2:] == '\r\n':
            data_bits = self.buff.split(';')
            self.voltage = float(f"{data_bits[10][0:2]}.{data_bits[10][2:4]}")
            self.amp_hours = int(data_bits[28])
            self.sunbeams = float(f"{data_bits[0][0:4]}.{data_bits[0][4:1]}")
            self.battery = int(data_bits[12])

            self.buff = None


def poll_stats(addr, controller):
    try:
        controller = Peripheral(addr)
    except BTLEDisconnectError:
        result = subprocess.run(["/usr/bin/bluetoothctl", "disconnect", addr], capture_output=True)
        if result.returncode != 0:
            sys.stderr.write('BT Connection error\n')
            sys.exit(1)

        if b'disconnected' not in result.stdout:
            sys.stderr.write('BT Force Disconnect error\n')
            sys.exit(1)

    if not controller:
        try:
            controller = Peripheral(addr)
        except BTLEDisconnectError:
            sys.stderr.write('BT Re-Connection error\n')
            sys.exit(1)

    delegate = GPDelegate()
    controller.setDelegate(delegate)

    notify_svc_bits = [x for x in controller.getCharacteristics() if x.uuid == GP_NOT_CHAR]
    notify_desc = notify_svc_bits[0].getDescriptors()[0]

    intent_svc_bits = [x for x in controller.getCharacteristics() if x.uuid == GP_INT_CHAR]
    intent_char = intent_svc_bits[0]

    notify_desc.write(b"\x01\x00")
    intent_char.write(b"\x20\x00")

    while delegate.voltage == 0 and delegate.amp_hours == 0:
        if controller.waitForNotifications(0.1):
            continue

    return delegate

def addr_arg(parser):
    parser.add_argument('--addr', '-a',
                        help='Specify BLE address to connect with.'
                        ' Overrides GOPOWER_ADDR env var')

def entrypoint():
    controller = None

    parser = argparse.ArgumentParser(usage='usage goes here',
                                     description='Go Power CLI')
    subparsers = parser.add_subparsers(dest='action',
                                       help='Specify Go Power CLI action to take')
    stats_parser = subparsers.add_parser('stats',
                                         help='Show stats in terminal')
    addr_arg(stats_parser)
    promtext_parser = subparsers.add_parser('prom',
                                            help='Write stats to Prometheus text file')
    addr_arg(promtext_parser)

    args = vars(parser.parse_args())
    signal.signal(signal.SIGTERM, cleanup(args, controller))
    signal.signal(signal.SIGINT, cleanup(args, controller))

    if args['action'] == 'stats':
        delegate = poll_stats(get_addr(args), controller)
        print(f"Voltage: {delegate.voltage}v ({delegate.battery}%)")
        print(f"Sunbeams: {delegate.sunbeams}A")
        print(f"Amp Hours: {delegate.amp_hours}Ah")
    elif args['action'] == 'prom':
        prom_write(poll_stats(get_addr(args), controller))
    else:
        parser.print_help()
        sys.exit(1)

if __name__ == '__main__':
    entrypoint()
