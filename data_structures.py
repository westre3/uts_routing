import math
import itertools
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