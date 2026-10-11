import os 
import time
import json
import urllib.request
import urllib.parse
CLIENT_ID = os.environ.get("XWEATHER_CLIENT_ID")
CLIENT_SECRET = os.environ.get("XWEATHER_CLIENT_SECRET")
while True :
  time.sleep (60)
