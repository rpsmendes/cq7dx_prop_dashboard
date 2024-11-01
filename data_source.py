import math

import requests
import datetime

# Function to fetch MUF and foF2 values for a specified station code
def fetch_station_values():
    url = "https://prop.kc2g.com/api/stations.json"
    response = requests.get(url)
    data = response.json()
    target_station_code = "EA036"

    for station_data in data:
        if station_data['station']['code'] == target_station_code:
            muf_value = station_data.get('mufd')
            fof2_value = station_data.get('fof2')
            timestamp = station_data.get('time')
            return {'muf': muf_value, 'fof2': fof2_value, 'time': timestamp}

# Function to fetch MUF and foF2 values for a specified station code
def fetch_essn_values():
    url = "https://prop.kc2g.com/api/essn.json?days=1"
    response = requests.get(url)
    data = response.json()
    info_array = data['24h']

    essn_values = []  # List to hold all entries

    for essn_data in info_array:
        timestamp = essn_data.get('time')
        ssn = math.floor(int(essn_data.get('ssn')))
        sfi = math.floor(int(essn_data.get('sfi')))
        # Append the data to the list
        essn_values.append({
            'time': datetime.datetime.fromtimestamp(timestamp),
            'ssn': ssn,
            'sfi': sfi
        })

    # Sort the list by time and get the most recent entry
    most_recent_entry = max(essn_values, key=lambda x: x['time']) if essn_values else None

    return most_recent_entry