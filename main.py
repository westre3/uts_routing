import requests
import json
import math
import time
import sys

SRC_ID = "SRC"
DST_ID = "DST"

# Routes we include by default:
# Northline               "4013584"
# Central Grounds Shuttle "4013586"
# Blue                    "4013576"
# Blueline Express        "4013580"
# Red                     "4013582"
# Early Inner Loop        "4013590"
# Northline Express       "4013594"
# Purple                  "4013696"
# Outer Loop              "4013698"
# Inner Loop              "4013700"

routes_to_exclude = [
"4013468", # 29 North Connect
"4013470", # Buckingham East Connect
"4013472", # Buckingham North Connect
"4013474", # Crozet East Connect
"4013476", # Crozet West Connect
"4013478", # Lovingston Connect
"4013480", # Park connect
"4013640"  # Crozet Connect Loop
]

# Some simple Google Maps code that uses the Static Maps API to save
# a PNG image of the specified location
#
# DO NOT call excessively, as the API is currently being used on a free trial
# basis and once we run out of the free trial charges will begin
def googlemaps(location, image_file):
  with open("GoogleMapsAPIKey.txt", "r") as fp:
    key = fp.readline()
  
  static_maps_url = "https://maps.googleapis.com/maps/api/staticmap"
  zoom_level = 12
  size = "500x500"
  
  payload = {"center": location, "zoom": zoom_level, "size": size, "key": key}
  r = requests.get(static_maps_url, params=payload)
  
  with open(image_file, "wb") as fp:
    fp.write(r.content)

# A class to hold the actual graph we'll be working with
class graph:
  def __init__(self):
    self.adj_list = {}
  
  # Takes in JSON structures specifying routes, stops, and estimated arrival times 
  # and parses them into the graph's nodes and edges
  def parse_data(self, routes, stops, arrival_estimates):
    for datum in stops["data"]:
      # If this stop is only on routes we don't care about, we exclude it
      if len([r for r in datum["routes"] if r in routes_to_exclude]) == len(datum["routes"]):
        pass
      else:
        dict_key = datum["stop_id"]
        self.adj_list[dict_key] = {}
        self.adj_list[dict_key]["edges"] = {}
        self.adj_list[dict_key]["location"] = str(datum["location"]["lat"]) + ","
        self.adj_list[dict_key]["location"] += str(datum["location"]["lng"])
        self.adj_list[dict_key]["name"] = datum["name"]
        self.adj_list[dict_key]["arrival_estimates"] = {}
        self.adj_list[dict_key]["dijkstra"] = math.inf # For use by Dijkstra's Algorithm
        self.adj_list[dict_key]["routes"] = datum["routes"]
      
    for route in routes["data"]["347"]:
      if route["route_id"] not in routes_to_exclude:
        for index, stop in enumerate(route["stops"]):
          self.adj_list[stop]["edges"][route["stops"][(index + 1) % len(route["stops"])]] = {}
          #self.adj_list[stop]["edges"][route["stops"][(index + 1) % len(route["stops"])]]["weight"] = -1
          self.adj_list[stop]["edges"][route["stops"][(index + 1) % len(route["stops"])]]["route"] = route["route_id"]

    for arrival_estimate in arrival_estimates["data"]:
      for arrival in arrival_estimate["arrivals"]:
        if arrival["route_id"] in routes_to_exclude:
          pass
        elif arrival["route_id"] not in self.adj_list[arrival_estimate["stop_id"]]["arrival_estimates"]:
          self.adj_list[arrival_estimate["stop_id"]]["arrival_estimates"][arrival["route_id"]] = []
          self.adj_list[arrival_estimate["stop_id"]]["arrival_estimates"][arrival["route_id"]].append(time.mktime(time.strptime(arrival["arrival_at"][:16], "%Y-%m-%dT%H:%M")))
          
  def add_source_node(self, location):
    self.adj_list[SRC_ID] = {}
    self.adj_list[SRC_ID]["edges"] = {}
    self.adj_list[SRC_ID]["location"] = location
    self.adj_list[SRC_ID]["name"] = "SRC"
    self.adj_list[SRC_ID]["dijkstra"] = 0

  def add_walking_edges(self):
    src_location = self.adj_list[SRC_ID]["location"]
    dst_location = self.adj_list[DST_ID]["location"]
    
    # This code limits the number of destinations in a single call to 25, which
    # is a limit set by the Google Distance Matrix API
    stop_locations = [""]
    num_requests = 0
    for stop in self.adj_list:
      if num_requests > 25:
        sys.exit("Error: Too many calls to Google Distance Matrix API: requests=" + str(num_requests) + ", max=25")
      elif num_requests == 25:
        # Remove  trailing pipe character
        stop_locations[-1] = stop_locations[-1][:-1]
        
        #stop_locations_index += 1
        stop_locations.append("")
        num_requests = 0
      
      stop_locations[-1] += self.adj_list[stop]["location"] + "|"
      num_requests += 1
    
    # Remove  trailing pipe character
    stop_locations[-1] = stop_locations[-1][:-1]
    
    google_walking_url = "https://maps.googleapis.com/maps/api/distancematrix/json"
    with open("GoogleMapsAPIKey.txt", "r") as fp:
      key = fp.readline()

    # Source to stops Google API requests
    payload = {"origins":src_location, "key":key, "mode":"walking"}
    walking_results = []
    walking_results_json = []
    for max25_stop_locations in stop_locations:
      payload["destinations"] = max25_stop_locations
    
      walking_results.append(requests.get(google_walking_url, params=payload))
      walking_results_json.append(json.loads(walking_results[-1].text))
    
      if walking_results_json[-1]["status"] != "OK":
        sys.exit("Error: Google Distance Matrix Overall Status is " + walking_results_json[-1]["status"])
    
    # Stop to Destination Google API requests
    payload = {"destinations":dst_location, "key":key, "mode":"walking"}
    dst_walking_results = []
    dst_walking_results_json = []
    for max25_stop_locations in stop_locations:
      payload["origins"] = max25_stop_locations
      
      dst_walking_results.append(requests.get(google_walking_url, params=payload))
      dst_walking_results_json.append(json.loads(dst_walking_results[-1].text))
      
      if dst_walking_results_json[-1]["status"] != "OK":
        sys.exit("Error: Google Distance Matrix Overall Status is " + walking_results_json[-1]["status"])
    
    json_index = 0
    for stop in self.adj_list:
      # Source to stop status check
      if walking_results_json[json_index // 25]["rows"][0]["elements"][json_index % 25]["status"] != "OK":
        sys.exit("Error: Google Distance Matrix Status for element " + 
                 str(json_index) + " is " + walking_results_json[json_index // 25]["rows"][0]["elements"][json_index % 25]["status"])
      
      # Stop to Destination status check
      if dst_walking_results_json[json_index // 25]["rows"][json_index % 25]["elements"][0]["status"] != "OK":
        sys.exit("Error: Google Distance Matrix Status for element " + 
                 str(json_index) + " is " + dst_walking_results_json[json_index // 25]["rows"][json_index % 25]["elements"][0]["status"])
      
      # Add edge from source to stop
      self.adj_list[SRC_ID]["edges"][stop] = walking_results_json[json_index // 25]["rows"][0]["elements"][json_index % 25]["duration"]["value"]
      
      # Add edge from stop to destination
      self.adj_list[stop]["edges"][DST_ID] = dst_walking_results_json[json_index // 25]["rows"][json_index % 25]["elements"][0]["duration"]["value"]
      
      json_index += 1

  def add_dest_node(self, location):
    self.adj_list[DST_ID] = {}
    self.adj_list[DST_ID]["edges"] = {}
    self.adj_list[DST_ID]["location"] = location
    self.adj_list[DST_ID]["name"] = "SRC"
    self.adj_list[DST_ID]["dijkstra"] = math.inf
    
if __name__ == "__main__":
  # Use the TransLoc API to get route and stop information
  stops_url = "https://transloc-api-1-2.p.rapidapi.com/stops.json"
  routes_url = "https://transloc-api-1-2.p.rapidapi.com/routes.json"
  arrival_estimates_url = "https://transloc-api-1-2.p.rapidapi.com/arrival-estimates.json"
  host = "transloc-api-1-2.p.rapidapi.com"
  key = "5fa48323f4mshca893848a7efd53p1bb117jsnd6adf17f2c76"
  agencies = "347" # UVA
  
  headers = {"x-rapidapi-host": host, "x-rapidapi-key": key}
  payload = {"agencies": agencies}
  
  stops = requests.get(stops_url, headers=headers, params=payload)
  routes = requests.get(routes_url, headers=headers, params=payload)
  arrival_estimates = requests.get(arrival_estimates_url, headers=headers, params=payload)
  stops_json = json.loads(stops.text)
  routes_json = json.loads(routes.text)
  arrival_estimates_json = json.loads(arrival_estimates.text)
  
  # Create the graph from what's returned by TransLoc
  g = graph()
  g.parse_data(routes_json, stops_json, arrival_estimates_json)
  
  # Add source, destination, and associated edges to graph
  
  # Rice Hall
  rice_location = "38.0316,-78.5108"
  
  # Thornton Hall
  thornton_location = "38.0333,-78.5097"
  
  g.add_source_node(rice_location)
  g.add_dest_node(thornton_location)
  g.add_walking_edges()
  
  