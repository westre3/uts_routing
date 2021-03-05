from flask import Flask, render_template, request
from uts_routing import run

app = Flask(__name__)

# Force Flask to reload image file
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0
# No caching at all for API endpoints.

@app.route('/', methods=('GET', 'POST'))
def index():
  if request.method == "POST":
    display_image = True
    display_directions = True
    if request.form['locationSelect'] == 'predefinedLocation':
      location = request.form['predefinedLocationChoice']
      loc_lat = None
      loc_lng = None
    elif request.form['locationSelect'] == 'customLocation':
      location = None
      loc_lat = request.form['locLat']
      loc_lng = request.form['locLng']
    else:
      # error
      pass

    if request.form['destinationSelect'] == 'predefinedDestination':
      destination = request.form['predefinedDestinationChoice']
      dst_lat = None
      dst_lng = None
    elif request.form['destinationSelect'] == 'customDestination':
      destination = None
      dst_lat = request.form['dstLat']
      dst_lng = request.form['dstLng']
    else:
      # error
      pass

    image_name, directions = run(location, loc_lat, loc_lng, destination, dst_lat, dst_lng)
  else:
    display_image = False
    display_directions = False
    image_name = None
    directions = None

  return render_template('index.html', display_image=display_image, display_directions=display_directions, image_name=image_name, directions=directions)
