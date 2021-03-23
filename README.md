# UTS Routing

This is a tool written in Python that combines live data from UVA, TransLoc, and Google to find the fastest route between locations on UVA's grounds using UVA's University Transportation System (UTS) in real time.

## Installation
To run this tool, you'll need 3 things:

### Flask
[Flask](https://flask.palletsprojects.com/en/1.1.x/) is a lightweight framework for web apps that this project uses for a simple user interface. It can be installed simply with `pip install Flask`. More detailed installation instructions can be found [here](https://flask.palletsprojects.com/en/1.1.x/installation/).

### Google API Key
This project uses several of Google's APIs, so you need to set up a [Google Cloud Console](https://developers.google.com/maps/documentation/embed/cloud-setup) and get an API key. This requires payment information and could technically start billing you, but the first $300 worth of API calls are free. Once you have  an API key, the codebase expects you to put it in a file named `GoogleMapsAPIKey.txt`.

### RapidAPI Key
This project uses the TransLoc API, available via the RapidAPI marketplace, to get live information about bus locations and arrival estimates. You'll need to [create an account](https://docs.rapidapi.com/docs/account-creation-and-settings) with RapidAPI and then create a project, which will assign you an API Key. You can access paid APIs through RapidAPI, but TransLoc is free, so you shouldn't need to worry about billing. Once you get your key, place it in a file named `TransLocKey.txt`.

## Running
Once you've installed Flask and obtained the necessary API keys, running the project is very straightforward. Flask requires you to set up the `FLASK_APP` and `FLASK_ENV` environment variables. These can be set as shown below:

    export FLASK_APP=/path/to/this/directory/uts_routing/display.py
    export FLASK_ENV=development

Then, you can start the Flask server with the command `flask run`. Flask will give you an IP address and port to point your favorite web browser at. You should see a screen that looks like this:

![Image of user interface before running](https://github.com/westre3/uts_routing/blob/master/example_images/before_running.png)

Once you select locations or type in latitude and longitude values, the software will pull live bus information, calculate the fastest route to your destination, and display the image and directions! Here's an example of how to get from Scott Stadium to the parking at John Paul Jones Arena (a route that I've taken myself many times).

![Image of user interface after running](https://github.com/westre3/uts_routing/blob/master/example_images/after_running.png)
