# Doan'tMa'ah, 22.10e prod

import paho.mqtt.client as mqtt
from os import system
import json
from math import *
import time
import threading
from datetime import datetime, timedelta


m2tracking = False # TRACKING SWITCHt

start_time = datetime.now()
vehicles_near_stations = {}
broker = "mqtt.hsl.fi"
port = 1883
topic = "/hfp/v2/journey/ongoing/vp/metro/#"
distance = 0
stations = {
    "KILK": (60.1569, 24.6296), 
    "KIL": (60.1556, 24.6359), 
    "ESL": (60.1490, 24.6563),
    "SVV": (60.1548, 24.6584), 
    "SOU": (60.1417, 24.6691), 
    "KAI": (60.1493, 24.6903), 
    "FIN": (60.1528, 24.7105), 
    "MAK": (60.1596, 24.7394), 
    "NIK": (60.1708, 24.7628), 
    "URP": (60.1745, 24.7810), 
    "TAP": (60.1749, 24.8035), 
    "OTA": (60.1485, 24.8233), 
    "KEN": (60.1754, 24.8291),
    "KOS": (60.1632, 24.8557), 
    "LAS": (60.1593, 24.8781),  
    "RL" : (60.1632, 24.9151),
    "KP" : (60.1689, 24.9312),
    "RT" : (60.1705, 24.9414), 
    "HY" : (60.1715, 24.9472), 
    "HT" : (60.1802, 24.9497), 
    "SN" : (60.1867, 24.9593), 
    "KA" : (60.1875, 24.9771), 
    "KS" : (60.1889, 25.0082),
    "HN" : (60.1948, 25.0308),
    "ST" : (60.2055, 25.0441),
    "MV" : (60.2104, 25.0646),
    "IK" : (60.2102, 25.0779),
    "PT" : (60.2147, 25.0930),
    "RS" : (60.2054, 25.1214),
    "VS" : (60.2071, 25.1420),
    "VSG": (60.2077, 24.1499),
    "MP" : (60.2250, 25.0757),
    "KL" : (60.2359, 25.0833),
    "MM" : (60.2391, 25.1109),
    "MMG": (60.2405, 25.1143)
}

next_stations = {
    "KILK": ("KIL1"), 
    "KIL1": ("ESL1"), 
    "ESL1": ("SOU1"), 
    "SOU1": ("KAI1"), 
    "KAI1": ("FIN1"), 
    "FIN1": ("MAK1"), 
    "MAK1": ("NIK1"), 
    "NIK1": ("URP1"), 
    "URP1": ("TAP1"), 
    "TAP1": ("OTA1"), 
    "OTA1": ("KEN1"), 
    "KEN1": ("KOS1"),
    "KOS1": ("LAS1"), 
    "LAS1": ("RL1"),  
    "RL1" : ("KP1"),
    "KP1" : ("RT1"),
    "RT1" : ("HY1"), 
    "HY1" : ("HT1"), 
    "HT1" : ("SN1"), 
    "SN1" : ("KA1"), 
    "KA1" : ("KS1"),
    "KS1" : ("HN1"),
    "HN1" : ("ST1"),
    "ST1" : ("IK1"),
    "MV"  : (""),
    "IK1" : ("PT1"),
    "PT1" : ("RS1"),
    "RS1" : ("VS1"),
    "VS1" : (""),
    "VSG" : ("VS"),
    "MP1" : ("KL1"),
    "KL1" : ("MM1"),
    "MM1" : (""),
    "MMG" : ("MM"),
    "MM2" : ("KL2"),
    "KL2" : ("MP2"),
    "VS2" : ("RS2"),
    "RS2" : ("PT2"),
    "PT2" : ("IK2"),
    "IK2" : ("ST2"),
    "ST2" : ("HN2"),
    "HN2" : ("KS2"),
    "KS2" : ("KA2"),
    "KA2" : ("SN2"),
    "SN2" : ("HT2"),
    "HT2" : ("HY2"),
    "HY2" : ("RT2"),
    "RT2" : ("KP2"),
    "KP2" : ("RL2"),
    "RL2" : ("LAS2"),
    "LAS2": ("KOS2"),
    "KOS2": ("KEN2"),
    "KEN2": ("OTA2"),
    "OTA2": ("TAP2"),
    "TAP2": (""),
    "URP2": ("NIK2"),
    "NIK2": ("MAK2"),
    "MAK2": ("FIN2"),
    "FIN2": ("KAI2"),
    "KAI2": ("SOU2"),
    "SOU2": ("ESL2"),
    "ESL2": ("KIL2"),
    "KIL2": ("KILK"),
}

##############################################

# Distance-o-matic
def haversine(coord1, coord2):
    #print(f"DEBUG: {coord1}, {coord2}") # DEBUG
    try:
        if coord1 is None or coord2 is None or len(coord1) != 2 or len(coord2) != 2:
            raise ValueError("Invalid coordinates provided.")

        R = 6371e3
        lat1, lon1 = map(radians, coord1)
        lat2, lon2 = map(radians, coord2)

        dlat = lat2 - lat1
        dlon = lon2 - lon1

        a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
        c = 2 * atan2(sqrt(a), sqrt(1 - a))

        return R * c

    except Exception as e:
        print(f"Error in haversine calculation: {e}")
        return None

def print_vehicle_table(): # PRINT FUNCTION!
    myKeys = list(vehicles_near_stations.keys())
    myKeys.sort()

    sorted = {i: vehicles_near_stations[i] for i in myKeys}
    system('clear') # CLEAR
    global runtime
    runtime = datetime.now() - start_time
    runtime = int(runtime.total_seconds())
    #print(vehicles_near_stations) # DEBUG
    print(f" Runtime: {runtime}s")
    print(" Car | Location     | Destination")
    print(" ----|--------------|------------")
    global vs, mm, tap, kil, m2
    vs = mm = tap = kil = m2 = 0
    for vehicle_number, station in sorted.items():
        station, next, line, direction, dest = vehicles_near_stations[vehicle_number]
        #print(next) # DEBUG
        #print(station)
        dest = "" if station == "SVV" else dest
        if station == "KILK":
            print(f" {vehicle_number:<3} | {station:>4}         | {dest}") 
        elif station.endswith("1") or station. endswith("2"):
            #print("TRUE") # DEBUG
            if next == "":
                print(f" {vehicle_number:<3} | {station:>4}         | {dest}")
            else:
                print(f" {vehicle_number:<4}| {station:>4} -> {next:<4} | {dest}")
        else:
            #print(vehicle_number,"FALSE") # DEBUG
            print(f" {vehicle_number:<3} | {station:>3}          | {dest}") 
        stock = 0.5 if int(str(vehicle_number)[:3]) < 300 else 1
        if dest in ["VS", "  MM", "    TAP", "       KIL", "          M2"]: globals()[{'VS': 'vs', '  MM': 'mm', '    TAP': 'tap', '       KIL': 'kil', '          M2': 'm2'}[dest]] += stock

    print(" ----|--------------|------------")
    n = vs+mm+tap+kil+m2
    n = ceil(n) if isinstance(n, float) and n.is_integer() else n
    o = str(ceil(mm+tap+m2)) + "xM2"
    p = str(ceil(vs+kil)) + "xM1"
    if m2 == 0:
        print(f" {n:<4}| {p:<5}  {o:>5} |{ceil(vs):<2} {ceil(mm):<2} {ceil(tap):<2} {ceil(kil):<2}")
    else:
        print(f" {n:<4}|{p:<5}   {o:>5}|{ceil(vs):<2} {ceil(mm):<2} {ceil(tap):<2} {ceil(kil):<2} {ceil(m2):<2}") 

def update_vehicle_table():
    while True:
        print_vehicle_table()
        time.sleep(1.5-(runtime % 1)) # SLEEP

def on_message(client, userdata, message):
    data = json.loads(message.payload.decode())

    vehicle_number = data.get('VP', {}).get('veh', 'Unknown')
    latitude = data.get('VP', {}).get('lat', 'Unknown')
    longitude = data.get('VP', {}).get('long', 'Unknown')   
    line = data.get('VP', {}).get('desi', 'Unknown')
    direction = data.get('VP', {}).get('dir', 'Unknown')
    heading = data.get('VP', {}).get('hdg' , 'Unknown')  
    #print(f"Vehicle Number: {vehicle_number}, Latitude: {latitude}, Longitude: {longitude}")  # DEBUG

    vehicle_coord = (latitude, longitude)
    close_station = ""
    proximity_threshold = 200 # DISTANCE
    

    for station_name, station_coord in stations.items():
        #print(f"DEBUG2: {station_name}, {station_coord}") # DEBUG
        distance = haversine(vehicle_coord, station_coord)
        #print(distance, proximity_threshold) # DEBUG
        if distance < proximity_threshold:
            close_station = station_name
            break

     # Distance calculations for broken M2s
    if line == "M2":
        #print(heading) # DEBUG
        heading = int(heading)
        if close_station == "MP":
            direction = '1' if 0 <= heading <= 90 or 270 <= heading else '2' if 90 <= heading <= 270 else ''
        elif close_station == "HY" or close_station == "HT":
            direction = '2' if (0 <= heading <= 90) or 270 <= heading else '1' if 90 <= heading <= 270 else ''
        else:
            direction = '1' if 10 <= heading <= 170 else '2' if 190 <= heading <= 350 else ''
        if heading == 0:
            if close_station == "MAK" or close_station == "RL":
                direction = '1'
            elif close_station == "IK" or close_station == "MM":
                direction = '2'
    
    if direction == "1":
        	if line == "M1":
        		dest = "VS"
        	elif line == "M2": 
        		dest = "  MM"
    elif direction == "2":
        	if line == "M1":
        		dest = "       KIL"
        	elif line == "M2":
        		dest = "    TAP"
    else:
        dest = "          M2"

    if close_station:
        if not close_station.endswith(direction):
            tester = close_station in ["KILK", "SVV", "TAPG", "MV", "VSG", "MMG"]# or (line != "M2" and not m2tracking)
            close_station = close_station + direction if not tester else close_station
        next_station = ""

        if len(close_station) == 2:
            close_station = " " + close_station

        vehicles_near_stations[vehicle_number] = close_station, next_station, line, direction, dest

    else:  
        if vehicle_number not in vehicles_near_stations:
            #print(vehicle_number) # DEBUG
            bloop = "   " + direction
            next_station = ""
            vehicles_near_stations[vehicle_number] = ("", next_station, line, bloop, dest)
        else:
            close_station, next_station, line, direction, dest = vehicles_near_stations[vehicle_number]
            if not close_station.endswith(direction):
                tester = close_station in ["KILK", "SVV", "TAPG", "MV", "VSG", "MMG"]# or (line != "M2" and not m2tracking)
                close_station = close_station + direction if not tester else close_station
            next_station = next_stations.get(close_station, "")
            vehicles_near_stations[vehicle_number] = (close_station, next_station, line, direction, dest)
    #print(close_station, next_station, vehicle_number) # DEBUG
    if vehicle_number == 203:
            vehicles_near_stations[219] = close_station, next_station, line, direction, dest

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