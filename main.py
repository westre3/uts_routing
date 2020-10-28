import requests
import json
import math
import time as tm
import sys
import route_listing
from tkinter import *
from PIL import ImageTk,Image
import os

SRC_ID = "SRC"
DST_ID = "DST"

host = "transloc-api-1-2.p.rapidapi.com"
key = "5fa48323f4mshca893848a7efd53p1bb117jsnd6adf17f2c76"
agencies = "347" # UVA
gui_path_display = ""

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
"4013640",  # Crozet Connect Loop
"4013590",  # Early Inner Loop (add back if time permits)
"4013700"
]

operating_condition = "LIVE"
#operating_condition = "SAVED"

# Saved time options
#saved_arrival_estimates = ("saved_arrival_estimates_12_05_16_30.txt", 1575585000.0)
#saved_arrival_estimates = ("saved_arrival_estimates_12_06_14_30.txt", 1575664200.0)
saved_arrival_estimates = ("saved_arrival_estimates_12_06_15_00.txt", 1575666000.0)
#saved_arrival_estimates= ("saved_arrival_estimates_12_07_14_10.txt", 1575749400.0)

# Some simple Google Maps code that uses the Static Maps API to save
# a PNG image of the specified location
#
# DO NOT call excessively, as the API is currently being used on a free trial
# basis and once we run out of the free trial charges will begin
# def googlemaps(location, image_file):
#   with open("GoogleMapsAPIKey.txt", "r") as fp:
#     key = fp.readline()
  
#   static_maps_url = "https://maps.googleapis.com/maps/api/staticmap"
#   zoom_level = 13
#   size = "500x500"
  
#   payload = {"center": location, "zoom": zoom_level, "size": size, "key": key, "path":"enc:ezegFrvd~Mv@uBdBuFLU|@yC`@eAd@cB"}
#   r = requests.get(static_maps_url, params=payload)
  
#   with open(image_file, "wb") as fp:
#     fp.write(r.content)

class Node:
  def __init__(self, stop, name, location):
    
    # The unique ID number of the stop
    self.stop = stop
    
    # The English name of the stop
    self.name = name
    
    # The value that will be used in Dijkstra's algorithm
    self.dijkstra = -math.inf
    
    # A dictionary of the estimated arrival times at this stop for each route
    self.arrival_times = {}
    
    # The latitude and longitude of the stop
    self.location = location

class Edge:
  def __init__(self, from_stop, to_stop, route, name, walking_time=None):
    
    # The source node of this directed edge
    self.from_stop = from_stop
    
    # The destination node of this directed edge
    self.to_stop = to_stop
    
    # The unique route ID that this edge corresponds to
    self.route = route

    # The English name of the route this edge corresponds to
    self.name = name
    
    self.walking_time = walking_time

# A class to hold the actual graph we'll be working with
class Graph:
  def __init__(self):
    self.nodes = {}
    self.adj_list = {}
  
  # Takes in JSON structures specifying routes, stops, and estimated arrival times 
  # and parses them into the graph's nodes and edges
  def parse_uts_data(self, stops, routes, arrival_estimates):
    
    # Mapping of IDs to names and locations
    stop_lookup = {}
    for stop in stops["data"]:
      stop_lookup[stop["stop_id"]] = {"name": stop["name"], "location": stop["location"]}
    
    route_lookup = {}
    for route in routes["data"]["347"]:
      route_lookup[route["route_id"]] = route["long_name"]
    
    running_routes = {}
    for arrival_estimate in arrival_estimates["data"]:
      
      # If this stop doesn't already exist as a node in the graph, add it
      if arrival_estimate["stop_id"] not in self.adj_list:
        self.nodes[arrival_estimate["stop_id"]] = Node(arrival_estimate["stop_id"],
                                                       stop_lookup[arrival_estimate["stop_id"]]["name"],
                                                       stop_lookup[arrival_estimate["stop_id"]]["location"])
        self.adj_list[arrival_estimate["stop_id"]] = []
    
      # Create a list of all routes that are currently running
      # Also include a vehicle ID that is running that route
      for arrival in arrival_estimate["arrivals"]:
        if arrival["route_id"] not in running_routes:
          running_routes[arrival["route_id"]] = arrival["vehicle_id"]
          
        eta = tm.mktime(tm.strptime(arrival["arrival_at"][:19], "%Y-%m-%dT%H:%M:%S"))
        if arrival["route_id"] not in self.nodes[arrival_estimate["stop_id"]].arrival_times:
          self.nodes[arrival_estimate["stop_id"]].arrival_times[arrival["route_id"]] = []
          
        self.nodes[arrival_estimate["stop_id"]].arrival_times[arrival["route_id"]].append(eta)
    
    # Add edges between stops in graph
    # I'm doing this by sorting the stops in order of arrival time estimate
    # because the routes info from TransLoc API is not in order
    for route in running_routes:
      stops_on_route = []
      stop_times = {}
      for arrival_estimate in arrival_estimates["data"]:
        for arrival in arrival_estimate["arrivals"]:          
          if arrival["vehicle_id"] == running_routes[route]:
            if arrival_estimate["stop_id"] not in stops_on_route:
              stops_on_route.append(arrival_estimate["stop_id"])
              stop_times[arrival_estimate["stop_id"]] = tm.mktime(tm.strptime(arrival["arrival_at"][:19], "%Y-%m-%dT%H:%M:%S"))
      
      # Sort routes based on arrival time estimate
      stops_on_route.sort(key = lambda stop : stop_times[stop])
      
      # Connect stops in order of arrival time estimate
      for i in range(len(stops_on_route)):
        self.adj_list[stops_on_route[i]].append(Edge(stops_on_route[i], stops_on_route[(i+1) % len(stops_on_route)], route, route_lookup[route]))

  # Add the node representing the person's current location to the graph
  def add_src_node(self, location):
    self.nodes[SRC_ID] = Node(-1, SRC_ID, location)
    self.adj_list[SRC_ID] = []

  # Add the node representing the person's desired destination to the graph
  def add_dst_node(self, location):
    self.nodes[DST_ID] = Node(-1, DST_ID, location)
    self.adj_list[DST_ID] = []

  # Add edges from source to all nodes and from all nodes to destination
  # representing walking time using Google Distance Matrix API to find walking
  # times
  def add_walking_edges(self):
    src_location = self.nodes[SRC_ID].location
    dst_location = self.nodes[DST_ID].location

    # Save stop IDs in a list to simplify code
    stops = [s for s in self.nodes if self.nodes[s].name not in [SRC_ID, DST_ID]]
    stop_locations = [f"{self.nodes[s].location['lat']},{self.nodes[s].location['lng']}" for s in stops]
    
    google_walking_url = "https://maps.googleapis.com/maps/api/distancematrix/json"
    with open("GoogleMapsAPIKey.txt", "r") as fp:
      key = fp.readline()

    try:
      # Source to stops Google Distance Matrix API request
      # Note that I only need to take into account SRC to DST route in one
      # API call, not both
      payload = {"origins" : f"{src_location['lat']},{src_location['lng']}",
                 "destinations" : "|".join(stop_locations + [f"{dst_location['lat']},{dst_location['lng']}"]),
                 "key" : key,
                 "mode" : "walking"}

      src_to_stops = requests.get(google_walking_url, params=payload)
      src_to_stops = json.loads(src_to_stops.text)
      
      if src_to_stops["status"] != "OK":
        sys.exit(f"Error : Google Distance Matrix API status is {src_to_stops['status']}")
      
      # Stops to destination Google Distance Matrix API request
      payload = {"origins" : "|".join(stop_locations),
                 "destinations" : f"{dst_location['lat']},{dst_location['lng']}",
                 "key" : key,
                 "mode" : "walking"}

      stops_to_dst = requests.get(google_walking_url, params=payload)
      stops_to_dst = json.loads(stops_to_dst.text)

    except:
      sys.exit("Unable to connect to Google Distance Matrix API")

    # Put both sets of API results in the format of an list of results
    src_to_stops = src_to_stops["rows"][0]["elements"]
    stops_to_dst = [row["elements"][0] for row in stops_to_dst["rows"]]
    
    for i in range(len(stops)):      
      # Add edge from SRC to stop
      if src_to_stops[i]["status"] == "OK":
        self.adj_list[SRC_ID].append(Edge(SRC_ID, stops[i], -1, "walking", src_to_stops[i]["duration"]["value"]))
      else:
        sys.exit(f"Error : Google Distance Matrix API status for route from SRC to {self.nodes[stops[i]].name} is {src_to_stops[i]['status']}")

      # Add edge from stop to DST
      if stops_to_dst[i]["status"] == "OK":
        self.adj_list[stops[i]].append(Edge(stops[i], DST_ID, -1, "walking", stops_to_dst[i]["duration"]["value"]))
      else:
        sys.exit(f"Error : Google Distance Matrix API status for route from {self.nodes[stops[i]].name} to DST is {stops_to_dst[i]['status']}")
    
    # Add edge from SRC to DST
    self.adj_list[SRC_ID].append(Edge(SRC_ID, DST_ID, -1, "walking", src_to_stops[-1]["duration"]["value"]))
    
  def dijkstra(self, current_time):
    unvisited = []
    dijkstra_val = {}
    dijkstra_prev = {}
    
    for stop in g.adj_list:
      unvisited.append(stop)
      
      dijkstra_val[stop] = math.inf
      
      dijkstra_prev[stop] = None
    
    dijkstra_val[SRC_ID] = 0
    
    # Update dijkstra numbers from Source node
    for connected_stop in g.adj_list[SRC_ID]["edges"]:
      dijkstra_val[connected_stop] = g.adj_list[SRC_ID]["edges"][connected_stop]
      dijkstra_prev[connected_stop] = SRC_ID
    unvisited.remove(SRC_ID)
    
    while DST_ID in unvisited:
      min_val = math.inf
      min_stop = None
      for node in unvisited:
        #print("Checking node {} with value {}".format(node, dijkstra_val[node]))
        if dijkstra_val[node] < min_val:
          min_val = dijkstra_val[node]
          min_stop = node
          #print("Updating min_val to {} and min_stop to {}".format(min_val, min_stop))

      print("Final min_val = {} and min_stop = {}".format(min_val, min_stop))

      current_stop = min_stop
      
      unvisited.remove(current_stop)
    
      # Update Dijkstra Value
      for connected_stop in g.adj_list[current_stop]["edges"]:
        if connected_stop == DST_ID:
          min_estimated_arrival = g.adj_list[current_stop]["edges"][DST_ID]
          min_route = "walk"
          print("Walking time to DST_ID={}".format(min_estimated_arrival))
        else:
          # Route that takes us from current_stop to connected_stop
          min_estimated_arrival = math.inf
          min_route = None
          for route_to_connected_stop in g.adj_list[current_stop]["edges"][connected_stop]["route"]:
          
          # Estimated arrival of bus at connected_stop via this route
            print("current_stop:{}, connected_stop:{}, route:{}".format(current_stop, connected_stop, route_to_connected_stop))
            if route_to_connected_stop in g.adj_list[connected_stop]["arrival_estimates"]:
              estimated_arrival_list = g.adj_list[connected_stop]["arrival_estimates"][route_to_connected_stop]
            else:
              estimated_arrival_list = [math.inf]

            estimated_arrival = math.inf          
            for val in estimated_arrival_list:
              if val - dijkstra_val[current_stop] - current_time >= 0:
                estimated_arrival = val - dijkstra_val[current_stop] - current_time
                break
            
            if estimated_arrival < min_estimated_arrival:
              min_estimated_arrival = estimated_arrival
              min_route = route_to_connected_stop
          
        print("min_estimated_arrival={}, djcurrent={}, djnext={}".format(min_estimated_arrival, dijkstra_val[current_stop], dijkstra_val[connected_stop]))
        if min_estimated_arrival + dijkstra_val[current_stop] < dijkstra_val[connected_stop]:
          print("Updating dijkstra_val[{}] to {} and dijkstra_prev[{}] to {}".format(connected_stop, min_estimated_arrival + dijkstra_val[current_stop], connected_stop, current_stop))
          dijkstra_val[connected_stop] = min_estimated_arrival + dijkstra_val[current_stop]
          dijkstra_prev[connected_stop] = (current_stop, min_route)
      
    path = [DST_ID]
    current = DST_ID
    print(dijkstra_prev)
    while SRC_ID not in path:
      path.append(dijkstra_prev[current])
      current = dijkstra_prev[current][0]
    
    path.reverse()
    return (path, dijkstra_val[DST_ID])
      

def display_routes(path, unique_routes, unique_stops, src_polyline, dst_polyline, image_file):
  with open("GoogleMapsAPIKey.txt", "r") as fp:
    google_key = fp.readline()
  
  static_maps_url = "https://maps.googleapis.com/maps/api/staticmap"
  segments_url = "https://transloc-api-1-2.p.rapidapi.com/segments.json"
  size = "500x500"
  
  transloc_key = "5fa48323f4mshca893848a7efd53p1bb117jsnd6adf17f2c76"
  headers = {"x-rapidapi-host": host, "x-rapidapi-key": transloc_key}
  transloc_payload = {"agencies": "347"}
  
  google_payload = [("size", size), ("key", google_key)]
  colors = ["black", "brown", "green", "purple", "yellow", "blue", "gray", "orange"]
  color_index = 0
  
  route_color = {"4013576": "0x0066ff", "4013580": "0x00aeef", "4013582": "0xed1c24",
                 "4013584": "0xf59cb0", "4013586": "0xfff200", "4013590": "0xa681ba",
                 "4013594": "0x9e1f63", "4013696": "0x714294", "4013698": "0xdc9145",
                 "4013700": "0xf4dc59"}
  
  for unique_route in unique_routes:
    segments_list = []
    transloc_payload["routes"] = unique_route
  
    segments = requests.get(segments_url, headers=headers, params=transloc_payload)
    segments_json = json.loads(segments.text)
  
    for segment_id in segments_json["data"]:
      segments_list.append(segments_json["data"][segment_id])
      
    for route_poly in segments_list:
      google_payload.append(("path", "color:" + route_color[unique_route] + "|enc:" + route_poly))
  
  lat_lons = []
  print("Path: " + str(path))
  for unique_stop in unique_stops:
    if unique_stop == SRC_ID or unique_stop == DST_ID:
      color = 'red'
    else:
      print("Unique stop: " + unique_stop)
      # Find color for unique stop
      for (stop, route) in path[1:-1]:
        print("Checking stop " + stop)
        if stop == unique_stop:
          if route == "walk":
            color = 'red'
          else:
            color = route_color[route]
    
    lat_lons.append((g.adj_list[unique_stop]["location"], color))
    
  current_label = 'A'
  for lat_lon in lat_lons:
    google_payload.append(("markers", "size:mid|label:" + current_label + "|color:" + lat_lon[1] + "|" + lat_lon[0]))
    current_label = chr(ord(current_label) + 1)
  
  # Add source to first stop polyline
  google_payload.append(("path", "color:red|enc:" + src_polyline))
  
  # Add destination to last stop polyline
  google_payload.append(("path", "color:red|enc:" + dst_polyline))
  
  r = requests.get(static_maps_url, params=google_payload)
  
  with open(image_file, "wb") as fp:
    fp.write(r.content)
    

# Use the TransLoc API to get route and stop information
stops_url = "https://transloc-api-1-2.p.rapidapi.com/stops.json"
routes_url = "https://transloc-api-1-2.p.rapidapi.com/routes.json"
arrival_estimates_url = "https://transloc-api-1-2.p.rapidapi.com/arrival-estimates.json"

headers = {"x-rapidapi-host": host, "x-rapidapi-key": key}
payload = {"agencies": agencies}

try:
  stops = requests.get(stops_url, headers=headers, params=payload)
  routes = requests.get(routes_url, headers=headers, params=payload)
  stops_json = json.loads(stops.text)
  routes_json = json.loads(routes.text)
except:
  sys.exit("Unable to connect to TransLoc")

# Get either current arrival estimates or saved ones (if buses are not running)
if operating_condition == "LIVE":
  try:
    arrival_estimates = requests.get(arrival_estimates_url, headers=headers, params=payload)
    arrival_estimates_json = json.loads(arrival_estimates.text)
  except:
    sys.exit("Unable to connect to TransLoc API")
elif operating_condition == "SAVED":
  with open(saved_arrival_estimates[0], "r") as fp:
    arrival_estimates_json = json.load(fp)
else:
  sys.exit("Unrecognized operating condition")

# Create the graph from what's returned by TransLoc
g = Graph()
g.parse_uts_data(stops_json, routes_json, arrival_estimates_json)

# # Add source, destination, and associated edges to graph  
# rice_location = "38.0316,-78.5108"
# thornton_location = "38.0333,-78.5097"
# jpa_location = "38.0459,-78.5067"
# downtown = "38.0292,-78.4773"
# colonnade = "38.042702, -78.517687"
# colonnade2 = "38.042775,-78.51756"
# lile_location = '38.035015,-78.516131'
# barracks_location = '38.048796,-78.505219'
# lake_monticello = '37.911027,-78.326811'

# g.add_source_node(e1.get())
# g.add_dest_node(e2.get())
# g.add_walking_edges()

# if operating_condition == "LIVE":
#   (path, time) = g.dijkstra(tm.time())
  
#   unique_routes = []
#   unique_stops = [SRC_ID]
#   for route_taken in path:
#       if route_taken == SRC_ID or route_taken == DST_ID:
#           pass
#       else:
#           if route_taken[0] not in unique_stops:
#               unique_stops.append(route_taken[0])
#           if route_taken[1] not in unique_routes and route_taken[1] != "walk":
#             unique_routes.append(route_taken[1])

#   unique_stops.append(DST_ID)
#   print(path, time, unique_routes, unique_stops)

#   directions_url = "https://maps.googleapis.com/maps/api/directions/json?"
  
#   with open("GoogleMapsAPIKey.txt", "r") as fp:
#     google_key = fp.readline()

#   payload = {"key": google_key, "origin": g.adj_list[SRC_ID]["location"], "destination": g.adj_list[unique_stops[1]]["location"], "mode": "walking"}
#   r = requests.get(directions_url, params=payload)
#   src_json = json.loads(r.text)
  
#   payload["origin"] = g.adj_list[unique_stops[-2]]["location"]
#   payload["destination"] = g.adj_list[DST_ID]["location"]
#   r = requests.get(directions_url, params=payload)
#   dst_json = json.loads(r.text)
  
#   display_routes(path, unique_routes, unique_stops, src_json["routes"][0]["overview_polyline"]["points"], dst_json["routes"][0]["overview_polyline"]["points"], "final_output.png")
  
# elif operating_condition == "SAVED":
#   (path, time) = g.dijkstra(saved_arrival_estimates[1])
  
#   unique_routes = []
#   unique_stops = [SRC_ID]
#   for route_taken in path:
#       if route_taken == SRC_ID or route_taken == DST_ID:
#           pass
#       else:
#           if route_taken[0] not in unique_stops:
#               unique_stops.append(route_taken[0])
#           if route_taken[1] not in unique_routes and route_taken[1] != "walk":
#             unique_routes.append(route_taken[1])

#   unique_stops.append(DST_ID)
#   print(path, time, unique_routes, unique_stops)
  
#   directions_url = "https://maps.googleapis.com/maps/api/directions/json?"
  
#   with open("GoogleMapsAPIKey.txt", "r") as fp:
#     google_key = fp.readline()

#   payload = {"key": google_key, "origin": g.adj_list[SRC_ID]["location"], "destination": g.adj_list[unique_stops[1]]["location"], "mode": "walking"}
#   r = requests.get(directions_url, params=payload)
#   src_json = json.loads(r.text)
  
#   payload["origin"] = g.adj_list[unique_stops[-2]]["location"]
#   payload["destination"] = g.adj_list[DST_ID]["location"]
#   r = requests.get(directions_url, params=payload)
#   dst_json = json.loads(r.text)
  
#   display_routes(path, unique_routes, unique_stops, src_json["routes"][0]["overview_polyline"]["points"], dst_json["routes"][0]["overview_polyline"]["points"], "final_output.png")
  
#   os.system("final_output.png")

# if __name__ == "__main__":
  # m = Tk()
  
  # Label(m, text="Source").grid(row=0)
  # Label(m, text="Destination").grid(row=1)
  
  # e1 = Entry(m)
  # e2 = Entry(m)
  
  # e1.grid(row=0, column=1)
  # e2.grid(row=1, column=1)
  
  # Button(m, 
  #       text='Find Route', command=run_program).grid(row=2, column=0, sticky=W, pady=4)
  
  
  # m.mainloop()