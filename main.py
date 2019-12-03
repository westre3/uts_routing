import requests
import json
import math
import time

SRC_ID = -1
DST_ID = -2

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
      dict_key = datum["stop_id"]
      self.adj_list[dict_key] = {}
      self.adj_list[dict_key]["edges"] = {}
#      self.adj_list[dict_key]["routes"] = datum["routes"]
      self.adj_list[dict_key]["location"] = datum["location"]
      self.adj_list[dict_key]["name"] = datum["name"]
      self.adj_list[dict_key]["arrival_estimates"] = {}
      self.adj_list[dict_key]["dijkstra"] = math.inf # For use by Dijkstra's Algorithm
    
    for route in routes["data"]["347"]:
      for index, stop in enumerate(route["stops"]):
        self.adj_list[stop]["edges"][route["stops"][(index + 1) % len(route["stops"])]] = {}
        #self.adj_list[stop]["edges"][route["stops"][(index + 1) % len(route["stops"])]]["weight"] = -1
        self.adj_list[stop]["edges"][route["stops"][(index + 1) % len(route["stops"])]]["route"] = route["route_id"]
        
    for arrival_estimate in arrival_estimates["data"]:
      for arrival in arrival_estimate["arrivals"]:
        if arrival["route_id"] not in self.adj_list[arrival_estimate["stop_id"]]["arrival_estimates"]:
          self.adj_list[arrival_estimate["stop_id"]]["arrival_estimates"][arrival["route_id"]] = []
        self.adj_list[arrival_estimate["stop_id"]]["arrival_estimates"][arrival["route_id"]].append(time.mktime(time.strptime(arrival["arrival_at"][:16], "%Y-%m-%dT%H:%M")))
          
  def add_source_node(self, location):
    self.adj_list[SRC_ID] = {}
    self.adj_list[SRC_ID]["edges"] = {}
    self.adj_list[SRC_ID]["location"] = location
    self.adj_list[SRC_ID]["name"] = "SRC"
    self.adj_list[SRC_ID]["dijkstra"] = 0
      
  def add_dest_node(self, location):
    self.adj_list[DST_ID] = {}
    self.adj_list[DST_ID]["edges"] = {}
    self.adj_list[DST_ID]["location"] = location
    self.adj_list[DST_ID]["name"] = "SRC"
    self.adj_list[DST_ID]["dijkstra"] = 0
    
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