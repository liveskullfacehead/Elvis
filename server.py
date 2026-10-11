import os

import time

import json

import math

import urllib.parse

import urllib.request

from datetime import datetime, timezone

# Elvis hail monitor

# Houston, Texas

# 200-mile radius

# Hail threshold: 1 inch

# Check every 35 minutes

CLIENT_ID = os.environ.get("XWEATHER_CLIENT_ID")

CLIENT_SECRET = os.environ.get("XWEATHER_CLIENT_SECRET")

CHECK_INTERVAL = 35 * 60

MIN_HAIL_INCHES = 1.0

MAX_DISTANCE_MILES = 200

HOUSTON_LAT = 29.7604

HOUSTON_LON = -95.3698

seen = set()

def distance_miles(lat1, lon1, lat2, lon2):

    radius = 3958.8

    lat1, lon1, lat2, lon2 = map(

        math.radians,

        [lat1, lon1, lat2, lon2]

    )

    dlat = lat2 - lat1

    dlon = lon2 - lon1

    a = (

        math.sin(dlat / 2) ** 2

        + math.cos(lat1)

        * math.cos(lat2)

        * math.sin(dlon / 2) ** 2

    )

    return radius * 2 * math.asin(min(1, math.sqrt(a)))

def check_hail():

    if not CLIENT_ID or not CLIENT_SECRET:

        print("Missing Xweather credentials", flush=True)

        return

    params = urllib.parse.urlencode({

        "client_id": CLIENT_ID,

        "client_secret": CLIENT_SECRET,

        "p": f"{HOUSTON_LAT},{HOUSTON_LON}",

        "radius": "200miles",

        "limit": 100

    })

    url = (

        "https://data.api.xweather.com/"

        "stormcells/closest?" + params

    )

    try:

        with urllib.request.urlopen(url, timeout=30) as response:

            data = json.load(response)

        if not data.get("success"):

            print("Xweather API error", flush=True)

            return

        cells = data.get("response") or []

        print(

            f"Checked {len(cells)} storm cells",

            flush=True

        )

        for cell in cells:

            loc = cell.get("loc") or {}

            ob = cell.get("ob") or {}

            hail = ob.get("hail") or {}

            lat = loc.get("lat")

            lon = loc.get("long")

            if lat is None or lon is None:

                continue

            distance = distance_miles(

                HOUSTON_LAT,

                HOUSTON_LON,

                lat,

                lon

            )

            if distance > MAX_DISTANCE_MILES:

                continue

            size = float(hail.get("maxSizeIN") or 0)

            if size < MIN_HAIL_INCHES:

                continue

            cell_id = cell.get("id", "unknown")

            timestamp = ob.get("timestamp", "unknown")

            event_id = f"{cell_id}:{timestamp}"

            if event_id in seen:

                continue

            seen.add(event_id)

            print(

                f"HAIL ALERT: {size} inches | "

                f"{distance:.1f} miles from Houston | "

                f"Latitude {lat}, Longitude {lon}",

                flush=True

            )

    except Exception as error:

        print(

            f"Weather check failed: {type(error).__name__}",

            flush=True

        )

print("ELVIS HAIL MONITOR STARTING", flush=True)

while True:

    print(

        "Elvis checking weather at "

        + datetime.now(timezone.utc).isoformat(),

        flush=True

    )

    check_hail()

    print("Next check in 35 minutes", flush=True)

    time.sleep(CHECK_INTERVAL)
