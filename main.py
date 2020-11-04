import requests
import json
import math
import time as tm
import sys
from tkinter import *
from PIL import ImageTk,Image
import os
from heapq import *
import itertools
import logging

SRC_ID = "SRC"
DST_ID = "DST"

# Based on the Python docs' example code for using heapq
# I'm using this wrapper class so that two heap elements with equal priorities
# are removed
class PriorityQueue:
  """
  Based on the Python docs' example code for using heapq. I'm using this
  wrapper class for heapq so that two heap elements with equal priorities are
  removed in the order of their insertion and also so that the heap re-orders
  itself when an element's priority is changed.
  """

  def __init__(self):
    self.pq = []
    self.entry_finder = {}
    self.REMOVED = '<removed-task>'
    self.counter = itertools.count()

  def add_task(self, task, priority=0):
    count = next(self.counter)
    entry = [priority, count, task]
    self.entry_finder[task] = entry
    heappush(self.pq, entry)

  def update_task(self, task, priority):
    if task in self.entry_finder:
      self.remove_task(task)
    count = next(self.counter)
    entry = [priority, count, task]
    self.entry_finder[task] = entry
    heappush(self.pq, entry)

  def remove_task(self, task):
    entry = self.entry_finder.pop(task)
    entry[-1] = self.REMOVED

  def pop_task(self):
    while self.pq:
      priority, count, task = heappop(self.pq)
      if task is not self.REMOVED:
        del self.entry_finder[task]
        return task

  def __contains__(self, task):
    return task in self.entry_finder and self.entry_finder[task] is not self.REMOVED

class Node:
  def __init__(self, stop, name, location):

    # The unique ID number of the stop
    self.stop = stop

    # The English name of the stop
    self.name = name

    # For Dijkstra's algorithm
    self.dijkstra = math.inf
    self.unvisited = True
    self.p = None
    self.n = None # to be used only once a path is found
    self.via = None

    # A dictionary of the estimated arrival times at this stop for each route
    self.arrival_times = {}

    # A mapping of arrival times to the vehicle ID arriving at that time
    self.buses = {}

    # The latitude and longitude of the stop
    self.location = location

  # Define < so we can use Node objects in priority queue
  def __lt__(self, other):
    return self.dijkstra < other.dijkstra

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
def parse_uts_data(g, stops, routes, arrival_estimates):

  # Mapping of IDs to names and locations
  stop_lookup = {}
  for stop in stops["data"]:
    stop_lookup[stop["stop_id"]] = {"name": stop["name"], "location": stop["location"]}

  route_lookup = {}
  for route in routes["data"]["347"]:
    route_lookup[route["route_id"]] = route["long_name"]

  running_routes = {}
  for arrival_estimate in arrival_estimates["data"]:
    stop_id = arrival_estimate["stop_id"]

    # If this stop doesn't already exist as a node in the graph, add it
    if stop_id not in g.adj_list:
      g.nodes[stop_id] = Node(stop_id,
                              stop_lookup[stop_id]["name"],
                              stop_lookup[stop_id]["location"])

      g.adj_list[stop_id] = []

      logging.debug(f'Added stop {g.nodes[stop_id].name} with ID {stop_id} and location {g.nodes[stop_id].location["lat"]},{g.nodes[stop_id].location["lng"]} to graph')

    # Create a list of all routes that are currently running
    for arrival in arrival_estimate["arrivals"]:
      route_id = arrival["route_id"]
      vehicle_id = arrival["vehicle_id"]

      # Save one specific vehicle ID for each route to order stops later
      if route_id not in running_routes:
        running_routes[route_id] = vehicle_id

      # Save arrival times and vehicle IDs that correspond to those arrivals
      eta = tm.mktime(tm.strptime(arrival["arrival_at"][:19], "%Y-%m-%dT%H:%M:%S"))
      if route_id not in g.nodes[stop_id].arrival_times:
        g.nodes[stop_id].arrival_times[route_id] = []
      g.nodes[stop_id].arrival_times[route_id].append(eta)
      g.nodes[stop_id].buses[eta] = vehicle_id

  # Add edges between stops in graph
  # I'm doing this by sorting the stops in order of arrival time estimate
  # for a single vehicle ID because the TransLoc API does not list the stops
  # in order
  for route in running_routes:
    stops_on_route = []
    stop_times = {}
    for arrival_estimate in arrival_estimates["data"]:
      stop_id = arrival_estimate["stop_id"]

      for arrival in arrival_estimate["arrivals"]:
        vehicle_id = arrival["vehicle_id"]

        if vehicle_id == running_routes[route]:
          if stop_id not in stops_on_route:
            stops_on_route.append(stop_id)
            stop_times[stop_id] = tm.mktime(tm.strptime(arrival["arrival_at"][:19], "%Y-%m-%dT%H:%M:%S"))

    # Sort routes based on arrival time estimate
    stops_on_route.sort(key = lambda stop : stop_times[stop])

    # Connect stops in order of arrival time estimate
    for i in range(len(stops_on_route)):
      g.adj_list[stops_on_route[i]].append(Edge(stops_on_route[i], stops_on_route[(i+1) % len(stops_on_route)], route, route_lookup[route]))
      logging.debug(f'Added {route_lookup[route]} edge from stop {stop_lookup[stops_on_route[i]]["name"]} with ID {stops_on_route[i]} to stop {stop_lookup[stops_on_route[(i+1) % len(stops_on_route)]]["name"]} with ID {stops_on_route[(i+1) % len(stops_on_route)]}')

def dijkstra(g, current_time):
  logging.debug(f"Current time is {current_time}")

  # Min Heap Priority Queue
  pq = PriorityQueue()

  g.nodes[SRC_ID].dijkstra = current_time

  # Put every node in the priority queue. They've already been marked
  # unvisited.
  for node in g.nodes:
    pq.add_task(g.nodes[node], g.nodes[node].dijkstra)

  while g.nodes[DST_ID] in pq:
    u = pq.pop_task()

    u.unvisited = False

    logging.debug(f"Removed stop {u.name} with ID {u.stop} from Priority Queue. We can reach this stop in {u.dijkstra - current_time} s")

    for e in g.adj_list[u.stop]:
      v = g.nodes[e.to_stop]
      logging.debug(f"Considering edge {e.name} from {u.name} with ID {u.stop} to {v.name} with ID {v.stop}")

      if v.unvisited:

        # Compute the edge weight differently depending on if this is a
        # bus edge or a walking edge
        if e.name == "walking":
          logging.debug(f"This is a walking edge. Comparing {u.dijkstra - current_time} s + {e.walking_time} s to {v.dijkstra - current_time} s")
          if u.dijkstra + e.walking_time < v.dijkstra:
            v.dijkstra = u.dijkstra + e.walking_time
            v.via = e
            pq.update_task(v, v.dijkstra)
            logging.debug(f"This route is faster. Updating v's time to {v.dijkstra - current_time} s")

          else:
            logging.debug(f"This route is not faster.")

        else:
          # Find the next time a bus on e.route is arriving at u.stop
          arrivals = [ar for ar in u.arrival_times[e.route] if ar >= u.dijkstra]

          # If we don't have an arrival estimate for any buses on this route
          # at the current stop, then we assume that we'd have to wait a
          # long time for the next bus (longer than what the TransLoc API
          # returns by default), and thus we don't consider this edge
          if len(arrivals) > 0:
            next_arrival = min(arrivals)
          else:
            continue

          # Find the vehicle ID of the bus arriving at that time
          next_bus = u.buses[next_arrival]

          # Find the first time that the same bus arrives at the next stop
          # after it already arrived at this top. This is the time at which
          # we would arrive at v if we traveled along edge e
          arrivals_at_v = [ar for ar in v.arrival_times[e.route] if v.buses[ar] == next_bus and ar > next_arrival]

          # If the next bus to arrive at the current stop has no arrival
          # estimates at the next stop, then we don't consider this edge
          if len(arrivals_at_v) > 0:
            arrival_at_v = min(arrivals_at_v)
          else:
            continue

          logging.debug(f"This is a bus edge. Bus {next_bus} will arrive at u at time {next_arrival - current_time} s and at v at time {arrival_at_v - current_time}")
          logging.debug(f"Comparing {arrival_at_v - current_time} s to {v.dijkstra - current_time} s")

          if arrival_at_v < v.dijkstra:
            v.dijkstra = arrival_at_v
            v.via = e
            pq.update_task(v, v.dijkstra)
            logging.debug(f"This route is faster. Updating v's time to {v.dijkstra - current_time} s")

          else:
            logging.debug(f"This route is not faster.")

  path = [DST_ID]
  while SRC_ID not in path:
    current_stop = g.nodes[path[0]]
    prev_stop = g.nodes[current_stop.via.from_stop]
    prev_stop.n = current_stop.via
    path.insert(0, prev_stop.stop)
    logging.debug(f"Prepended stop {prev_stop.name} with ID {prev_stop.stop} to path")

  # If our path has only walking edges from SRC to DST, simply make the path
  # two elements long. Google sometimes shows that it's faster to walk from
  # SRC to one or more stops, then to DST rather than to walk directly from
  # SRC to DST. This corrects that issue.
  all_walking = True
  for node in path[:-1]:
    if g.nodes[node].n.name != "walking":
      all_walking = False
      break

  if all_walking:
    path = [SRC_ID, DST_ID]

  for i in range(len(path)):
    logging.debug(f"path[{i}] = {g.nodes[path[i]].name} with ID {g.nodes[path[i]].stop}")

  return path


def display_routes(g, path, stops, routes, image_file):
  segments_url = "https://transloc-api-1-2.p.rapidapi.com/segments.json"

  # Read in TransLoc API Key
  try:
    with open("TransLocKey.txt", "r") as fp:
      transloc_key = fp.readline()
  except FileNotFoundError:
    err = f"Cannot read TransLoc key file"
    logging.critical(err)
    sys.exit(err)

  segments_url = "https://transloc-api-1-2.p.rapidapi.com/segments.json"
  host = "transloc-api-1-2.p.rapidapi.com"
  agencies = "347" # UVA
  headers = {"x-rapidapi-host": host, "x-rapidapi-key": transloc_key}
  transloc_payload = {"agencies": agencies}

  unique_routes = set()
  for stop in path[:-1]: # There is no next stop for DST
    if g.nodes[stop].n.route:
      unique_routes.add(g.nodes[stop].n.route)

  # Data structure to lookup route colors
  color_lookup = {}
  for route in routes["data"]["347"]:
    if route["route_id"] in unique_routes:
      color_lookup[route["route_id"]] = route["color"]

  # Get the encoded polylines for the routes on our path.
  # I have to request separate responses for each route in unique_routes because
  # the TransLoc API provides no way to distinguish which encoded polylines
  # correspond to which route when I request multiple routes.
  static_maps_payload = []
  for route in unique_routes:
    transloc_payload["routes"] = route

    try:
      segments_response = requests.get(segments_url, headers=headers, params=transloc_payload)
    except ConnectionError:
      err = f"Connection error when attempting to access {segments_url}"
      logging.critical(err)
      sys.exit(err)

    if not segments_response.ok:
      logging.critical(f"When attempting to access {segments_url}, received Status Code {segments_response.status_code} for Reason {segments_response.reason}.")
      sys.exit("Unable to access TransLoc API")

    segments_json = segments_response.json()

    for polyline in segments_json["data"].values():
      static_maps_payload.append(("path", f'color:0x{color_lookup[route]}|enc:{polyline}'))

  directions_url = "https://maps.googleapis.com/maps/api/directions/json"

  # Read in Google API Key
  try:
    with open("GoogleMapsAPIKey.txt", "r") as fp:
      google_key = fp.readline()
  except FileNotFoundError:
    err = f"Cannot read Google key file"
    logging.critical(err)
    sys.exit(err)

  # Use Google Directions API to get encoded polylines for walking edges
  directions_payload = {"origin"      : f'{g.nodes[path[0]].location["lat"]},{g.nodes[path[0]].location["lng"]}',
                        "destination" : f'{g.nodes[path[1]].location["lat"]},{g.nodes[path[1]].location["lng"]}',
                        "key"         : google_key,
                        "mode"        : "walking"}

  try:
    directions_response = requests.get(directions_url, params=directions_payload)
  except ConnectionError:
    err = f"Connection error when attempting to access {directions_url}"
    logging.critical(err)
    sys.exit(err)

  if not directions_response.ok:
    logging.critical(f"When attempting to access {directions_url}, received Status Code {directions_response.status_code} for Reason {directions_response.reason}.")
    sys.exit("Unable to access Google Static Maps API")

  directions_json = directions_response.json()

  static_maps_payload.append(("path", f'color:red|enc:{directions_json["routes"][0]["overview_polyline"]["points"]}'))

  # We only need another line if the path is not to walk from SRC to DST
  if len(path) > 2:
    directions_payload = {"origin"      : f'{g.nodes[path[-2]].location["lat"]},{g.nodes[path[-2]].location["lng"]}',
                          "destination" : f'{g.nodes[path[-1]].location["lat"]},{g.nodes[path[-1]].location["lng"]}',
                          "key"         : google_key,
                          "mode"        : "walking"}

    try:
      directions_response = requests.get(directions_url, params=directions_payload)
    except ConnectionError:
      err = f"Connection error when attempting to access {directions_url}"
      logging.critical(err)
      sys.exit(err)

    if not directions_response.ok:
      logging.critical(f"When attempting to access {directions_url}, received Status Code {directions_response.status_code} for Reason {directions_response.reason}.")
      sys.exit("Unable to access Google Static Maps API")

    directions_json = directions_response.json()

    static_maps_payload.append(("path", f'color:red|enc:{directions_json["routes"][0]["overview_polyline"]["points"]}'))

  # Parameters for Google Static Maps API
  static_maps_url = "https://maps.googleapis.com/maps/api/staticmap"
  size = "500x500"

  static_maps_payload += [("size", size), ("key", google_key)]

  # Build up payload to Google API with markers for the stops on the path
  label = 'A'
  for stop  in path:

    # We display markers for SRC and DST and color them red
    if stop in [SRC_ID, DST_ID]:
      color = "red"

    # We display markers for every stop at which we change buses
    elif g.nodes[stop].via.route != g.nodes[stop].n.route:

      # If we're getting on a different bus, we color the marker the color of
      # the route that we're getting on
      if g.nodes[stop].n.route:
        color = color_lookup[g.nodes[stop].n.route]

      # If we're getting off of a bus and walking to DST, we color the makerer
      # the color of the route we were just on
      else:
        color = color_lookup[g.nodes[stop].via.route]

    # We don't display markers for stops that we simply pass through on a bus
    else:
      continue

    static_maps_payload.append(("markers", f'size:mid|label:{label}|color:0x{color}|{g.nodes[stop].location["lat"]},{g.nodes[stop].location["lng"]}'))

    label = chr(ord(label) + 1)

  try:
    static_maps_response = requests.get(static_maps_url, params=static_maps_payload)
  except ConnectionError:
    err = f"Connection error when attempting to access {static_maps_url}"
    logging.critical(err)
    sys.exit(err)

  if not static_maps_response.ok:
    logging.critical(f"When attempting to access {static_maps_url}, received Status Code {static_maps_response.status_code} for Reason {static_maps_response.reason}.")
    sys.exit("Unable to access Google Static Maps API")

  try:
    with open(image_file, "wb") as fp:
      fp.write(static_maps_response.content)
  except FileNotFoundError:
    err = f"Unable to open image file {image_file} for writing"
    logging.critical(err)
    sys.exit(err)


# Add edges from source to all nodes and from all nodes to destination
# representing walking time using Google Distance Matrix API to find walking
# times
def add_walking_edges(g):
  src_location = g.nodes[SRC_ID].location
  dst_location = g.nodes[DST_ID].location

  # Save stop IDs in a list to simplify code
  stops = [s for s in g.nodes if g.nodes[s].name not in [SRC_ID, DST_ID]]
  stop_locations = [f"{g.nodes[s].location['lat']},{g.nodes[s].location['lng']}" for s in stops]

  google_walking_url = "https://maps.googleapis.com/maps/api/distancematrix/json"
  with open("GoogleMapsAPIKey.txt", "r") as fp:
    key = fp.readline()

  payload = {"origins" : f"{src_location['lat']},{src_location['lng']}",
             "destinations" : "|".join(stop_locations + [f"{dst_location['lat']},{dst_location['lng']}"]),
             "key" : key,
             "mode" : "walking"}

  # Source to stops Google Distance Matrix API request
  # Note that I only need to take into account SRC to DST route in one
  # API call, not both
  try:
    src_to_stops_response = requests.get(google_walking_url, params=payload)
  except ConnectionError:
    err = f"Connection error when attempting to access {google_walking_url}"
    logging.critical(err)
    sys.exit(err)

  if not src_to_stops_response.ok:
    logging.critical(f"When attempting to access {google_walking_url}, received Status Code {src_to_stops_response.status_code} for Reason {src_to_stops_response.reason}.")
    sys.exit("Unable to access Google Distance Matrix API")

  src_to_stops_json = src_to_stops_response.json()

  if src_to_stops_json["status"] != "OK":
    err = f"Google Distance Matrix API status is {src_to_stops_json['status']}"
    logging.critical(err)
    sys.exit(err)

  # Stops to destination Google Distance Matrix API request
  payload = {"origins" : "|".join(stop_locations),
             "destinations" : f"{dst_location['lat']},{dst_location['lng']}",
             "key" : key,
             "mode" : "walking"}

  try:
    stops_to_dst_response = requests.get(google_walking_url, params=payload)
  except ConnectionError:
    err = f"Connection error when attempting to access {google_walking_url}"
    logging.critical(err)
    sys.exit(err)

  if not stops_to_dst_response.ok:
    logging.critical(f"When attempting to access {google_walking_url}, received Status Code {stops_to_dst_response.status_code} for Reason {stops_to_dst_response.reason}.")
    sys.exit("Unable to access Google Distance Matrix API")

  stops_to_dst_json = stops_to_dst_response.json()

  if stops_to_dst_json["status"] != "OK":
    err = f"Google Distance Matrix API status is {stops_to_dst_json['status']}"
    logging.critical(err)
    sys.exit(err)

  # Put both sets of API results in the format of a list of results
  src_to_stops = src_to_stops_json["rows"][0]["elements"]
  stops_to_dst = [row["elements"][0] for row in stops_to_dst_json["rows"]]

  for i in range(len(stops)):

    # Add edge from SRC to stop
    if src_to_stops[i]["status"] == "OK":
      g.adj_list[SRC_ID].append(Edge(SRC_ID, stops[i], None, "walking", src_to_stops[i]["duration"]["value"]))
      logging.debug(f'Added walking edge with travel time {src_to_stops[i]["duration"]["value"]} s from {SRC_ID} to {stops[i]}')
    else:
      logging.critical(f"Google Distance Matrix API status for route from SRC to {g.nodes[stops[i]].name} is {src_to_stops[i]['status']}")
      sys.exit(f"Google Distance Matrix API status is {src_to_stops[i]['status']}")

    # Add edge from stop to DST
    if stops_to_dst[i]["status"] == "OK":
      g.adj_list[stops[i]].append(Edge(stops[i], DST_ID, None, "walking", stops_to_dst[i]["duration"]["value"]))
      logging.debug(f'Added walking edge with travel time {stops_to_dst[i]["duration"]["value"]} s from {stops[i]} to {DST_ID}')
    else:
      logging.critical(f"Google Distance Matrix API status for route from {g.nodes[stops[i]].name} to DST is {stops_to_dst[i]['status']}")
      sys.exit(f"Google Distance Matrix API status is {stops_to_dst[i]['status']}")

  # Add edge from SRC to DST
  g.adj_list[SRC_ID].append(Edge(SRC_ID, DST_ID, None, "walking", src_to_stops[-1]["duration"]["value"]))
  logging.debug(f'Adding walking edge with travel time {src_to_stops[-1]["duration"]["value"]} s from {SRC_ID} to {DST_ID}')




# Some common locations
rice_location = "38.0316,-78.5108"
thornton_location = "38.0333,-78.5097"
jpa_location = "38.0459,-78.5067"
downtown = "38.0292,-78.4773"
colonnade = "38.042702, -78.517687"
colonnade2 = "38.042775,-78.51756"
lile_location = '38.035015,-78.516131'
barracks_location = '38.048796,-78.505219'
lake_monticello = '37.911027,-78.326811'

def conv_to_dict(latlon):
  latlon = latlon.split(',')
  return {"lat" : float(latlon[0]), "lng" : float(latlon[1])}

def run_program():
  source = e1.get()
  destination = e2.get()

  live = True

  # Log information about last run to aid in debugging
  logging.basicConfig(level=logging.DEBUG, filename="logs/last_run.log", filemode="w", format="%(levelname)s : %(message)s")

  if live:
    # URLs for the TransLoc API
    stops_url = "https://transloc-api-1-2.p.rapidapi.com/stops.json"
    routes_url = "https://transloc-api-1-2.p.rapidapi.com/routes.json"
    arrival_estimates_url = "https://transloc-api-1-2.p.rapidapi.com/arrival-estimates.json"

    host = "transloc-api-1-2.p.rapidapi.com"
    agencies = "347" # UVA

    try:
      with open("TransLocKey.txt", "r") as fp:
        transloc_key = fp.readline()
    except FileNotFoundError:
      err = f"Unable to open TransLoc key file"
      logging.critical(err)
      sys.exit(err)

    headers = {"x-rapidapi-host": host, "x-rapidapi-key": transloc_key}
    payload = {"agencies": agencies}

    # Get stops information from TransLoc
    try:
      stops_response = requests.get(stops_url, headers=headers, params=payload)
    except ConnectionError:
      err = f"Connection error when attempting to access {stops_url}"
      logging.critical(err)
      sys.exit(err)

    if not stops_response.ok:
      logging.critical(f"When attempting to access {stops_url}, received Status Code {stops_response.status_code} for Reason {stops_response.reason}.")
      sys.exit("Unable to access TransLoc API")

    stops_json = stops_response.json()

    # Get route information from TransLoc
    try:
      routes_response = requests.get(routes_url, headers=headers, params=payload)
    except ConnectionError:
      err = f"Connection error when attempting to access {routes_url}"
      logging.critical(err)
      sys.exit(err)

    if not routes_response.ok:
      logging.critical(f"When attempting to access {routes_url}, received Status Code {routes_response.status_code} for Reason {routes_response.reason}.")
      sys.exit("Unable to access TransLoc API")

    routes_json = routes_response.json()

    # Get arrival estimates information from TransLoc
    try:
      arrival_estimates_response = requests.get(arrival_estimates_url, headers=headers, params=payload)
    except ConnectionError:
      err = f"Connection error when attempting to accesss {arrival_estimates_url}"
      logging.critical(err)
      sys.exit(err)

    if not arrival_estimates_response.ok:
      logging.critical(f"When attempting to access {arrival_estimates_url}, received Status Code {arrival_estimates_response.status_code} for Reason {arrival_estimates_response.reason}.")
      sys.exit("Unable to access TransLoc API")

    arrival_estimates_json = arrival_estimates_response.json()

    # Get current time
    current_time = tm.time()

    # TODO : Create logs directory if it doesn't exist

    # Save TransLoc results to log files
    try:
      with open("logs/stops.log", "w") as fp:
        json.dump(stops_json, fp)

      with open("logs/routes.log", "w") as fp:
        json.dump(routes_json, fp)

      with open("logs/arrival_estimates.log", "w") as fp:
        json.dump(arrival_estimates_json, fp)

      with open("logs/current_time.log", "w") as fp:
        fp.write(str(current_time))
    except FileNotFoundError:
      err = f"Unable to save TransLoc results to logs"
      logging.error(err)

  else:

    # Read in TransLoc data from log files
    try:
      with open("logs/stops.log", "r") as fp:
        stops_json = json.load(fp)

      with open("logs/routes.log", "r") as fp:
        routes_json = json.load(fp)

      with open("logs/arrival_estimates.log", "r") as fp:
        arrival_estimates_json = json.load(fp)

      with open("logs/current_time.log", "r") as fp:
        current_time = float(fp.readline()[:-1])

    except FileNotFoundError:
      err = "Unable to read saved information from logs"
      logging.critical(err)
      sys.exit(err)

  # Create empty graph
  g = Graph()

  # Build graph with data returned by TransLoc API
  parse_uts_data(g, stops_json, routes_json, arrival_estimates_json)

  # Add source node
  location = conv_to_dict(source)
  g.nodes[SRC_ID] = Node(SRC_ID, SRC_ID, location)
  g.adj_list[SRC_ID] = []
  logging.debug(f"Added source node at location {location['lat']},{location['lng']}")

  # Add destination node
  location = conv_to_dict(destination)
  g.nodes[DST_ID] = Node(DST_ID, DST_ID, location)
  g.adj_list[DST_ID] = []
  logging.debug(f"Added destination node at location {location['lat']},{location['lng']}")

  # Add edges from SRC to every stop and from every stop to DST
  add_walking_edges(g)

  # Run Dijkstra's algorithm on graph
  path = dijkstra(g, current_time)

  # Create image file with Google Static Maps API to show path from SRC to DST
  display_routes(g, path, stops_json, routes_json, "test_image.png")

if __name__ == "__main__":
  m = Tk()

  Label(m, text="Source").grid(row=0)
  Label(m, text="Destination").grid(row=1)

  e1 = Entry(m)
  e2 = Entry(m)

  e1.grid(row=0, column=1)
  e2.grid(row=1, column=1)

  Button(m, text='Find Route', command=run_program).grid(row=2, column=0, sticky=W, pady=4)

  m.mainloop()
