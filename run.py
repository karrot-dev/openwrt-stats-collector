import os
import sys
import signal
import configparser
import influxdb
import time
from datetime import datetime

running = True

def shutdown(signal, frame):
  global running
  running = False

signal.signal(signal.SIGTERM, shutdown)

def read_config(filename):
  config = configparser.ConfigParser()
  config.read(os.path.join(os.path.dirname(__file__), 'defaults.ini'))
  config.read(filename)
  return config

def main(config_filename):
    config = read_config(config_filename)

    influxdb_client = influxdb.InfluxDBClient(
            config.get('influxdb', 'host'),
            config.getint('influxdb', 'port'),
            config.get('influxdb', 'username'),
            config.get('influxdb', 'password'),
            config.get('influxdb', 'database'),
            )
    influxdb_client.create_database(config.get('influxdb', 'database'))


    while running:
        #data = {
                #"measurement": config.get('fritzbox', 'measurement_name'),
                #"time": datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ'),
                #"fields": points
                #}
        #influxdb_client.write_points([data], time_precision="ms")
        time.sleep(10)


if __name__ == "__main__":
    main(*sys.argv[1:])
