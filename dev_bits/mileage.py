import gspread, platform
from os import system
from google.oauth2.service_account import Credentials
print("Starting...")
SCOPE = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
CREDS = Credentials.from_service_account_file('mileage-machine-3000-8c0f154bda27.json', scopes=SCOPE)
client = gspread.authorize(CREDS)
sheet = client.open("Transport List 2025").sheet1
rows = sheet.get_all_values()

stations = {
    "kilk":-0.3,
    "kil": 0.0,
    "esl": 1.3,
    "sou": 2.9,
    "kai": 4.3,
    "fin": 5.5,
    "mak": 7.1,
    "nik": 9.0,
    "urp": 10.1,
    "tapg": 11.1,
    "tap": 11.4,
    "ota": 13.1,
    "ken": 14.5,
    "kos": 16.8,
    "las": 18.4,
    "rl": 20.6,
    "kp": 21.8,
    "rt": 22.3,
    "hy": 22.9,
    "ht": 23.8,
    "sn": 24.7,
    "ka": 25.8,
    "ks": 27.6,
    "hn": 29.1,
    "st": 30.5,
    "ik": 32.5,
    "pt": 33.6,
    "rs": 35.5,
    "vs": 36.8,
    "vsg": 37.1,
    "mp": 34.4,
    "kl": 35.8,
    "mm": 37.1,
    "mmg": 37.4
}
distances = a = 0
x = input("Enter start row: ")
while True:
    try: x = int(x)-1
    except Exception:
        x = input("An integer, please. Let's try again: ")
    else: break
#print(rows)
for i, row in enumerate(rows[x:], start=2):
    start = row[7].lower()
    end = row[9].lower()
    if row[1]=='2' or row[1]=='3':
        station1 = start[:-1]
        station2 = end[:-1]
        if platform.system() == "Linux":
            system('clear')
            print("Starting...")
            print("Working...")
            print(f"Calculating journey no. {a+1}...")
            print(station1.upper()+"-"+station2.upper())
        if station1 in stations and station2 in stations:
            if station1<station2:
                distance = stations[station2] - stations[station1]
            else:
                distance = stations[station1] - stations[station2]
            distance=round(distance, 1)
            if distance<0: distance=abs(distance)
        else:
            distance=None
        if distance is not None:
            sheet.update_cell(i+x-1, 12, distance)
            distances+=distance
            a+=1

if platform.system() == "Linux":
    system('clear')
    print("Starting...")
    print("Working...")
    print(f"Calculated {a} journeys with a total distance of {round(distances, 1)}km.")