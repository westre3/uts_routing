from flask import Flask, render_template, request
from uts_routing import run
from data_structures import location_lookup, west_longitude_limit, east_longitude_limit, north_latitude_limit, south_latitude_limit

app = Flask(__name__)

# Force Flask to reload image file
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0
# No caching at all for API endpoints.



@app.route('/', methods=('GET', 'POST'))
def index():
  if request.method == "POST":
    error = ""

    if 'locationSelect' not in request.form:
      error = "invalid_selection"
    elif request.form['locationSelect'] == 'predefinedLocation':
      location = request.form['predefinedLocationChoice']
      loc_lat = None
      loc_lng = None
    elif request.form['locationSelect'] == 'customLocation':
      location = None
      if request.form['locLat'] == "" or request.form['locLng'] == "":
        error = "invalid_selection"
      else:
        loc_lat = request.form['locLat']
        loc_lng = request.form['locLng']


        if float(loc_lng) < west_longitude_limit or float(loc_lng) > east_longitude_limit or \
           float(loc_lat) < north_latitude_limit or float(loc_lat) > south_latitude_limit:
          error = "out_of_bounds"
    else:
      error = "unknown"

    if error != "":
      display_image = False
      display_directions = False
      display_graph = False
      map_image_name, directions, graph_image_name = None, None, None

    elif 'destinationSelect' not in request.form:
      error = "invalid_selection"
    elif request.form['destinationSelect'] == 'predefinedDestination':
      destination = request.form['predefinedDestinationChoice']
      dst_lat = None
      dst_lng = None
    elif request.form['destinationSelect'] == 'customDestination':
      destination = None
      if request.form['dstLat'] == "" or request.form['dstLng'] == "":
        error = "invalid_selection"
      else:
        dst_lat = request.form['dstLat']
        dst_lng = request.form['dstLng']

        if float(dst_lng) < west_longitude_limit or float(dst_lng) > east_longitude_limit or \
           float(dst_lat) < north_latitude_limit or float(dst_lat) > south_latitude_limit:
          error = "out_of_bounds"
    else:
      error = "unknown"

    if error != "":
      display_image = False
      display_directions = False
      display_graph = False
      map_image_name, directions, graph_image_name = None, None, None
    else:
      display_image = True
      display_directions = True
      display_graph = 'display_graph' in request.form
      map_image_name, directions, graph_image_name = run(location, loc_lat, loc_lng, destination, dst_lat, dst_lng, display_graph)

  else:
    error = ""
    display_image = False
    display_directions = False
    display_graph = False
    map_image_name, directions, graph_image_name = None, None, None

  return render_template('index.html', locations=location_lookup.keys(), display_image=display_image,
                         display_directions=display_directions, display_graph=display_graph,
                         map_image_name=map_image_name, directions=directions,
                         graph_image_name=graph_image_name, error=error)
