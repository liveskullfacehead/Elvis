import os
import time
import math
import requests
from datetime import datetime, timezone

# ============================================================
# ELVIS — HAIL LEAD MONITOR
# Xweather hail + Census ACS median home value filter
# ============================================================

CENTER_LAT = 29.7604
CENTER_LON = -95.3698

SEARCH_RADIUS_MILES = 200
MIN_HAIL_INCHES = 1.5
MIN_HOME_VALUE = 300_000
CHECK_EVERY_SECONDS = 30 * 60

XWEATHER_CLIENT_ID = os.getenv("XWEATHER_CLIENT_ID")
XWEATHER_CLIENT_SECRET = os.getenv("XWEATHER_CLIENT_SECRET")
CENSUS_API_KEY = os.getenv("CENSUS_API_KEY")

CENSUS_YEAR = "2024"
CENSUS_VARIABLE = "B25077_001E"
CENSUS_URL = f"https://api.census.gov/data/{CENSUS_YEAR}/acs/acs5"

home_value_cache = {}
alerted_events = set()

def send_sms(message):
    api_key = os.getenv(TEXTBELT_PHONE)
    phone = os.getenv("SMS_PHONE")
    if not api_key or not phone:
        print("SMS not configured.")
        return
    try:
        resonse = requests.post(
            "https://textbelt.com/text",
            {
                "phone": phone,
                "message": message,
                "key": api_key,
            },
            timeout=15
        )
        result = response.json()

        if result.get("success"):
            print("SMS sent successfully.")
        else:
            print("SMS failed:", result)

    except Exception as e:
        print("SMS error:", e)

    try:
        respose = requests.post(
            "https://textbelt.com",
            data = {
                "phone": phone,
                "message": message,
                "key": api_key,
            },
            timeout=15,
        )
        result = response.jsopn()

        if result.get("success"):
            print("SMS sent successfully.")
        else:
            print("SMS failed:",result)

    except Exception as e:
        print("SMS error:", e)

def distance_miles(lat1, lon1, lat2, lon2):
    radius = 3958.8
    p1 = math.radians(lat1)
    p2 = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)

    a = (
        math.sin(delta_lat / 2) ** 2
        + math.cos(p1)
        * math.cos(p2)
        * math.sin(delta_lon / 2) ** 2
    )

    return 2 * radius * math.asin(math.sqrt(a))


def get_median_home_value(zip_code):
    if not zip_code:
        return None

    zip_code = str(zip_code).strip()[:5]

    if zip_code in home_value_cache:
        return home_value_cache[zip_code]

    params = {
        "get": f"NAME,{CENSUS_VARIABLE}",
        "for": f"zip code tabulation area:{zip_code}",
    }

    if CENSUS_API_KEY:
        params["key"] = CENSUS_API_KEY

    try:
        response = requests.get(CENSUS_URL, params=params, timeout=20)
        response.raise_for_status()
        data = response.json()

        if len(data) < 2:
            print(f"Census: no housing data for ZIP {zip_code}")
            home_value_cache[zip_code] = None
            return None

        headers = data[0]
        values = data[1]
        record = dict(zip(headers, values))
        raw_value = record.get(CENSUS_VARIABLE)

        if raw_value in (None, "", "null"):
            home_value_cache[zip_code] = None
            return None

        value = int(float(raw_value))

        if value <= 0:
            home_value_cache[zip_code] = None
            return None

        home_value_cache[zip_code] = value
        print(f"Census ZIP {zip_code}: median home value ${value:,.0f}")
        return value

    except Exception as error:
        print(f"Census lookup error for ZIP {zip_code}:", error)
        return None


def get_hail_reports():
    if not XWEATHER_CLIENT_ID or not XWEATHER_CLIENT_SECRET:
        print("ERROR: Xweather credentials are missing.")
        return []

    url = "https://data.api.xweather.com/stormreports/within"

    params = {
        "p": f"{CENTER_LAT},{CENTER_LON}",
        "radius": f"{SEARCH_RADIUS_MILES}mi",
        "filter": "hail",
        "limit": 1000,
        "client_id": XWEATHER_CLIENT_ID,
        "client_secret": XWEATHER_CLIENT_SECRET,
    }

    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        payload = response.json()

        if not payload.get("success"):
            print("Xweather returned an unsuccessful response.")
            return []

        return payload.get("response", [])

    except Exception as error:
        print("Xweather error:", error)
        return []


def extract_hail_inches(report):
    report_data = report.get("report", {})
    detail = report_data.get("detail", {})
    hail_inches = None

    if isinstance(detail, dict):
        hail_inches = detail.get("hailIN")

    if hail_inches is None:
        hail_inches = report_data.get("hailIN")

    try:
        return float(hail_inches)
    except (TypeError, ValueError):
        return None


def extract_zip(report):
    place = report.get("place", {})
    profile = report.get("profile", {})

    zip_code = (
        place.get("zip")
        or place.get("postalCode")
        or profile.get("zip")
        or profile.get("postalCode")
    )

    if not zip_code:
        return None

    return str(zip_code).strip()[:5]


def process_report(report):
    report_data = report.get("report", {})
    report_type = str(report_data.get("type", "")).lower()

    if report_type and "hail" not in report_type:
        return

    hail_inches = extract_hail_inches(report)

    if hail_inches is None or hail_inches < MIN_HAIL_INCHES:
        return

    coordinates = report.get("loc", {})
    latitude = coordinates.get("lat")
    longitude = (
        coordinates.get("long")
        if coordinates.get("long") is not None
        else coordinates.get("lon")
    )

    distance = None

    if latitude is not None and longitude is not None:
        try:
            distance = distance_miles(
                CENTER_LAT,
                CENTER_LON,
                float(latitude),
                float(longitude),
            )
            if distance > SEARCH_RADIUS_MILES:
                return
        except (TypeError, ValueError):
            distance = None

    zip_code = extract_zip(report)

    if not zip_code:
        print(f'Qualified {hail_inches:.2f}" hail report found, but no ZIP was supplied.')
        return

    median_home_value = get_median_home_value(zip_code)

    if median_home_value is None:
        print(f'ZIP {zip_code}: {hail_inches:.2f}" hail — no usable Census home-value data.')
        return

    if median_home_value < MIN_HOME_VALUE:
        print(
            f"Skipped ZIP {zip_code}: "
            f'${median_home_value:,.0f} median value, '
            f'{hail_inches:.2f}" hail.'
        )
        return

    place = report.get("place", {})
    city = place.get("name", "Unknown")
    state = place.get("state", "TX")

    timestamp = (
        report.get("ob", {}).get("timestamp")
        or report.get("timestamp")
        or report_data.get("timestamp")
        or "unknown"
    )

    event_id = f"{timestamp}-{zip_code}-{hail_inches:.2f}"

    if event_id in alerted_events:
        return

    alerted_events.add(event_id)

    print()
    print("========================================")
    print("ELVIS QUALIFIED HAIL LEAD")
    print("========================================")
    print(f'Hail: {hail_inches:.2f}"')
    print(f"Location: {city}, {state}")
    print(f"ZIP: {zip_code}")
    send_sms(f"ELVIS HAIL ALERT: {hail_inches:.2f} inch hail - {city}, {state} ZIP {zip_code}")

    if distance is not None:
        print(f"Distance from Houston center: {distance:.1f} miles")

    print(f"ACS median home value: ${median_home_value:,.0f}")
    print(f"Minimum required value: ${MIN_HOME_VALUE:,.0f}")
    print("========================================")
    print()


def check_for_hail():
    now = datetime.now(timezone.utc)
    print()
    print("Elvis checking weather:", now.strftime("%Y-%m-%d %H:%M:%S UTC"))

    reports = get_hail_reports()
    print(f"Hail reports received: {len(reports)}")

    for report in reports:
        try:
            process_report(report)
        except Exception as error:
            print("Error processing hail report:", error)


def run_elvis():
    print("========================================")
    print("ELVIS IS ONLINE")
    print("========================================")
    print(f'Hail threshold: {MIN_HAIL_INCHES}"')
    print(f"Search radius: {SEARCH_RADIUS_MILES} miles")
    print(f"Minimum ACS median home value: ${MIN_HOME_VALUE:,}")
    print(f"Census ACS dataset: {CENSUS_YEAR}")
    print(f"Census variable: {CENSUS_VARIABLE}")
    print("Weather check: every 30 minutes")
    print("========================================")

    if not CENSUS_API_KEY:
        print("WARNING: CENSUS_API_KEY is not set.")

    while True:
        check_for_hail()
        print("Elvis sleeping for 30 minutes...")
        time.sleep(CHECK_EVERY_SECONDS)


if __name__ == "__main__":
    send_SMS("elvis test - SMS is working")
    run_elvis()
