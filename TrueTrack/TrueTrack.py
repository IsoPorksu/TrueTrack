# TrueTrack v10.4 (25.1.25)
import asyncio, json, time, platform, requests, paho.mqtt.client as mqtt
from os import system
from math import *
from datetime import datetime, timezone, timedelta
from pytz import timezone
from pathlib import Path

global last_message, start_time, vehicles, friends, vuoros, session
last_message, start_time, vehicles, friends, vuoros = time.time(), datetime.now(), {}, {}, {}

session = requests.Session()
digitransitURL = "https://api.digitransit.fi/routing/v1/routers/hsl/index/graphql"
API_KEY = "5442e22683ae4d7ba9dc5149b51daa2e"
session.headers.update({"Content-Type": "application/json", "digitransit-subscription-key": API_KEY})
broker, port, topic = "mqtt.hsl.fi", 1883, "/hfp/v2/journey/ongoing/vp/metro/#" # Port 8883 does not work
QUERY = '{alerts(route:"HSL:31M2"){alertDescriptionText}}'

# Load JSON data
if platform.system() == "Linux":
    with open('metro_coords.json', 'r') as f: coords = json.load(f)
    with open('special_timetables.json', 'r') as f: specials = json.load(f)
else:
    with open('TrueTrack/metro_coords.json', 'r') as f: coords = json.load(f)
    with open('TrueTrack/special_timetables.json', 'r') as f: specials = json.load(f)
coordinates = {tuple(coordinate): tuple(values) for coordinate, values in coords}

# Service times (M2)
m2as = [("04:57", "T"), ("04:57", "P"), ("17:12", "T"), ("17:13", "P"), ("21:00", "T"),
        ("21:00", "P"), ("04:49", "L"), ("05:04", "L"), ("05:19", "L"), ("05:34", "L"),
        ("05:46", "L"), ("06:01", "L"), ("05:33", "L"), ("05:48", "L"), ("06:03", "L"),
        ("06:18", "L"), ("06:33", "L"), ("06:48", "L"), ("07:03", "L"), ("05:49", "L"),
        ("06:00", "S"), ("19:40", "S"), ("20:15", "S"), ("20:30", "S"), ("20:45", "S"),
        ("21:00", "S")]

# Destinations
destinations = {("M1", 1): "VS", ("M1", 2): "       KIL", ("M2", 1): "  MM", ("M2", 2): "    TAP"}

##############################################  

def clear():
    if platform.system() == "Linux":
        system('clear')
    elif platform.system() == "Windows":
        system('cls')

def check_friends(filtered_vehicles):
    taken = []
    for vehicle_number, [current, next, eta, track, dest, speed, dep, seq, vuoro] in filtered_vehicles.items():
        for other_vehicle_number, [other_current, other_next, other_eta, other_track, other_dest, other_speed, other_dep, other_seq, other_vuoro] in filtered_vehicles.items():
            if other_vehicle_number != vehicle_number and (vehicle_number and other_vehicle_number) not in taken:
                if track == other_track:
                    if (current == other_current or (current == other_next and next == "") or (next == other_current and other_next == "")) and dep == other_dep:
                        eta = 0 if eta == "" else int(eta)
                        other_eta = 0 if other_eta == "" else int(other_eta)
                        if eta < other_eta:
                            vehicles[other_vehicle_number] = current, next, eta, track, dest, speed, dep, other_seq, vuoro
                            friends[other_vehicle_number] = vehicle_number
                            friends[vehicle_number] = other_vehicle_number
                        else:
                            vehicles[vehicle_number] = other_current, other_next, other_eta, other_track, other_dest, other_speed, other_dep, seq, other_vuoro
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
    except ValueError: eta = ""
    return str(eta)
    
async def check_timetable():
    global timetable
    date = (datetime.now(timezone("Europe/Helsinki")) - timedelta(hours=3)).date()
    timetable = {1: "P", 2: "T", 3: "T", 4: "T", 5: "P", 6: "L", 7: "S"}.get(date.isoweekday(), "")
    date = date.strftime("%d.%m.%y")
    timetable = next((item[1] for item in specials if item[0] == date), timetable)
    await asyncio.sleep(1)

def print_maker(car, station, next, eta, destination, speed, departure, seq, vuoro):
    if car < 299 and seq == 1: new_car = "^"+str(car)
    else: new_car = " " + str(car)
    if car in (131, 320): new_car = str(new_car)+"*" # Special (motors/straphangers)
    if car in (141, 179): new_car = str(new_car)+"'" # Adverts
    if car in (000, 135): new_car = str(new_car)+"+" # Joel likes
    if car in (000, 155): new_car = str(new_car)+"-" # Joel dislikes
    string = f"{new_car:<5}| {station:>4} "
    if next: string += f"-> {next:<4}{eta:>4}s | {destination:<11}|"
    else: string += f"             | {destination:<11}|"
    friend = friends.get(car, "")
    if friend in (131, 320): friend = str(friend)+"*"
    if friend in (141, 179): friend = str(friend)+"'"
    if friend in (000, 135): friend = str(friend)+"+"
    if friend in (000, 155): friend = str(friend)+"-"
    if car < 299 and seq == 2: friend = "^"+str(friend)

    else: friend = " " + str(friend)
    if speed not in ["0", 0] and next:
        string += f"{friend:<5}| {speed:>2} | " if friend else f"     | {speed:>2} | "
    else: string += f"{friend:<5}|    | " if friend else f"     |    | "
    if vuoro == 'Unknown': string += departure
    else: string += timetable+vuoro
    
    track = station[-1] if station.endswith(("1", "2")) else ""
    vehicles[car] = station, next, eta, track, destination, speed, departure, seq, vuoro
    print_list.append(string)

async def fetch_alerts():
    try:
        response = session.post(digitransitURL, json={'query': QUERY})
        if response.status_code == 200:
            for alert in response.json().get('data', {}).get('alerts', []):
                print(f" {alert['alertDescriptionText']}")
        else:
            print(f" Error fetching alerts: HTTP {response.status_code}")
    except requests.exceptions.RequestException:
        print(" No internet, retrying...")

async def print_vehicle_table():
    global print_list, session
    print_list, station_counter = [], 0
    sync_friends()
    sorted_vehicles = {k: vehicles[k] for k in sorted(vehicles)}
    if next == "":
            station_counter += 1
    clear()
    counters = {key: 0 for key in ['vs', 'mm', 'tap', 'kil', 'm100_count', 'm200_count', 'm300_count', 'o300_count']}
    vehicle_ranges = [
        (range(200), 'm100_count', 0.5),
        (range(201, 224), 'm200_count', 0.5),
        (range(301, 321), 'm300_count', 1),
        (range(321, 326), 'o300_count', 1)]
    dest_map = {"VS": 'vs', "  MM": 'mm', "    TAP": 'tap', "       KIL": 'kil'}
    for vehicle_number, data in sorted_vehicles.items():
        station, next_station, eta, _, destination, speed, departure, seq, vuoro = data
        eta = "" if eta in ["", "0"] else str(eta)
        print_maker(vehicle_number, station, next_station, eta, destination, speed, departure, seq, vuoro)
        # Update counters
        stock = 0.5 if int(str(vehicle_number)[:3]) < 300 else 1
        for num_range, count_name, increment in vehicle_ranges:
            if vehicle_number in num_range:
                counters[count_name] += increment
        if destination in dest_map:
            counters[dest_map[destination]] += stock

    runtime = datetime.now() - start_time
    now = datetime.now(timezone("Europe/Helsinki"))
    print(f" Runtime: {int(runtime.total_seconds())}s  Ping: {ceil((time.time() - last_message) * 1000)}ms  Time: {now.strftime('%H:%M:%S')}  Timetable: {timetable}")
    print(" Set |  Now -> Next  ETA | Destination|Set 2|Sped|Vuoro")
    print(" ----|-------------------|------------|-----|----|-----")
    for item in print_list: print(item)
    print(" ----|-------------------|------------|-----|----|-----")

    total_m2 = counters['mm'] + counters['tap']
    total_m1 = counters['vs'] + counters['kil']
    o = str(ceil(total_m1))+"xM1"
    print(f" {sum(ceil(counters[k]) for k in ['m100_count', 'm200_count', 'm300_count', 'o300_count']):<4}| {o:<5}       {ceil(total_m2):>2}xM2 | {ceil(counters['vs']):<2} {ceil(counters['mm'])}  {ceil(counters['tap'])} {ceil(counters['kil']):>2} |     |    |")
    # Train types and emotion
    emotion = [":D", ":(", ":(", ":C", ">:(", ">:C"][int(counters['o300_count'])]
    print(f" {ceil(counters['m100_count'])}xM100, {ceil(counters['m200_count'])}xM200, {ceil(counters['m300_count'])}xM300, {ceil(counters['o300_count'])}xO300 = {emotion}")
    await fetch_alerts()

    # Traffic status
    if station_counter >= sum(counters[k] for k in ['m100_count', 'm200_count', 'm300_count']) and runtime.total_seconds() > 3:
        print(" ALL TRAFFIC IS STOPPED")

async def update_vehicle_table():
    while True:
        await print_vehicle_table()
        await asyncio.sleep(1)

def on_message(client, userdata, message):
    global last_message
    last_message = time.time()
    data = json.loads(message.payload.decode())
    line, car, vuoro, dep, seq, day, lat, lon = data.get('VP', {}).get('desi', 'Unknown'), data.get('VP', {}).get('veh', 'Unknown'), data.get('VP', {}).get('line', 'Unknown'), data.get('VP', {}).get('start', 'Unknown'), data.get('VP', {}).get('seq', 'Unknown'), data.get('VP', {}).get('oday', 'Unknown'), data.get('VP', {}).get('lat', 'Unknown'), data.get('VP', {}).get('long', 'Unknown'), 
    speed = str(ceil(data.get('VP', {}).get('spd', 62.5) * 3.6))

    if (lat, lon) in coordinates:
        current, next, track, pos = coordinates[(lat, lon)]
        if current == "Pre-IK": current = "PT" if line == "M1" else "MP" if line == "M2" else ""
        elif next == "Post-IK": next, pos = ("PT" if line == "M1" else "MP" if line == "M2" else "", "76" if line == "M1" else "132" if line == "M2" else "")
        elif next == "Post-TAPx1": next, pos = ("URP" if line == "M1" else "TAPG" if line == "M2" else "", "84" if line == "M1" else "64" if line == "M2" else "")
        elif next == "Post-TAPx2": next, pos = ("URP" if line == "M1" else "TAPG" if line == "M2" else "", "79" if line == "M1" else "58" if line == "M2" else "")
        elif current == "Pre-TAP": current = "URP" if line == "M1" else "TAPG" if line == "M2" else ""
        eta = eta_maker(pos)
        #last_etas[car] = eta
        dest_key = (line, int(track))
        destination = destinations.get(dest_key, "")
        if datetime.strptime(dep, "%H:%M") > datetime.strptime("20:15", "%H:%M"): # if it leaves TAP after 20:15 then it will become an M2A
            if destination == "    TAP":
                destination = "       KIL"
        elif (dep, timetable) in m2as and destination == "    TAP":
            destination = "       KIL" 
        if current not in ["KILK", "TAPG", "SVV", "VSG", "MMG", ""]: current += track
        # Short-term dest fixing during disruption
        """if current in ["KILK", "KIL1" , "ESL1", "SOU1", "KAI1", "FIN1", "MAK1", "NIK1", "URP1", "TAP1", "OTA1", "KEN1", "KOS1", "LAS1"]: destination = "    LAS"
        if current in ["KIL2", "ESL2", "SOU2", "KAI2", "FIN2", "MAK2", "NIK2", "URP2", "TAP2", "OTA2", "KEN2", "KOS2", "LAS2"]: destination == "       KIL"
        if current in ["MMG", "MM2", "KL2", "MP2", "IK2", "VSG", "VS2", "ST2", "HN2", "KS2", "KA2", "SN2", "HT2", "HY2", "RT2", "KP2", "KPG"]: destination = "     KP" """
        if next not in ["KILK", "TAPG", "SVV", "VSG", "MMG", ""]: next += track
        if next == "VS1" and int(eta) < 60 and int(speed) < 36:
            next == "VS2"
        
        if len(current) == 2: current = " " + current
        speed = min(max(int(speed), 15), 81) if int(speed) != 0 else 0
        if vuoro == 'Unknown':
            if car in vehicles:
                vuoro = vehicles[car][-1]
        if car in vehicles and eta != "" and vehicles[car][2] != "":
            if int(eta) in range (int(vehicles[car][2])-1, int(vehicles[car][2])-10): # If running "bang road"
                eta=""
                current, next = next, current
        dep_time = datetime.strptime(dep, "%H:%M").replace(tzinfo=timezone("Europe/Helsinki"))
        current_time = datetime.now(timezone("Europe/Helsinki")).replace(second=0, microsecond=0)

        try:
            current_date = datetime.now().strftime("%d%m%y")
            if platform.system() == "Linux": file = Path(f'Vuoro Lists/vuoro_{current_date}{timetable}.json')
            else: file = Path(f'TrueTrack/Vuoro Lists/vuoro_{current_date}{timetable}.json')
            if file.exists():
                with file.open('r') as f: vuoro_list = json.load(f)
            else: vuoro_list = {}
        except Exception as e:
            print(f" JSON fetch error: {e}")
        for found_vuoro, car_list in vuoro_list.items():
            if car in car_list: vuoro = found_vuoro
        # Check if dep_time is within the past 2 hours
        dep_time = datetime.strptime(f"{day} {dep}", "%Y-%m-%d %H:%M").replace(tzinfo=timezone("Europe/Helsinki"))
        current_time = datetime.now(timezone("Europe/Helsinki")).replace(second=0, microsecond=0)
        if (current_time - timedelta(hours=2)) <= dep_time <= (current_time + timedelta(minutes=30)):
            vehicles[car] = current, next, eta, track, destination, speed, dep, seq, vuoro

async def export_vuoro():
    await asyncio.sleep(2)
    while True: # Open old data
        try:
            current_date = datetime.now().strftime("%d%m%y")
            if platform.system() == "Linux": file = Path(f'Vuoro Lists/vuoro_{current_date}{timetable}.json')
            else: file = Path(f'TrueTrack/Vuoro Lists/vuoro_{current_date}{timetable}.json')
            if file.exists():
                with file.open('r') as f: existing = json.load(f)
            else: existing = {}
            
            # Format new data
            for car in vehicles:
                if vehicles[car][-1] != 'Unknown':
                    vuoros[vehicles[car][-1]] = car, 0
                    if car in friends: vuoros[vehicles[car][-1]] = car, friends[car]
            combined = {**existing, **vuoros}
            sorted_data = dict(sorted(combined.items(), key=lambda x: int(x[0])))
            with file.open('w') as f:
                f.write("{\n")
                for idx, (key, value) in enumerate(sorted_data.items()):
                    value = sorted(value)
                    if 0 in value:
                        value.remove(0)
                        value.append(0)
                    line = f'    "{key}": {json.dumps(value)}'
                    if idx < len(sorted_data) - 1:
                        line += ","
                    f.write(line + "\n")
                f.write("}\n")
            await asyncio.sleep(11)
        except Exception as e:
            print(f" JSON dumping error: {e}")
            break

async def main():
    await check_timetable()
    client = mqtt.Client()
    client.on_message = on_message
    while True:
        try:
            client.connect(broker, port)
            break
        except Exception as e:
            clear()
            print(f" Connection error: {e}. Retrying...")
            time.sleep(1)
    client.subscribe(topic)
    client.loop_start()
    await asyncio.gather(update_vehicle_table(), export_vuoro(), check_timetable())
    stop_event = asyncio.Event()
    try: stop_event.wait()
    except KeyboardInterrupt:
        client.loop_stop()
        client.disconnect()
        session.close()

asyncio.run(main())