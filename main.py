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

operating_condition = "LIVE"
#operating_condition = "SAVED"

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
    # Make list of stops that have arrival times
    arrival_estimates_exist = []
    for arrival_estimate in arrival_estimates["data"]:
      arrival_estimates_exist.append(arrival_estimate["stop_id"])
    
    for datum in stops["data"]:
      # If this stop is only on routes we don't care about, we exclude it
      if len([r for r in datum["routes"] if r in routes_to_exclude]) == len(datum["routes"]):
        pass
      #elif datum["stop_id"] not in arrival_estimates_exist:
      #  pass
      else:
        dict_key = datum["stop_id"]
        self.adj_list[dict_key] = {}
        self.adj_list[dict_key]["edges"] = {}
        self.adj_list[dict_key]["location"] = str(datum["location"]["lat"]) + ","
        self.adj_list[dict_key]["location"] += str(datum["location"]["lng"])
        self.adj_list[dict_key]["name"] = datum["name"]
        self.adj_list[dict_key]["arrival_estimates"] = {}
        #self.adj_list[dict_key]["dijkstra_val"] = math.inf # For use by Dijkstra's Algorithm
        #self.adj_list[dict_key]["dijkstra_prev"] = None
        self.adj_list[dict_key]["routes"] = datum["routes"]
        
      
    # Add edges between stops
    for route in routes["data"]["347"]:
      if route["route_id"] not in routes_to_exclude:
        for index, stop in enumerate(route["stops"]):
          if stop in arrival_estimates_exist:
            self.adj_list[stop]["edges"][route["stops"][(index + 1) % len(route["stops"])]] = {}
            #self.adj_list[stop]["edges"][route["stops"][(index + 1) % len(route["stops"])]]["weight"] = -1
            self.adj_list[stop]["edges"][route["stops"][(index + 1) % len(route["stops"])]]["route"] = route["route_id"]

    # Add arrival estimate information to stops
    for arrival_estimate in arrival_estimates["data"]:
      for arrival in arrival_estimate["arrivals"]:
        if arrival["route_id"] in routes_to_exclude:
          pass
        elif arrival["route_id"] not in self.adj_list[arrival_estimate["stop_id"]]["arrival_estimates"]:
          self.adj_list[arrival_estimate["stop_id"]]["arrival_estimates"][arrival["route_id"]] = []
          self.adj_list[arrival_estimate["stop_id"]]["arrival_estimates"][arrival["route_id"]].append(time.mktime(time.strptime(arrival["arrival_at"][:16], "%Y-%m-%dT%H:%M")))
        else:
          self.adj_list[arrival_estimate["stop_id"]]["arrival_estimates"][arrival["route_id"]].append(time.mktime(time.strptime(arrival["arrival_at"][:16], "%Y-%m-%dT%H:%M")))
        
  # Add the node representing the person's current location to the graph
  def add_source_node(self, location):
    self.adj_list[SRC_ID] = {}
    self.adj_list[SRC_ID]["edges"] = {}
    self.adj_list[SRC_ID]["location"] = location
    self.adj_list[SRC_ID]["name"] = SRC_ID

  # Add the node representing the person's desired destination to the graph
  def add_dest_node(self, location):
    self.adj_list[DST_ID] = {}
    self.adj_list[DST_ID]["edges"] = {}
    self.adj_list[DST_ID]["location"] = location
    self.adj_list[DST_ID]["name"] = DST_ID

  # Add edges from source to all nodes and from all nodes to destination
  # representing walking time
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

    try:
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
    except:
      sys.exit("Unable to connect to Google")
    
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
          estimated_arrival = g.adj_list[current_stop]["edges"][DST_ID]
          route_to_connected_stop = "walk"
          print("Walking time to DST_ID={}".format(estimated_arrival))
        else:
          # Route that takes us from current_stop to connected_stop
          route_to_connected_stop = g.adj_list[current_stop]["edges"][connected_stop]["route"]
          
          # Estimated arrival of bus at connected_stop via this route
          print("current_stop:{}, connected_stop:{}, route:{}".format(current_stop, connected_stop, route_to_connected_stop))
          if route_to_connected_stop in g.adj_list[connected_stop]["arrival_estimates"]:
            estimated_arrival_list = g.adj_list[connected_stop]["arrival_estimates"][route_to_connected_stop]
          else:
            estimated_arrival_list = [math.inf]
          
          for val in estimated_arrival_list:
            if val - dijkstra_val[current_stop] - current_time >= 0:
              estimated_arrival = val - dijkstra_val[current_stop] - current_time
              break
          
        print("estimated_arrival={}, djcurrent={}, djnext={}".format(estimated_arrival, dijkstra_val[current_stop], dijkstra_val[connected_stop]))
        if estimated_arrival + dijkstra_val[current_stop] < dijkstra_val[connected_stop]:
          print("Updating dijkstra_val[{}] to {} and dijkstra_prev[{}] to {}".format(connected_stop, estimated_arrival + dijkstra_val[current_stop], connected_stop, current_stop))
          dijkstra_val[connected_stop] = estimated_arrival + dijkstra_val[current_stop]
          dijkstra_prev[connected_stop] = (current_stop, route_to_connected_stop)
      
    path = [(DST_ID, "walk")]
    current = DST_ID
    print(dijkstra_prev)
    while SRC_ID not in path:
      path.append(dijkstra_prev[current])
      current = dijkstra_prev[current][0]
    
    path.reverse()
    return path
      
    
    
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
  
  try:
    stops = requests.get(stops_url, headers=headers, params=payload)
    routes = requests.get(routes_url, headers=headers, params=payload)
    stops_json = json.loads(stops.text)
    routes_json = json.loads(routes.text)
  except:
    sys.exit("Unable to connect to TransLoc API")
  
  # Get either current arrival estimates or saved ones (if buses are not running)
  if operating_condition == "LIVE":
    try:
      arrival_estimates = requests.get(arrival_estimates_url, headers=headers, params=payload)
      arrival_estimates_json = json.loads(arrival_estimates.text)
    except:
      sys.exit("Unable to connect to TransLoc API")
  elif operating_condition == "SAVED":
    with open("saved_arrival_estimates_4_30.txt", "r") as fp:
      arrival_estimates_json = json.load(fp)
  else:
    sys.exit("Unrecognized operating condition")

  # Create the graph from what's returned by TransLoc
  g = graph()
  g.parse_data(routes_json, stops_json, arrival_estimates_json)
  
  # Add source, destination, and associated edges to graph  
  rice_location = "38.0316,-78.5108"
  thornton_location = "38.0333,-78.5097"
  jpa_location = "38.0459,-78.5067"
  
  g.add_source_node(rice_location)
  g.add_dest_node(jpa_location)
  g.add_walking_edges()
  
  print(g.dijkstra(time.time()))