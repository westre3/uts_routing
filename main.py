import requests
import json
import math
import time as tm
import sys
import route_listing
from tkinter import *
from PIL import ImageTk,Image 

SRC_ID = "SRC"
DST_ID = "DST"

host = "transloc-api-1-2.p.rapidapi.com"
key = "5fa48323f4mshca893848a7efd53p1bb117jsnd6adf17f2c76"
agencies = "347" # UVA

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

#operating_condition = "LIVE"
operating_condition = "SAVED"

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
def googlemaps(location, image_file):
  with open("GoogleMapsAPIKey.txt", "r") as fp:
    key = fp.readline()
  
  static_maps_url = "https://maps.googleapis.com/maps/api/staticmap"
  zoom_level = 13
  size = "500x500"
  
  payload = {"center": location, "zoom": zoom_level, "size": size, "key": key, "path":"enc:ezegFrvd~Mv@uBdBuFLU|@yC`@eAd@cB"}
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
      elif datum["stop_id"] not in arrival_estimates_exist:
        pass
      else:
        dict_key = datum["stop_id"]
        self.adj_list[dict_key] = {}
        self.adj_list[dict_key]["edges"] = {}
        self.adj_list[dict_key]["location"] = str(datum["location"]["lat"]) + ","
        self.adj_list[dict_key]["location"] += str(datum["location"]["lng"])
        self.adj_list[dict_key]["name"] = datum["name"]
        self.adj_list[dict_key]["arrival_estimates"] = {}
        self.adj_list[dict_key]["routes"] = datum["routes"]
        
      
    # Add edges between stops
    for route in routes:
      if route not in routes_to_exclude:
        for index, stop in enumerate(routes[route]):
          # If the current stop has no arrival estimate, don't include it in the graph
          if stop not in arrival_estimates_exist:
            pass
          
          # If the current stop has an arrival estimate, but the next stop doesn't, skip over that
          # stop and add an edge to the next stop that does have an arrival estimate
          elif stop in arrival_estimates_exist and routes[route][(index + 1) % len(routes[route])] not in arrival_estimates_exist:
            next_stop = None
            for i in range(2, len(routes[route])):
              if routes[route][(index + i) % len(routes[route])] in arrival_estimates_exist:
                next_stop = i
                break
              
            if routes[route][(index + next_stop) % len(routes[route])] not in self.adj_list[stop]["edges"]:
              self.adj_list[stop]["edges"][routes[route][(index + next_stop) % len(routes[route])]] = {}
              self.adj_list[stop]["edges"][routes[route][(index + next_stop) % len(routes[route])]]["route"] = []
            self.adj_list[stop]["edges"][routes[route][(index + next_stop) % len(routes[route])]]["route"].append(route)
          
          # If the current stop and next stop both have arrival estimates, add an edge from
          # the current stop to the next stop
          else:
            if routes[route][(index + 1) % len(routes[route])] not in self.adj_list[stop]["edges"]:
              self.adj_list[stop]["edges"][routes[route][(index + 1) % len(routes[route])]] = {}
              self.adj_list[stop]["edges"][routes[route][(index + 1) % len(routes[route])]]["route"] = []
            self.adj_list[stop]["edges"][routes[route][(index + 1) % len(routes[route])]]["route"].append(route)

    # Add arrival estimate information to stops
    for arrival_estimate in arrival_estimates["data"]:
      for arrival in arrival_estimate["arrivals"]:
        if arrival["route_id"] in routes_to_exclude:
          pass
        elif arrival["route_id"] not in self.adj_list[arrival_estimate["stop_id"]]["arrival_estimates"]:
          self.adj_list[arrival_estimate["stop_id"]]["arrival_estimates"][arrival["route_id"]] = []
          self.adj_list[arrival_estimate["stop_id"]]["arrival_estimates"][arrival["route_id"]].append(tm.mktime(tm.strptime(arrival["arrival_at"][:16], "%Y-%m-%dT%H:%M")))
        else:
          self.adj_list[arrival_estimate["stop_id"]]["arrival_estimates"][arrival["route_id"]].append(tm.mktime(tm.strptime(arrival["arrival_at"][:16], "%Y-%m-%dT%H:%M")))
        
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
      
g = graph()

def display_routes(unique_routes, unique_stops, src_polyline, dst_polyline, image_file):
  with open("GoogleMapsAPIKey.txt", "r") as fp:
    google_key = fp.readline()
  
  static_maps_url = "https://maps.googleapis.com/maps/api/staticmap"
  segments_url = "https://transloc-api-1-2.p.rapidapi.com/segments.json"
  size = "500x500"
  
  transloc_key = "5fa48323f4mshca893848a7efd53p1bb117jsnd6adf17f2c76"
  headers = {"x-rapidapi-host": host, "x-rapidapi-key": transloc_key}
  payload = {"agencies": "347"}
  
  segments_list = []
  for unique_route in unique_routes:
    payload["routes"] = unique_route
  
    segments = requests.get(segments_url, headers=headers, params=payload)
    segments_json = json.loads(segments.text)
  
    segments_list.append([])
    for segment_id in segments_json["data"]:
      segments_list[-1].append(segments_json["data"][segment_id])
      
  #payload = {"size": size, "key": google_key, "path":"enc:}zdgFtud~MwBvE"|"enc:yyegFz~d~M_@[_Ak@"}
  payload = [("size", size), ("key", google_key)]
  colors = ["black", "brown", "green", "purple", "yellow", "blue", "gray", "orange"]
  color_index = 0
  
  for route_poly in segments_list:
    for segment in route_poly:
      payload.append(("path", "color:" + colors[color_index] + "|enc:" + segment))
    color_index += 1
  
  lat_lons = []
  for unique_stop in unique_stops:
    lat_lons.append(g.adj_list[unique_stop]["location"])
    
  current_label = 'A'
  for lat_lon in lat_lons:
    payload.append(("markers", "size:mid|label:" + current_label + "|" + lat_lon))
    current_label = chr(ord(current_label) + 1)
  
  # Add source to first stop polyline
  payload.append(("path", "color:red|enc:" + src_polyline))
  
  # Add destination to last stop polyline
  payload.append(("path", "color:red|enc:" + dst_polyline))
  
  r = requests.get(static_maps_url, params=payload)
  
  with open(image_file, "wb") as fp:
    fp.write(r.content)
    
def run_program():
  # Use the TransLoc API to get route and stop information
  stops_url = "https://transloc-api-1-2.p.rapidapi.com/stops.json"
  routes_url = "https://transloc-api-1-2.p.rapidapi.com/routes.json"
  arrival_estimates_url = "https://transloc-api-1-2.p.rapidapi.com/arrival-estimates.json"
  
  headers = {"x-rapidapi-host": host, "x-rapidapi-key": key}
  payload = {"agencies": agencies}
  
  try:
    stops = requests.get(stops_url, headers=headers, params=payload)
    #routes = requests.get(routes_url, headers=headers, params=payload)
    stops_json = json.loads(stops.text)
    #routes_json = json.loads(routes.text)
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
    with open(saved_arrival_estimates[0], "r") as fp:
      arrival_estimates_json = json.load(fp)
  else:
    sys.exit("Unrecognized operating condition")

  # Create the graph from what's returned by TransLoc
  g.parse_data(route_listing.routes, stops_json, arrival_estimates_json)
  
  # Add source, destination, and associated edges to graph  
  rice_location = "38.0316,-78.5108"
  thornton_location = "38.0333,-78.5097"
  jpa_location = "38.0459,-78.5067"
  downtown = "38.0292,-78.4773"
  colonnade = "38.042702, -78.517687"
  colonnade2 = "38.042775,-78.51756"
  lile_location = '38.035015,-78.516131'
  barracks_location = '38.048796,-78.505219'
  lake_monticello = '37.911027,-78.326811'
  
  g.add_source_node(e1.get())
  g.add_dest_node(e2.get())
  g.add_walking_edges()
  
  if operating_condition == "LIVE":
    (path, time) = g.dijkstra(tm.time())
    
    unique_routes = []
    unique_stops = [SRC_ID]
    for route_taken in path:
        if route_taken == SRC_ID or route_taken == DST_ID:
            pass
        else:
            if route_taken[0] not in unique_stops:
                unique_stops.append(route_taken[0])
            if route_taken[1] not in unique_routes and route_taken[1] != "walk":
              unique_routes.append(route_taken[1])

    unique_stops.append(DST_ID)
    print(path, time, unique_routes, unique_stops)

    directions_url = "https://maps.googleapis.com/maps/api/directions/json?"
    
    with open("GoogleMapsAPIKey.txt", "r") as fp:
      google_key = fp.readline()
  
    payload = {"key": google_key, "origin": g.adj_list[SRC_ID]["location"], "destination": g.adj_list[unique_stops[1]]["location"], "mode": "walking"}
    r = requests.get(directions_url, params=payload)
    src_json = json.loads(r.text)
    
    payload["origin"] = g.adj_list[unique_stops[-2]]["location"]
    payload["destination"] = g.adj_list[DST_ID]["location"]
    r = requests.get(directions_url, params=payload)
    dst_json = json.loads(r.text)
    
    display_routes(unique_routes, unique_stops, src_json["routes"][0]["overview_polyline"]["points"], dst_json["routes"][0]["overview_polyline"]["points"], "final_output.png")
    
  elif operating_condition == "SAVED":
    (path, time) = g.dijkstra(saved_arrival_estimates[1])
    
    unique_routes = []
    unique_stops = [SRC_ID]
    for route_taken in path:
        if route_taken == SRC_ID or route_taken == DST_ID:
            pass
        else:
            if route_taken[0] not in unique_stops:
                unique_stops.append(route_taken[0])
            if route_taken[1] not in unique_routes and route_taken[1] != "walk":
              unique_routes.append(route_taken[1])

    unique_stops.append(DST_ID)
    print(path, time, unique_routes, unique_stops)
    
    directions_url = "https://maps.googleapis.com/maps/api/directions/json?"
    
    with open("GoogleMapsAPIKey.txt", "r") as fp:
      google_key = fp.readline()
  
    payload = {"key": google_key, "origin": g.adj_list[SRC_ID]["location"], "destination": g.adj_list[unique_stops[1]]["location"], "mode": "walking"}
    r = requests.get(directions_url, params=payload)
    src_json = json.loads(r.text)
    
    payload["origin"] = g.adj_list[unique_stops[-2]]["location"]
    payload["destination"] = g.adj_list[DST_ID]["location"]
    r = requests.get(directions_url, params=payload)
    dst_json = json.loads(r.text)
    
    display_routes(unique_routes, unique_stops, src_json["routes"][0]["overview_polyline"]["points"], dst_json["routes"][0]["overview_polyline"]["points"], "final_output.png")

#    m2 = Tk()
#    canvas = Canvas(m2, width = 1000, height = 1000)
#    canvas.pack()
#    img = ImageTk.PhotoImage(file="final_output.png")
#    canvas.create_image(0,0, anchor=NW, image=img)
#    m2.mainloop()
    
if __name__ == "__main__":
  m = Tk()
  #w = Canvas(m, width=500, height=500)
  #w.pack()
  
  Label(m, text="Source").grid(row=0)
  Label(m, text="Destination").grid(row=1)
  
  e1 = Entry(m)
  e2 = Entry(m)
  
  e1.grid(row=0, column=1)
  e2.grid(row=1, column=1)
  
  Button(m, 
        text='Go', command=run_program).grid(row=3, column=0, sticky=W, pady=4)
  
  
  m.mainloop()