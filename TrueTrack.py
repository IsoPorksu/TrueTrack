# TrueTrack v7
import json, threading, time, platform, paho.mqtt.client as mqtt
from os import system
from math import *
from datetime import datetime
from pytz import timezone
from varname import nameof

global last_message
last_message = time.time()
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

m2as = [("04:57", 0), ("04:49", 5), ("05:04", 5), ("05:19", 5), ("05:34", 5), ("05:46", 5), ("06:01", 5), ("05:33", 5), ("05:48", 5), ("06:03", 5), ("06:18", 5), ("06:33", 5), ("06:48", 5), ("07:03", 5), ("05:49", 6), ("20:15", 6), ("20:30", 6), ("20:45", 6)]

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
    
def findDayNumber(day):
    date_obj = datetime.strptime(day, "%Y-%m-%d")
    day_of_week = date_obj.isoweekday()
    if day_of_week in range (0,4):
        day_of_week = 0
    return day_of_week

def print_maker(car, station, next, eta, destination, speed):
    if next and eta:
        print(f" {car:<4}| {station:>4} -> {next:<4} {eta:>4}s | {destination:<11} |", end="")
    elif next:
        print(f" {car:<4}| {station:>4} -> {next:<4}     | {destination:<11} |", end="")
    else:
        print(f" {car:<4}| {station:>4}               | {destination:<11} |", end="")
    
    friend = friends.get(car, "")
    if speed not in ["0", 0] and next:
        print(f" {friend:<4}| {speed:>2}km/h" if friend else f"     | {speed:>2}km/h")
    else:
        print(f" {friend:<4}|" if friend else "     |")
    
    track = station[-1] if station.endswith(("1", "2")) else ""
    vehicles[car] = station, next, eta, track, destination, speed


def print_vehicle_table():
    sync_friends()
    my_keys = sorted(vehicles.keys())
    sorted_vehicles = {key: vehicles[key] for key in my_keys}
    
    if platform.system() == "Linux":
        system('clear')
    runtime = datetime.now() - start_time
    runtime_seconds = str(int(runtime.total_seconds())) + "s"
    now = datetime.now(timezone("Europe/Helsinki"))
    moment = time.time()
    ping = str(ceil((moment - last_message)*1000)) + "ms"
    print(f" Runtime: {runtime_seconds}  Ping: {ping}  Time: {now.strftime('%H:%M:%S')}")
    print(" Car |  Now -> Next   ETA | Destination |Car 2| Speed")
    print(" ----|--------------------|-------------|-----|-------")
    global vs, mm, tap, kil, m100_count, m200_count, m300_count, o300_count
    vs = mm = tap = kil = m100_count = m200_count = m300_count = o300_count = 0
    
    for vehicle_number, [station, next, eta, track, destination, speed] in sorted_vehicles.items():
        eta = 0 if eta == "" else eta
        eta = str(eta)
        if eta == "0":
            eta = ""
        print_maker(vehicle_number, station, next, eta, destination, speed )
        stock = 0.5 if int(str(vehicle_number)[:3]) < 300 else 1

        if vehicle_number < 200:
            m100_count += 0.5
        elif 201 <= vehicle_number <= 223:
            m200_count += 0.5
        elif 301 <= vehicle_number <= 320:
            m300_count += 1
        elif 321 <= vehicle_number <= 325:
            o300_count += 1

        if destination in ["VS", "  MM", "    TAP", "       KIL"]:
            globals()[{'VS': 'vs', '  MM': 'mm', '    TAP': 'tap', '       KIL': 'kil'}[destination]] += stock

    print(" ----|--------------------|-------------|-----|-------")
    total = ceil(vs + mm + tap + kil)
    o = float(mm+tap)
    p = float(vs+kil)
    m2_count = str(ceil(o)) + "xM2" if o.is_integer() else str(o) + "xM2"
    m1_count = str(ceil(p)) + "xM1" if p.is_integer() else str(p) + "xM1"
    print(f" {total:<4}| {m1_count:<7}    {m2_count:>7} | {ceil(vs):<2} {ceil(mm):<2} {ceil(tap):<2} {ceil(kil):<2} |     |")
    print(f" {ceil(m100_count)}xM100, {ceil(m200_count)}xM200, {ceil(m300_count)}xM300, {ceil(o300_count)}xO300")

def update_vehicle_table():
    while True:
        print_vehicle_table()
        time.sleep(1)

def on_message(client, userdata, message):
    global last_message
    last_message = time.time()
    data = json.loads(message.payload.decode())
    vehicle_number = data.get('VP', {}).get('veh')
    latitude, longitude = data.get('VP', {}).get('lat'), data.get('VP', {}).get('long')
    line, day, dep = data.get('VP', {}).get('desi'), data.get('VP', {}).get('oday'), data.get('VP', {}).get('start')
    speed = str(ceil(data.get('VP', {}).get('spd', 62.5) * 3.6))

    if (latitude, longitude) in coordinates:
        current, next, track, pos = coordinates[(latitude, longitude)]
        if current == "Pre-IK": current = "PT" if line == "M1" else "MP" if line == "M2" else ""
        elif next == "Post-IK": next, pos = ("PT" if line == "M1" else "MP" if line == "M2" else "", "76" if line == "M1" else "132" if line == "M2" else "")
        elif next == "Post-TAPx1": next, pos = ("URP" if line == "M1" else "TAPG" if line == "M2" else "", "84" if line == "M1" else "64" if line == "M2" else "")
        elif next == "Post-TAPx2": next, pos = ("URP" if line == "M1" else "TAPG" if line == "M2" else "", "79" if line == "M1" else "58" if line == "M2" else "")
        elif current == "Pre-TAP": current = "URP" if line == "M1" else "TAPG" if line == "M2" else ""

        eta = eta_maker(pos)
        day = findDayNumber(day)
        dest_key = (line, int(track))
        destination = destinations.get(dest_key, "")
        if datetime.strptime(dep, "%H:%M") > datetime.strptime("20:19", "%H:%M"):
            if destination == "    TAP":
                print(vehicle_number)
                destination = "       KIL"
        elif (dep, day) in m2as and destination == "    TAP":
            print(vehicle_number)
            destination = "       KIL"
        
        if current not in ["KILK", "TAPG", "SVV", "VSG", "MMG", ""]: current += track
        if next not in ["KILK", "TAPG", "SVV", "VSG", "MMG", ""]: next += track
        if len(current) == 2: current = " " + current
        speed = min(max(int(speed), 15), 81) if int(speed) != 0 else 0
        vehicles[vehicle_number] = current, next, eta, track, destination, speed
        if vehicle_number == 203: vehicles[219] = current, next, eta, track, destination, speed


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