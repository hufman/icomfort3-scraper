#!/usr/bin/python

import json
import secrets
from session import IComfort3Session
from lcc_zone import IComfort3Zone
import influxdb
import time

def generate_measurements(update):
    update_time = time.time()
    measurements = []
    if "Humidity" in update:
        measurements.append({
            "measurement": "%",
            "tags": {
                "domain": "sensor",
                "entity_id": update["systemName"] + "_humidity"
            },
            "fields": {
                "value": float(update["Humidity"])
            }
        })
    if "AmbientTemperature" in update:
        measurements.append({
            "measurement": "°F",
            "tags": {
                "domain": "sensor",
                "entity_id": update["systemName"] + "_temp"
            },
            "fields": {
                "value": float(update["AmbientTemperature"])
            }
        })
    return measurements

s = IComfort3Session()
s.login(secrets.icomfort_username, secrets.icomfort_password)
homes = s.fetch_home_zones()

influx = influxdb.InfluxDBClient(host=secrets.influxdb_hostname, database=secrets.influxdb_database)


for home in homes:
    lcc_zones = homes[home]
    for (lcc, zone) in lcc_zones:
        s.set_context(home, lcc, zone)
        z = IComfort3Zone(home, lcc, zone)
        update = z.fetch_update(s)
        measurements = generate_measurements(update)
        influx.write_points(measurements, time_precision='s')

out = s.logout()
