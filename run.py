import os
import re
import subprocess
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
    #influxdb_client.create_database(config.get('influxdb', 'database'))

    hosts = [s for s in config.sections() if s.startswith('host_')]
    remotes = {}
    for h in hosts:
        host = {'name': h[len('host_'):]}
        host.update({option: config.get(h, option) for option in config.options(h)})
        remotes.update({host['name']: host})

    print(remotes)

    while running:
        points = []
        for host, h in remotes.items():
            command = ['ssh', 'root@{ip}', 'iw dev {if_24} survey dump | grep -A 5 \'in use\'']
            res = subprocess.run(map(lambda c: c.format(**h), command), capture_output=True, timeout=10, check=True, encoding='utf8')
            lines = res.stdout.split('\n')
            data = {}
            for l in lines:
                l = l.strip()
                d = re.split(r'\t+', l)
                if len(d) >= 2:
                    v = int(''.join(c for c in d[1] if c.isdigit() or c is '-'))
                    if 'active' in d[0]:
                        data.update({'active': v})
                    if 'busy' in d[0]:
                        data.update({'busy': v})
                    if 'receive' in d[0]:
                        data.update({'rx': v})
                    if 'transmit' in d[0]:
                        data.update({'tx': v})
                    if 'noise' in d[0]:
                        data.update({'noise': v})
            last_data = h.get('last_survey')
            if last_data is not None:
                active = data['active'] - last_data['active'] 
                if active > 500:
                    # do not collect points when we did not spent time on the channel
                    # (or, for ath10k, when the measurement time jumps backwards)
                    out = { 'busy': (data['busy'] - last_data['busy'])/active,
                            'rx': (data['rx'] - last_data['rx'])/active,
                            'tx': (data['tx'] - last_data['tx'])/active,
                            'noise': data['noise']}
                    points.append({
                        'measurement': 'channel_utilization',
                        'time': datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ'),
                        'fields': out,
                        'tags': {'host': host, 'interface': h['if_24']}
                        })

            remotes[host].update({'last_survey': data})
        if len(points):
            influxdb_client.write_points(points, time_precision="ms")
        time.sleep(10)


if __name__ == "__main__":
    main(*sys.argv[1:])
