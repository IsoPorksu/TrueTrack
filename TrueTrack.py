# TrueTrack v8.5
import json, threading, time, platform, requests, paho.mqtt.client as mqtt
from os import system
from math import *
from datetime import datetime, timezone, timedelta
from pytz import timezone

global last_message, timetable
last_message = time.time()
start_time = datetime.now()
vehicles = {}
friends = {}
last_etas = {}
digitransitURL = "https://api.digitransit.fi/routing/v1/routers/hsl/index/graphql"
API_KEY = my_secret = "5442e22683ae4d7ba9dc5149b51daa2e"
headers = {"Content-Type": "application/json", "digitransit-subscription-key": API_KEY}
broker = "mqtt.hsl.fi"
port = 1883
topic = "/hfp/v2/journey/ongoing/vp/metro/#"
distance = 0
query = """{
  alerts (route: "HSL:31M2") {
    alertDescriptionText
  }
}"""
with open('metro_coords.json', 'r') as file:
    coords = json.load(file)
coordinates = {tuple(coordinate): tuple(values) for coordinate, values in coords}
with open('vuoro_list.json', 'r') as file:
    vuoros = json.load(file)
with open('special_timetables.json', 'r') as file:
    specials = json.load(file)
vuoros = {tuple(dep): vuoro for dep, vuoro in vuoros}
m2as = [("04:57", 0), ("04:49", 6), ("05:04", 6), ("05:19", 6), ("05:34", 6), ("05:46", 6), ("06:01", 6), ("05:33", 6), ("05:48", 6), ("06:03", 6), ("06:18", 6), ("06:33", 6), ("06:48", 6), ("07:03", 6), ("05:49", 7), ("19:29", 7), ("19:49", 7), ("19:59", 7), ("20:19", 7)] # A list of all other services on line M1 7
destinations = {
    ("M1", 1): "VS",
    ("M1", 2): "       KIL",
    ("M2", 1): "  MM",
    ("M2", 2): "    TAP",
}

##############################################  

def check_friends(filtered_vehicles):
    taken = []
    for vehicle_number, [current, next, eta, track, dest, speed, dep, seq] in filtered_vehicles.items():
        for other_vehicle_number, [other_current, other_next, other_eta, other_track, other_dest, other_speed, other_dep, other_seq] in filtered_vehicles.items():
            if other_vehicle_number != vehicle_number and (vehicle_number and other_vehicle_number) not in taken:
                if track == other_track:
                    if (current == other_current or (current == other_next and next == "") or (next == other_current and other_next == "")) and dep == other_dep:
                        eta = 0 if eta == "" else int(eta)
                        other_eta = 0 if other_eta == "" else int(other_eta)
                        if eta < other_eta:
                            vehicles[other_vehicle_number] = current, next, eta, track, dest, speed, dep, other_seq
                            friends[other_vehicle_number] = vehicle_number
                            friends[vehicle_number] = other_vehicle_number
                        else:
                            vehicles[vehicle_number] = other_current, other_next, other_eta, other_track, other_dest, other_speed, other_dep, seq
                            friends[other_vehicle_number] = vehicle_number
                            friends[vehicle_number] = other_vehicle_number
                        taken.append(vehicle_number)
                        taken.append(other_vehicle_number)

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
    if day_of_week in range (1,5):
        day_of_week = 0
    return day_of_week

def check_timetable():
    date = (datetime.now(timezone("Europe/Helsinki")) - timedelta(hours=3)).date()
    timetable = {1: "P", 2: "T", 3: "T", 4: "T", 5: "P", 6: "L", 7: "S"}.get(date.isoweekday(), "")
    date = date.strftime("%d.%m.%y")
    timetable = next((item[1] for item in specials if item[0] == date), timetable)
    #timetable = "HÄTÄ" # Häiriö
    return timetable

def print_maker(car, station, next, eta, destination, speed, departure, seq):
    if car < 299 and seq == 1: car = "^"+str(car)
    else: car = " " + str(car)
    if car in (131, 320):
        car = str(car)+"*"
    if car in (129, 169):
        car = str(car)+","
    if car in (141, 179):
        car = str(car)+"'"
    if car in (000, 135):
        car = str(car)+"+"
    if car in (000, 155):
        car = str(car)+"-"
    if next and eta:
        print(f"{car:<5}| {station:>4} -> {next:<4}{eta:>4}s | {destination:<11}|", end="")
    elif next:
        print(f"{car:<5}| {station:>4} -> {next:<4}    | {destination:<11}|", end="")
    else:
        print(f"{car:<5}| {station:>4}              | {destination:<11}|", end="")
    car = int(str(car)[1:4])
    friend = friends.get(car, "")
    if car < 299 and seq == 2: friend = "^"+str(friend)
    else: friend = " " + str(friend)
    if speed not in ["0", 0] and next:
        print(f"{friend:<5}| {speed:>2} | {departure}" if friend else f"     | {speed:>2} | {departure}")
    else:
        print(f"{friend:<5}|    | {departure}" if friend else f"     |    | {departure}")
    
    track = station[-1] if station.endswith(("1", "2")) else ""
    vehicles[car] = station, next, eta, track, destination, speed, departure, seq


def print_vehicle_table():
    station_counter = 0
    sync_friends()
    my_keys = sorted(vehicles.keys())
    sorted_vehicles = {key: vehicles[key] for key in my_keys}
    if platform.system() == "Linux":
        system('clear')
    runtime = datetime.now() - start_time
    runtime_seconds = str(int(runtime.total_seconds())) + "s"
    now = datetime.now(timezone("Europe/Helsinki"))
    ping = str(ceil((time.time() - last_message) * 1000)) + "ms"
    print(f" Runtime: {runtime_seconds}  Ping: {ping:>5}  Time: {now.strftime('%H:%M:%S')}  Timetable: {check_timetable()}")
    print(" Set |  Now -> Next  ETA | Destination|Set 2|Sped|Depart")
    print(" ----|-------------------|------------|-----|----|------")
    counters = {'vs': 0, 'mm': 0, 'tap': 0, 'kil': 0, 'm100_count': 0, 'm200_count': 0, 'm300_count': 0, 'o300_count': 0}
    destination_map = {"VS": 'vs', "  MM": 'mm', "    TAP": 'tap', "       KIL": 'kil'}
    vehicle_ranges = [(range(200), 'm100_count', 0.5),
        (range(201, 224), 'm200_count', 0.5),
        (range(301, 321), 'm300_count', 1),
        (range(321, 326), 'o300_count', 1)]
    for vehicle_number, [station, next, eta, track, destination, speed, departure, seq] in sorted_vehicles.items():
        eta = "" if eta == "" else str(eta)
        if eta == "0":
            eta = ""
        print_maker(vehicle_number, station, next, eta, destination, speed, departure, seq)
        stock = 0.5 if int(str(vehicle_number)[:3]) < 300 else 1
        if next == "":
            station_counter =+1
        for number_range, count_name, increment in vehicle_ranges:
            if vehicle_number in number_range:
                counters[count_name] += increment
        if destination in destination_map:
            counters[destination_map[destination]] += stock
    print(" ----|-------------------|------------|-----|----|------")
    total = ceil(counters['vs'] + counters['mm'] + counters['tap'] + counters['kil'])
    o = float(counters['mm'] + counters['tap'])
    p = float(counters['vs'] + counters['kil'])
    m2_count = f"{ceil(o)}xM2" if o.is_integer() else f"{o}xM2"
    m1_count = f"{ceil(p)}xM1" if p.is_integer() else f"{p}xM1"
    print(f" {ceil(counters['m100_count'])+ceil(counters['m200_count'])+ceil(counters['m300_count'])+ceil(counters['o300_count']):<4}| {m1_count:<7}   {m2_count:>7} | {ceil(counters['vs']):<2} {ceil(counters['mm'])}  {ceil(counters['tap'])} {ceil(counters['kil']):<2} |     |    |")
    emotions = [":D", ":)", ":|", ":(", ":C", ">:("]
    emotion = emotions[counters['o300_count']]
    print(f" {ceil(counters['m100_count'])}xM100, {ceil(counters['m200_count'])}xM200, {ceil(counters['m300_count'])}xM300, {ceil(counters['o300_count'])}xO300 = {emotion}")
    response = requests.post(digitransitURL, json={'query': query}, headers=headers)
    if response.status_code == 200:
        data = response.json()
        alerts = data['data']['alerts']
        for i, alert in enumerate(alerts):
            print("",alert['alertDescriptionText'])
    if int(station_counter) >= ceil(counters['m100_count'])+ceil(counters['m200_count'])+ceil(counters['m300_count']) and int(runtime.total_seconds())>1:
        print(" ALL TRAFFIC IS STOPPED")

def update_vehicle_table():
    while True:
        timetable = check_timetable()
        print_vehicle_table()
        time.sleep(1)

def on_message(client, userdata, message):
    global last_message
    last_message = time.time()
    data = json.loads(message.payload.decode())
    vehicle_number = data.get('VP', {}).get('veh')
    latitude, longitude = data.get('VP', {}).get('lat'), data.get('VP', {}).get('long')
    line, day, dep, seq = data.get('VP', {}).get('desi'), data.get('VP', {}).get('oday'), data.get('VP', {}).get('start'), data.get('VP', {}).get('seq') 
    speed = str(ceil(data.get('VP', {}).get('spd', 62.5) * 3.6))

    if (latitude, longitude) in coordinates:
        current, next, track, pos = coordinates[(latitude, longitude)]
        if current == "Pre-IK": current = "PT" if line == "M1" else "MP" if line == "M2" else ""
        elif next == "Post-IK": next, pos = ("PT" if line == "M1" else "MP" if line == "M2" else "", "76" if line == "M1" else "132" if line == "M2" else "")
        elif next == "Post-TAPx1": next, pos = ("URP" if line == "M1" else "TAPG" if line == "M2" else "", "84" if line == "M1" else "64" if line == "M2" else "")
        elif next == "Post-TAPx2": next, pos = ("URP" if line == "M1" else "TAPG" if line == "M2" else "", "79" if line == "M1" else "58" if line == "M2" else "")
        elif current == "Pre-TAP": current = "URP" if line == "M1" else "TAPG" if line == "M2" else ""
        eta = eta_maker(pos)
        last_etas[vehicle_number] = eta
        day = findDayNumber(day)
        dest_key = (line, int(track))
        destination = destinations.get(dest_key, "")
        if datetime.strptime(dep, "%H:%M") > datetime.strptime("20:19", "%H:%M"):
            if destination == "    TAP":
                destination = "       KIL"
        elif (dep, day) in m2as and destination == "    TAP":
            destination = "       KIL"
        if timetable == "XS" and dep == "10:20":
            destination = "       KIL"
        
        key = (dep, timetable, line, int(track))
        if key in vuoros:
            dep = vuoros[key]
        else:
            key = (dep, timetable, line, 1)
            if key in vuoros:
                dep = vuoros[key]
  
 
        if current not in ["KILK", "TAPG", "SVV", "VSG", "MMG", ""]: current += track
        """if current in ["KILK", "KIL1" , "ESL1", "SOU1", "KAI1", "FIN1", "MAK1", "NIK1", "URP1", "TAP1", "OTA1", "KEN1", "KOS1", "LAS1"]: destination = "    LAS" # Häiriö
        if current in ["KIL2", "ESL2", "SOU2", "KAI2", "FIN2", "MAK2", "NIK2", "URP2", "TAP2", "OTA2", "KEN2", "KOS2", "LAS2"]: destination == "       KIL"
        if current in ["MMG", "MM2", "KL2", "MP2", "IK2", "VSG", "VS2", "ST2", "HN2", "KS2", "KA2", "SN2", "HT2", "HY2", "RT2", "KP2", "KPG"]: destination = "     KP" """
        if next not in ["KILK", "TAPG", "SVV", "VSG", "MMG", ""]: next += track
        if next == "VS1" and int(eta) < 60 and int(speed) < 36:
            next == "VS2"
        departure = dep
        
        
        if len(current) == 2: current = " " + current
        speed = min(max(int(speed), 15), 81) if int(speed) != 0 else 0
        vehicles[vehicle_number] = current, next, eta, track, destination, speed, departure, seq
        
        if vehicle_number == 203: vehicles[219] = current, next, eta, track, destination, speed, departure, seq

timetable = check_timetable()
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