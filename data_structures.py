import math
import itertools
import requests
from heapq import *

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
  def __init__(self, stop_id, name, location):

    # The unique ID number of the stop
    self.stop_id = stop_id

    # The English name of the stop
    self.name = name

    # Soonest time at which we could reach this node (for use in Dijkstra)
    self.time = math.inf

    # Whether or not this node has been visited (for use in Dijkstra)
    self.unvisited = True

    # The directed edge from a previous node to this node along the fastest
    # path from SRC (for use in Dijkstra)
    self.p = None

    # The directed edge from this node to the next node along the fastest
    # path from SRC (for use in Dijkstra)
    self.n = None

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
  def __init__(self, from_stop, to_stop, route_id, name, walking_time=None):

    # The source node of this directed edge
    self.from_stop = from_stop

    # The destination node of this directed edge
    self.to_stop = to_stop

    # The unique route ID that this edge corresponds to
    self.route_id = route_id

    # The English name of the route this edge corresponds to
    self.name = name

    # If this is a walking edge, the time required to walk from from_stop to
    # to_stop. If this is not a walking edge, None.
    self.walking_time = walking_time

# A class to hold the actual graph we'll be working with
class Graph:
  def __init__(self):

    # A mapping of stop IDs to nodes in the graph
    self.nodes = {}

    # A mapping of stop IDs to the list of edges the corresponding node in the
    # graph has
    self.adj_list = {}

# Get building names, latitude, longitude from UVA Dev Hub
buildings = requests.get('https://api.devhub.virginia.edu/v1/facilities').json()
location_lookup = {}
for building in buildings:
  if building["Latitude"] is not None and building["Longitude"] is not None:
    location_lookup[building["Name"].title()] = f'{building["Latitude"]},{building["Longitude"]}'

# Sort alphabetically by building name
location_lookup = dict(sorted(location_lookup.items()))


# location_lookup = {
# "AFC" : "38.0329,-78.5134",
# "Fontaine Research Park" : "38.0246,-78.5261",
# "Gilmer Hall" : "38.0342,-78.5128",
# "Gooch/Dillard" : "38.0291,-78.5182",
# "Hereford" : "38.0301,-78.5196",
# "John Paul Jones Arena" : "38.0460,-78.5068",
# "O Hill" : "38.0348,-78.5152",
# "Rice Hall" : "38.0316,-78.5108",
# "Scott Stadium" : "38.0311,-78.5137",
# "Thornton Hall" : "38.0333,-78.5097"
# }

# Place ID lookup for Google APIs. This dictionary is currently unused, but
# will become very useful if Google ever adds support for place IDs to their
# Static Maps API
place_id_lookup = {
  "Scott Stadium" : "ChIJ83CLDFyGs4kRlpbwbea2AWc",
  "Rice Hall"     : "ChIJNVN8Z1uGs4kR7JcEE4iqkGQ",
  "Thornton Hall" : "ChIJYUh6OluGs4kR677pkwWBd7E",
  "John Paul Jones Arena" : "ChIJda7wKE2Gs4kRzsMO7thzcw4"
}

# Latitude and longitude limits of Charlottesville, VA
west_longitude_limit = -78.523574
east_longitude_limit = -78.447214
north_latitude_limit = 38.009506
south_latitude_limit = 38.070897