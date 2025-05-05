import paho.mqtt.client as mqtt
import json

broker = "mqtt.hsl.fi"
port = 1883
topic = "/hfp/v2/journey/ongoing/vp/metro/#"
coordinates = []

def on_message(client, userdata, message):
    data = json.loads(message.payload.decode())
    vehicle_id = data.get('VP', {}).get('veh', 'Unknown')
    if vehicle_id == 135:
        desi, dir, oper, veh, tst, tsi, spd, acc, dl, odo, drst, oday, jrn, line, start, loc, stop, route, occu, seq, label, ttarr, ttdep, dr_type = data.get('VP', {}).get('desi', 'Unknown'), data.get('VP', {}).get('dir', 'Unknown'), data.get('VP', {}).get('oper', 'Unknown'), data.get('VP', {}).get('veh', 'Unknown'), data.get('VP', {}).get('tst', 'Unknown'), data.get('VP', {}).get('tsi', 'Unknown'), data.get('VP', {}).get('spd', 'Unknown'), data.get('VP', {}).get('acc', 'Unknown'), data.get('VP', {}).get('dl', 'Unknown'), data.get('VP', {}).get('odo', 'Unknown'), data.get('VP', {}).get('drst', 'Unknown'), data.get('VP', {}).get('oday', 'Unknown'), data.get('VP', {}).get('jrn', 'Unknown'), data.get('VP', {}).get('line', 'Unknown'), data.get('VP', {}).get('start', 'Unknown'), data.get('VP', {}).get('loc', 'Unknown'), data.get('VP', {}).get('stop', 'Unknown'), data.get('VP', {}).get('route', 'Unknown'), data.get('VP', {}).get('occu', 'Unknown'), data.get('VP', {}).get('seq', 'Unknown'), data.get('VP', {}).get('label', 'Unknown'), data.get('VP', {}).get('ttarr', 'Unknown'), data.get('VP', {}).get('ttdep', 'Unknown'), data.get('VP', {}).get('dr-type', 'Unknown')
        print(desi, dir, oper, veh, tst, tsi, spd, acc, dl, odo, drst, oday, jrn, line, start, loc, stop, route, occu, seq, label, ttarr, ttdep, dr_type)

client = mqtt.Client()
client.on_message = on_message
client.connect(broker, port)
client.subscribe(topic)
client.loop_forever()