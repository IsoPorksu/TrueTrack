import paho.mqtt.client as mqtt
import json

broker = "mqtt.hsl.fi"
port = 1883
topic = "/hfp/v2/journey/ongoing/vp/metro/#"
coordinates = []

def on_message(client, userdata, message):
    data = json.loads(message.payload.decode())
    vehicle_id = data.get('VP', {}).get('veh', 'Unknown')
    if vehicle_id == 324: # ALWAYS CHECK VEHICLE NUMBER!
        latitude = data.get('VP', {}).get('lat', 'Unknown')
        longitude = data.get('VP', {}).get('long', 'Unknown') 
        #acceleration = data.get('VP', {}).get('acc', 'Unknown')
        #heading = data.get('VP', {}). get('hdg', 'Unknown')
        print (f"({latitude}, {longitude})")
        newCoordinate = [latitude, longitude]
        coordinates.append(newCoordinate)
    formatString = "  [[{lat},{long}], [\"\",\"\",\"1\",\"\"]],\n" #CHECK TRACK NUMBER!
    with open("Dev Bits/spare_coords/metro_coords_PT2IK2.json", "w") as outfile:
        outfile.write("[\n")
        for coordinate in coordinates:
            outfile.write(str.format(formatString, lat=coordinate[0], long=coordinate[1]))
        outfile.write("]\n")

client = mqtt.Client()
client.on_message = on_message
client.connect(broker, port)
client.subscribe(topic)
client.loop_forever()