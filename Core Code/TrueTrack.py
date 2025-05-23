# TrueTrack v13 (14.5.25)
import json, time, textwrap, platform, requests, paho.mqtt.client as mqtt
from os import system
from math import *
from datetime import datetime, timezone, timedelta, date as dt_date
from pytz import timezone
from pathlib import Path
from asyncio import *

global last_message, start_time, vehicles, friends, vuoros, session, alerts
last_message, start_time, vehicles, friends, vuoros, session, last_etas, alerts = time.time(), datetime.now(), {}, {}, {}, requests.Session(), {}, None
digitransitURL = "https://api.digitransit.fi/routing/v2/hsl/gtfs/v1"
API_KEY = "5442e22683ae4d7ba9dc5149b51daa2e"
session.headers.update({"Content-Type": "application/json", "digitransit-subscription-key": API_KEY})
broker, port, topic = "mqtt.hsl.fi", 1883, "/hfp/v2/journey/ongoing/vp/metro/#" # Port 8883 does not work
QUERY = '{alerts(route:"HSL:31M2"){alertDescriptionText(language: "en")}}'

# Load JSON data
if platform.system() == "Linux":
    with open('metro_coords.json', 'r') as f: coords = json.load(f)
    with open('special_timetables.json', 'r') as f: specials = json.load(f)
else:
    with open('Core Code/metro_coords.json', 'r') as f: coords = json.load(f)
    with open('Core Code/special_timetables.json', 'r') as f: specials = json.load(f)
coordinates = {tuple(coordinate): tuple(values) for coordinate, values in coords}

# Service times (M2)
"""m2as = [("04:57", "T"), ("04:57", "P"), ("17:12", "T"), ("17:13", "P"), ("21:00", "T"),
        ("21:00", "P"), ("04:49", "L"), ("05:04", "L"), ("05:19", "L"), ("05:34", "L"),
        ("05:46", "L"), ("06:01", "L"), ("05:33", "L"), ("05:48", "L"), ("06:03", "L"),
        ("06:18", "L"), ("06:33", "L"), ("06:48", "L"), ("07:03", "L"), ("05:49", "L"),
        ("05:49", "S"), ("18:59", "S"), ("19:29", "S"), ("19:49", "S"), ("19:59", "S")]"""

# Destinations
destinations = {("M1", 1): "PT", ("M1", 2): "       KIL", ("M2", 1): "  MM", ("M2", 2): "    TAP"}

##############################################  

def clear():
    if platform.system() == "Linux": system('clear')
    if platform.system() == "Windows": system('cls')

def check_friends(filtered_vehicles):
    taken = []
    for vehicle_number, [current, next, eta, track, dest, speed, dep, seq, vuoro] in filtered_vehicles.items():
        for other_vehicle_number, [other_current, other_next, other_eta, other_track, other_dest, other_speed, other_dep, other_seq, other_vuoro] in filtered_vehicles.items():
            if other_vehicle_number != vehicle_number and (vehicle_number and other_vehicle_number) not in taken:
                if vuoro == other_vuoro and vuoro!='Unknown':
                    eta = 0 if eta == "" else int(eta)
                    other_eta = 0 if other_eta == "" else int(other_eta)
                    if eta < other_eta:
                        vehicles[other_vehicle_number] = current, next, eta, track, dest, speed, dep, 2, vuoro
                        friends[other_vehicle_number] = vehicle_number
                        friends[vehicle_number] = other_vehicle_number
                    else:
                        vehicles[vehicle_number] = other_current, other_next, other_eta, other_track, other_dest, other_speed, other_dep, 1, other_vuoro
                        friends[other_vehicle_number] = vehicle_number
                        friends[vehicle_number] = other_vehicle_number
                    taken.append(vehicle_number)
                    taken.append(other_vehicle_number)                    
                elif track == other_track:
                    if (current == other_current or (current == other_next and next == "") or (next == other_current and other_next == "")) and dep == other_dep:
                        eta = 0 if eta == "" else int(eta)
                        other_eta = 0 if other_eta == "" else int(other_eta)
                        if eta < other_eta:
                            vehicles[other_vehicle_number] = current, next, eta, track, dest, speed, dep, 2, vuoro
                            friends[other_vehicle_number] = vehicle_number
                            friends[vehicle_number] = other_vehicle_number
                        else:
                            vehicles[vehicle_number] = other_current, other_next, other_eta, other_track, other_dest, other_speed, other_dep, 1, other_vuoro
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
    global timetable, vuoro_list
    date = (datetime.now(timezone("Europe/Helsinki")) - timedelta(hours=3)).date()
    if dt_date(2025, 6, 16) <= date <= dt_date(2025, 8, 10): timetable = {1: "K", 2: "K", 3: "K", 4: "K", 5: "K", 6: "L", 7: "S"}.get(date.isoweekday(), "")
    else: timetable = {1: "P", 2: "T", 3: "T", 4: "T", 5: "P", 6: "L", 7: "S"}.get(date.isoweekday(), "")
    date = date.strftime("%d.%m.%y")
    timetable = next((item[1] for item in specials if item[0] == date), timetable)
    try:
        date = datetime.now()-timedelta(hours=4.5)
        current_date = (date).strftime("%d%m%y")
        if platform.system() == "Linux": file = Path(f'Vuoro Lists/vuoro_{current_date}{timetable}.json')
        else: file = Path(f'Core Code/Vuoro Lists/{date.strftime("%m")}.{date.strftime("%y")} ({date.strftime("%B")} {date.strftime("%Y")})/vuoro_{current_date}{timetable}.json')
        if file.exists():
            with file.open('r') as f: vuoro_list = json.load(f)
        else:
            try:
                url = f'https://raw.githubusercontent.com/IsoPorksu/TrueTrack/refs/heads/main/Core%20Code/Vuoro%20Lists/{date.strftime("%m")}.{date.strftime("%y")} ({date.strftime("%B")} {date.strftime("%Y")})/vuoro_{current_date}{timetable}.json'
                resp = requests.get(url)
                vuoro_list = json.loads(resp.text)
            except: vuoro_list = {}
    except Exception as e:
        print(f" JSON fetch error: {e}")
        vuoro_list={}
    await sleep(1)

def print_maker(car, station, next, eta, destination, speed, departure, seq, vuoro):
    friend = friends.get(car, "")
    if station.endswith("1") and friend != "":
        friend = int(friend)+1
        car += 1
    if car < 299 and seq == 1: new_car = "^"+str(car)
    else: new_car = " " + str(car)
    if car in (131, 132, 320): new_car = str(new_car)+"*" # Special (motors/straphangers)
    if car in (141, 142, 179, 180): new_car = str(new_car)+"'" # Adverts
    if car in (135, 136): new_car = str(new_car)+"+" # Joel likes
    if car in (155, 156): new_car = str(new_car)+"-" # Joel dislikes
    if friend in (131, 132, 320): friend = str(friend)+"*"
    if friend in (141, 142, 179, 180): friend = str(friend)+"'"
    if friend in (135, 136): friend = str(friend)+"+"
    if friend in (155, 156): friend = str(friend)+"-"
    if car < 299 and seq == 2: friend = "^"+str(friend)
    else: friend = " " + str(friend)
    string = f"{new_car:<5}| {station:>4} "
    if next: string += f"-> {next:<5}{eta:>3}s | {destination:<11}|"
    else: string += f"             | {destination:<11}|"
    if speed not in ["0", 0] and next:
        string += f"{friend:<5}| {speed:>2} |" if friend else f"     | {speed:>2} |"
    else: string += f"{friend:<5}|    |" if friend else f"     |    |"
    if vuoro[-1]=="x":
        x="x"
        vuoro=vuoro[:-1]
    else: x=" "
    if vuoro == 'Unknown': string += f"     {departure}"
    else: string += f"{x}V{vuoro:<3}{departure}"
    print_list.append(string)

async def fetch_alerts():
    try:
        response = session.post(digitransitURL, json={'query': QUERY})
        if response.status_code == 200:
            alerts = response  
        else:
            print(f" Error fetching alerts: HTTP {response.status_code}")
            alerts = None 
    except requests.exceptions.RequestException:
        print(" No internet, retrying...")
        alerts = None
    await sleep(1)

async def print_vehicle_table():
    global print_list, session, response
    print_list, station_counter = [], 0
    sync_friends()
    for car in vehicles:
        current, other_next, eta, track, destination, speed, dep, seq, vuoro = vehicles[car]
        a, b = current, other_next
        if eta == "": eta=0
        #eta=int(eta)+15
        eta=int(eta)-1
        if int(eta) < 16 and other_next == "":
            if not eta < 0 and vehicles[car][2] != "":
                other_next = vehicles[car][1]
                #print(car, other_next)
                current = vehicles[car][0]
        if vehicles[car][2] == 0:
            current, other_next = a, b
        if int(eta)<=0:
            other_next=""
            eta=0
            if b != "": current=b 
        
        vehicles[car] = current, other_next, eta, track, destination, speed, dep, seq, vuoro
    sorted_vehicles = {k: vehicles[k] for k in sorted(vehicles)}
    if next == "":
            station_counter += 1
    counters = {key: 0 for key in ['vs', 'mm', 'tap', 'kil', 'm100_count', 'm200_count', 'm300_count', 'o300_count']}
    vehicle_ranges = [
        (range(200), 'm100_count', 0.5),
        (range(201, 225), 'm200_count', 0.5),
        (range(301, 321), 'm300_count', 1),
        (range(321, 326), 'o300_count', 1)]
    dest_map = {"PT": 'vs', "  MM": 'mm', "    TAP": 'tap', "       KIL": 'kil'}
    current_time = datetime.now(timezone("Europe/Helsinki")).replace(second=0, microsecond=0)
    # Check if dep_time is within the past 2 hours
    for vehicle_number, data in sorted_vehicles.items():
        dep_time_naive = datetime.strptime(f"{current_time.date()} {data[6]}", "%Y-%m-%d %H:%M")
        dep_time = timezone("Europe/Helsinki").localize(dep_time_naive)
        if (current_time - timedelta(minutes=130)) <= dep_time <= (current_time + timedelta(minutes=30)):
            station, next_station, eta, _, destination, speed, departure, seq, vuoro = data
            eta = "" if eta in ["", "0"] else str(eta)
            print_maker(vehicle_number, station, next_station, eta, destination, speed, departure, seq, vuoro)
            stock = 0.5 if int(str(vehicle_number)[:3]) < 300 else 1
            for num_range, count_name, increment in vehicle_ranges:
                if vehicle_number in num_range:
                    counters[count_name] += increment
            if destination in dest_map:
                counters[dest_map[destination]] += stock
    global runtime
    runtime = datetime.now() - start_time
    now = datetime.now(timezone("Europe/Helsinki"))
    clear()
    ping=f"{ceil((time.time() - last_message) * 1000)}ms"
    print(f" Runtime: {int(runtime.total_seconds())}s   Ping: {ping:<7} Time: {now.strftime('%H:%M:%S')}   Timetable: {timetable}")
    print(" Set |  Now -> Next  ETA | Destination|Set 2|Sped|Vuoro Dep ")
    print(" ----|-------------------|------------|-----|----|----------")
    for item in print_list: print(item)
    print(" ----|-------------------|------------|-----|----|----------")

    total_m2 = counters['mm'] + counters['tap']
    total_m1 = counters['vs'] + counters['kil']
    o = str(ceil(total_m1))+"xM1"
    print(f" {sum(ceil(counters[k]) for k in ['m100_count', 'm200_count', 'm300_count', 'o300_count']):<4}| {o:<5}       {ceil(total_m2):>2}xM2 |{ceil(counters['vs']):>2} {ceil(counters['mm']):>2} {ceil(counters['tap']):>2} {ceil(counters['kil']):>2} |     |    |")
    emotion = [":D", ":(", ":(", ":C", ">:(", ">:C"][int(counters['o300_count'])]
    print(f" {ceil(counters['m100_count'])}xM100, {ceil(counters['m200_count'])}xM200, {ceil(counters['m300_count'])}xM300, {ceil(counters['o300_count'])}xO300 = {emotion}")
    
    if alerts != None:
        for alert in alerts.json().get('data', {}).get('alerts', []):
            wrapped_lines = textwrap.wrap(alert['alertDescriptionText'], width=59)
            formatted_text = '\n '.join(wrapped_lines)
            print(" "+formatted_text)
    # Traffic status
    if station_counter >= sum(counters[k] for k in ['m100_count', 'm200_count', 'm300_count']) > 10 and runtime.total_seconds() > 5:
        print(" ALL TRAFFIC IS STOPPED")
    if sum(counters[k] for k in ['m100_count', 'm200_count', 'm300_count']) == 0 and runtime.total_seconds() > 5: print(" All trains are currently in bed")
    

async def update_vehicle_table():
    while True:
        await print_vehicle_table()
        await sleep(1)

def on_message(client, userdata, message):
    global last_message
    last_message = time.time()
    data = json.loads(message.payload.decode())
    dir, line, car, vuoro, dep, seq, day, lat, lon = data.get('VP', {}).get('dir', 1), data.get('VP', {}).get('desi', 'Unknown'), data.get('VP', {}).get('veh', 'Unknown'), data.get('VP', {}).get('line', 'Unknown'), data.get('VP', {}).get('start', 'Unknown'), data.get('VP', {}).get('seq', 'Unknown'), data.get('VP', {}).get('oday', 'Unknown'), data.get('VP', {}).get('lat', 'Unknown'), data.get('VP', {}).get('long', 'Unknown'), 
    speed = str(ceil(data.get('VP', {}).get('spd', 62.5) * 3.6))
    #if (lat, lon) not in coordinates:
    #    print(car)
    if (lat, lon) in coordinates:
        current, next, track, pos = coordinates[(lat, lon)]
        if current == "Pre-IK": current = "PT" if line == "M1" else "MP" if line == "M2" else ""
        elif next == "Post-IKx1": next, pos = ("PT" if line == "M1" else "MP" if line == "M2" else "", "76" if line == "M1" else "133" if line == "M2" else "")
        elif next == "Post-IKx2": next, pos = ("PT" if line == "M1" else "MP" if line == "M2" else "", "70" if line == "M1" else "130" if line == "M2" else "")
        elif next == "Post-IKx3": next, pos = ("PT" if line == "M1" else "MP" if line == "M2" else "", "69" if line == "M1" else "127" if line == "M2" else "")
        elif next == "Post-TAPx1": next, pos = ("URP" if line == "M1" else "TAPG" if line == "M2" else "", "84" if line == "M1" else "64" if line == "M2" else "")
        elif next == "Post-TAPx2": next, pos = ("URP" if line == "M1" else "TAPG" if line == "M2" else "", "79" if line == "M1" else "58" if line == "M2" else "")
        elif current == "Pre-TAP": current = "URP" if line == "M1" else "TAPG" if line == "M2" else ""
        eta = eta_maker(pos)
        #if car == 133: print(eta)
        dest_key = (line, int(dir))
        destination = destinations.get(dest_key, "")
        """if (datetime.strptime(dep, "%H:%M") > datetime.strptime("21:00", "%H:%M") and track=="2") or (datetime.strptime(dep, "%H:%M") > datetime.strptime("20:15", "%H:%M") and track=="1"): # if it leaves TAP after 20:15 then it will be an M2A
            if destination == "    TAP":
                destination = "       KIL"
        elif (dep, timetable) in m2as and destination == "    TAP":
            destination = "       KIL" """
        if current not in ["KILK", "TAPG", "SVV", "KPG", "VSG", "MMG", ""]: current += track
        # Short-term dest editing during disruption
        """if current in ["KILK", "KIL1" , "ESL1", "SOU1", "KAI1", "FIN1", "MAK1", "NIK1", "URP1", "TAP1", "OTA1", "KEN1", "KOS1", "LAS1"]: destination = "    LAS"
        if current in ["KIL2", "ESL2", "SOU2", "KAI2", "FIN2", "MAK2", "NIK2", "URP2", "TAP2", "OTA2", "KEN2", "KOS2", "LAS2"]: destination == "       KIL"
        if current in ["MMG", "MM2", "KL2", "MP2", "IK2", "VSG", "VS2", "ST2", "HN2", "KS2", "KA2", "SN2", "HT2", "HY2", "RT2", "KP2", "KPG"]: destination = "     KP" """
        if next not in ["KILK", "TAPG", "SVV", "KPG", "VSG", "MMG", ""]: next += track
        if next == "VS1" and int(eta) < 60 and int(speed) < 36: next = "VS2"
        if next == "MM1" and int(eta) < 60 and int(speed) < 36: next = "MM2"
        #if car == 203: print(203, dir, seq)
        if track == "2" and destination == "    TAP" or destination == "       KIL" or destination == "     KP":
            if car<300 and seq == 1: seq = 2
            elif car<300 and seq == 2: seq = 1
            pass
        a, b = current, next
        """if current=="PT2" and next =="IK2" and dir=="1":
                if 
                eta = 55
                next = "PT2"
                current = "IK1"
                dest = "PT"
                #print(car)"""
                
                
        #if car==175: print(current,next,dir)
        if len(current) == 2: current = " " + current
        speed = min(max(int(speed), 15), 85) if int(speed) != 0 else 0
        if car in vehicles:
            if vuoro == 'Unknown': vuoro = vehicles[car][-1]
        if car in vehicles and eta != "" and vehicles[car][2] != "":
            if int(dir) != int(track): # If running "bang road"
                eta="999"
                current, next = next, current
                next = next+"*"

        try:
            for found_vuoro, car_list in vuoro_list.items():
                if car in car_list and not vuoro.endswith("x"):
                    if vuoro=='Unknown': vuoro = f"{found_vuoro}x"
        except Exception as e: print(f" JSON fetch error: {e}")

        # Add custom-made sequence data
        if car in vehicles and track == vehicles[car][3]: seq = vehicles[car][7]
        else: seq = 0 # Sequence data is now (incorrectly) the same as direction data

        # Check if dep_time is within the past 2 hours
        helsinki = timezone("Europe/Helsinki")
        current_time = datetime.now(helsinki).replace(second=0, microsecond=0)
        dep_time_naive = datetime.strptime(f"{day} {dep}", "%Y-%m-%d %H:%M")
        dep_time = helsinki.localize(dep_time_naive)
        if (current_time - timedelta(minutes=130)) <= dep_time <= (current_time + timedelta(minutes=30)):
            if car in last_etas:
                if last_etas[car] == eta and car in vehicles:
                    eta = vehicles[car][2] # If ETA hasn't changed, get it from the vehicles dict
                elif last_etas[car] != eta: last_etas[car] = eta
            else: last_etas[car] = eta # If it has changed, use it and reset in the last_etas dict

            vehicles[car] = current, next, eta, track, destination, speed, dep, seq, vuoro
            #if car == 155:
              #vehicles[141] = current, next, eta, track, destination, speed, dep, seq, vuoro

async def export_vuoro():
    #print(runtime.total_seconds())
    if str(runtime.total_seconds()).endswith("0"):
        return
    while True: # Open old data
        try:
            date = datetime.now()-timedelta(hours=4.5)
            current_date = (date).strftime("%d%m%y")
            if platform.system() == "Linux": file = Path(f'Vuoro Lists/vuoro_{current_date}{timetable}.json')
            else: file = Path(f'Core Code/Vuoro Lists/{date.strftime("%m")}.{date.strftime("%y")} ({date.strftime("%B")} {date.strftime("%Y")})/vuoro_{current_date}{timetable}.json')
            if file.exists():
                with file.open('r') as f: existing = json.load(f)
            else: existing = {}
            # Format new data
            for car in vehicles:
                if vehicles[car][-1] != 'Unknown' and vehicles[car][-1][-1] != "x":
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
            await sleep(10)
        except Exception as e:
            print(f" JSON dumping error: {e}")
            break
        print("Exported!")

def on_disconnect(client, userdata, rc):
    if rc != 0:
        while True:
            print("Disconnected. Reconnecting...")
            client.connect(broker, port)
            client.subscribe(topic)
            sleep(1)

async def main():
    await check_timetable()
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1)
    client.on_message = on_message
    client.on_disconnect = on_disconnect
    client.reconnect_delay_set(min_delay=1, max_delay=2)
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
    await gather(update_vehicle_table(), export_vuoro(), check_timetable(), fetch_alerts())
    stop_event = Event()

run(main())