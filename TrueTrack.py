# TrueTrack, 23.10  build

import json, threading, time, paho.mqtt.client as mqtt
from os import system
from math import *
from datetime import datetime
import platform

start_time = datetime.now()
vehicles = {}
broker = "mqtt.hsl.fi"
port = 1883
topic = "/hfp/v2/journey/ongoing/vp/metro/#"
distance = 0
with open('metro_coords.json', 'r') as file:
    coords = json.load(file)
coordinates = {tuple(coordinate): tuple(values) for coordinate, values in coords}
destinations = {
    ("M1", 1): "VS",
    ("M1", 2): "       KIL",
    ("M2", 1): "  MM",
    ("M2", 2): "    TAP",
}

##############################################
##############################################

def debug(*args):
    for arg in args:
        print(f"{nameof(arg)}: {arg}", end="")

def sync_friends():
    filtered_vehicles = {k: v for k, v in vehicles.items() if int(k) < 300}
    for vehicle_number, [current, next, eta, track, dest] in filtered_vehicles.items():
        for other_vehicle_number, [other_current, other_next, other_eta, other_track, other_dest] in filtered_vehicles.items():
            if other_vehicle_number != vehicle_number:
                if track == other_track:
                    if current == other_current or current == other_next or next == other_current:
                        first = None
                        eta = 0 if eta == "" else int(eta)
                        other_eta = 0 if other_eta == "" else int(other_eta)
                        if eta < other_eta:
                            vehicles[other_vehicle_number] = current, next, eta, track, dest
                        else:
                            vehicles[vehicle_number] = other_current, other_next, other_eta, other_track, other_dest

def eta_maker(pos):
    try:
        pos = int(pos)
        eta = int(ceil(pos * 0.75))+1
    except ValueError:
        eta = ""
    return str(eta)

def print_maker(vehicle_number, station, next, eta, destination):
    eta = 0 if eta == "" else eta
    eta = int(eta)-1
    eta = str(eta)
    if eta == "0":
        eta = ""
    eta_print = "~" + eta
    if next != "" and eta != "":
        print(f" {vehicle_number:<4}| {station:>4} -> {next:<4} {eta_print:>4}s | {destination}")
    elif next != "":
        print(f" {vehicle_number:<3} | {station:>4} -> {next:<4}     | {destination}")
    else:
        print(f" {vehicle_number:<3} | {station:>4}               | {destination}")
    
    track = station[-1] if station.endswith("1") or station.endswith("2") else ""
    vehicles[vehicle_number] = station, next, eta, track, destination 

def print_vehicle_table():
    sync_friends()
    my_keys = sorted(vehicles.keys())
    sorted_vehicles = {key: vehicles[key] for key in my_keys}
    
    if platform.system() == "Linux":
        system('clear')
    runtime = datetime.now() - start_time
    runtime_seconds = int(runtime.total_seconds())
    print(f" Runtime {runtime_seconds}s")
    print(" Car |  Now -> Next   ETA | Destination")
    print(" ----|--------------------|------------")

    global vs, mm, tap, kil
    vs = mm = tap = kil = 0
    
    
    for vehicle_number, vehicle_info in sorted_vehicles.items():
        station, next, eta, track, destination = vehicle_info
        print_maker(vehicle_number, station, next, eta, destination)

        stock = 0.5 if int(str(vehicle_number)[:3]) < 300 else 1
        if destination in ["VS", "  MM", "    TAP", "       KIL"]:
            globals()[{'VS': 'vs', '  MM': 'mm', '    TAP': 'tap', '       KIL': 'kil'}[destination]] += stock

    print(" ----|--------------------|------------")
    total = ceil(vs + mm + tap + kil)
    o = float(mm+tap) 
    p = float(vs+kil) 
    o = str(ceil(o)) if o.is_integer() else str(o)
    p = str(ceil(p)) if p.is_integer() else str(p) 
    m2_count = o + "xM2"
    m1_count = p + "xM1"
    print(f" {total:<4}| {m1_count:<7}    {m2_count:>7} |{ceil(vs):<2} {ceil(mm):<2} {ceil(tap):<2} {ceil(kil):<2}")

def update_vehicle_table():
    while True:
        print_vehicle_table()
        time.sleep(1)

def on_message(client, userdata, message):
    data = json.loads(message.payload.decode())
    vehicle_number = data.get('VP', {}).get('veh', 'Unknown')
    latitude = data.get('VP', {}).get('lat', 'Unknown')
    longitude = data.get('VP', {}).get('long', 'Unknown')
    line = data.get('VP', {}).get('desi', 'Unknown')

    if (latitude, longitude) in coordinates:
        current, next, track, pos = coordinates[(latitude, longitude)]
        eta = eta_maker(pos)
        dest_key = (line, int(track))
        destination = destinations.get(dest_key, "")

        if current == "Pre-IK":
            current = "PT" if line == "M1" else "MP" if line == "M2" else ""

        if not current in ["KILK", "TAPG", "MV", "VSG", "MMG", ""]:
            current = current + track
        if not next in ["KILK", "TAPG", "MV", "VSG", "MMG", ""]:
            next = next + track

        if len(current) == 2:
            current = " " + current

        vehicles[vehicle_number] = current, next, eta, track, destination
        if vehicle_number == 203:
            vehicles[219] = current, next, eta, track, destination


# Set up MQTT client
client = mqtt.Client()
client.on_message = on_message
client.connect(broker, port)
client.subscribe(topic)
threading.Thread(target=update_vehicle_table, daemon=True).start()
client.loop_start()
stop_event = threading.Event()
try:
    stop_event.wait()
except KeyboardInterrupt:
    client.loop_stop()
    client.disconnect()