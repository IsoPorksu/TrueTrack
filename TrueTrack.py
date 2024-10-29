# TrueTrack v5
import json, threading, time, paho.mqtt.client as mqtt
from os import system
from math import *
from datetime import datetime
import platform
from varname import nameof

start_time = datetime.now()
vehicles = {}
friends = {}
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

def debug(*args):
    for arg in args:
        print(f"{nameof(arg)}: {arg}", end="")
        
def check_friends(filtered_vehicles):
    for vehicle_number, [current, next, eta, track, dest, speed] in filtered_vehicles.items():
        for other_vehicle_number, [other_current, other_next, other_eta, other_track, other_dest, other_speed] in filtered_vehicles.items():
            if other_vehicle_number != vehicle_number:
                if track == other_track:
                    if current == other_current or (current == other_next and next == "") or (next == other_current and other_next == ""):
                        eta = 0 if eta == "" else int(eta)
                        other_eta = 0 if other_eta == "" else int(other_eta)
                        if eta < other_eta:
                            vehicles[other_vehicle_number] = current, next, eta, track, dest, speed
                            friends[other_vehicle_number] = vehicle_number
                            friends[vehicle_number] = other_vehicle_number
                        else:
                            vehicles[vehicle_number] = other_current, other_next, other_eta, other_track, other_dest, other_speed
                            friends[other_vehicle_number] = vehicle_number
                            friends[vehicle_number] = other_vehicle_number

def sync_friends():
    filtered_vehicles = {k: v for k, v in vehicles.items() if int(k) < 200}
    check_friends(filtered_vehicles)
    filtered_vehicles = {k: v for k, v in vehicles.items() if 200 < int(k) < 300}
    check_friends(filtered_vehicles) 

def eta_maker(pos):
    try:
        pos = int(pos)
        eta = int(ceil(pos * 0.75))+1
    except ValueError:
        eta = ""
    return str(eta)

def print_maker(car, station, next, eta, destination, speed):
    if next != "" and eta != "":
        print(f" {car:<4}| {station:>4} -> {next:<4} {eta:>4}s | {destination:<11} |", end = "")
    elif next != "":
        print(f" {car:<4}| {station:>4} -> {next:<4}     | {destination:<11} |", end = "")
    else:
        print(f" {car:<4}| {station:>4}               | {destination:<11} |", end = "")
    if car in friends:
        friend = friends[car]
        if speed != 0:
            print(f" {friend:<4}| {speed:>2}km/h")
        else:
            print(f" {friend:<4}|")
    elif speed != 0:
        print(f"     | {speed:>2}km/h")
    else:
        print(f"     |")
    track = station[-1] if station.endswith("1") or station.endswith("2") else ""
    vehicles[car] = station, next, eta, track, destination, speed

def print_vehicle_table():
    sync_friends()
    my_keys = sorted(vehicles.keys())
    sorted_vehicles = {key: vehicles[key] for key in my_keys}
    
    if platform.system() == "Linux":
        system('clear')
    runtime = datetime.now() - start_time
    runtime_seconds = int(runtime.total_seconds())
    print(f" Runtime {runtime_seconds}s")
    print(" Car |  Now -> Next   ETA | Destination |Car 2| Speed")
    print(" ----|--------------------|-------------|-----|-------")
    global vs, mm, tap, kil
    vs = mm = tap = kil = 0
    
    for vehicle_number, [station, next, eta, track, destination, speed] in sorted_vehicles.items():
        eta = 0 if eta == "" else eta
        eta = int(eta)-1
        eta = str(eta)
        if eta == "0":
            eta = ""
        eta_print = "~" + eta
        print_maker(vehicle_number, station, next, eta, destination, speed )
        stock = 0.5 if int(str(vehicle_number)[:3]) < 300 else 1
        if destination in ["VS", "  MM", "    TAP", "       KIL"]:
            globals()[{'VS': 'vs', '  MM': 'mm', '    TAP': 'tap', '       KIL': 'kil'}[destination]] += stock

    print(" ----|--------------------|-------------|-----|-------")
    total = ceil(vs + mm + tap + kil)
    o = float(mm+tap) 
    p = float(vs+kil) 
    o = str(ceil(o)) if o.is_integer() else str(o)
    p = str(ceil(p)) if p.is_integer() else str(p) 
    m2_count = o + "xM2"
    m1_count = p + "xM1"
    print(f" {total:<4}| {m1_count:<7}    {m2_count:>7} | {ceil(vs):<2} {ceil(mm):<2} {ceil(tap):<2} {ceil(kil):<2} |     |")

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
    speed = data.get('VP', {}).get('spd', 62.5)
    speed = str(ceil(speed*3.6))
    if (latitude, longitude) in coordinates:
        current, next, track, pos = coordinates[(latitude, longitude)]
        if current == "Pre-IK":
            current = "PT" if line == "M1" else "MP" if line == "M2" else ""
        elif next == "Post-IK":
            next = "PT" if line == "M1" else "MP" if line == "M2" else ""
            pos = "76" if line == "M1" else "132" if line == "M2" else ""
        eta = eta_maker(pos)
        dest_key = (line, int(track))
        destination = destinations.get(dest_key, "")
        if not current in ["KILK", "TAPG", "SVV", "VSG", "MMG", ""]:
            current = current + track
        if not next in ["KILK", "TAPG", "SVV", "VSG", "MMG", ""]:
            next = next + track
        if len(current) == 2:
            current = " " + current           
        if next == "":
            speed = 0
        if int(speed) < 15 and int(speed) != 0:
            speed = 15
        vehicles[vehicle_number] = current, next, eta, track, destination, speed
        if vehicle_number == 203:
            vehicles[219] = current, next, eta, track, destination, speed


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