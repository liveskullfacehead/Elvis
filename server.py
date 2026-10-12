import os 
import time
import json
import urllib.request
import urllib.parse
CLIENT_ID = os.environ.get("XWEATHER_CLIENT_ID")
CLIENT_SECRET = os.environ.get("XWEATHER_CLIENT_SECRET")
url = "https://data.api.xweather.com/hail/threats/closest"
request_url = f"{url}?p=houston,tx&radius=200miles&limit=100&client_id={CLIENT_ID}&client_secret={CLIENT_SECRET}"
def check_hail():
  print("Checking Xweather")
try:
  response = urllib.request.urlopen(request_url, timeout=30)
  data = json.load(response)
except Exception as error:
 print("Xweather error:", error)
while True: 
  check_hail()
  time.sleep(2100)
