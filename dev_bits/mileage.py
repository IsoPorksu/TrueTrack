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
distances = 0
while True:
    station1 = input(" ")
    if station1=="done": break
    station2 = input(" ")

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
        print(f" {station1}-{station2} is {distance}km")
        distances+=distance
    else:
        print(" Invalid!")
print(f" Total: {distances}km")