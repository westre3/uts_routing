# UTS Routing

This is a tool written in Python that combines data from UVA, TransLoc, and Google to find the fastest route between locations on UVA's grounds using UVA's University Transportation System (UTS).

## Installation
To run this tool, you'll need 3 things:

### Flask
[Flask](https://flask.palletsprojects.com/en/1.1.x/) is a lightweight framework for web apps that this project uses for a simple user interface. It can be installed simply with `pip install Flask`. More detailed installation instructions can be found [here](https://flask.palletsprojects.com/en/1.1.x/installation/).

### Google API Key
This project uses several of Google's APIs, so you need to set up a [Google Cloud Console](https://developers.google.com/maps/documentation/embed/cloud-setup) and get an API key. This requires payment information and could technically start billing you, but the first $300 worth of API calls are free. Once you have  an API key, the codebase expects you to put it in a file named `GoogleMapsAPIKey.txt`.

### RapidAPI Key
This project uses the TransLoc API, available via the RapidAPI marketplace, to get live information about bus locations and arrival estimates. You'll need to [create an account](https://docs.rapidapi.com/docs/account-creation-and-settings) with RapidAPI and then create a project, which will assign you an API Key. You can access paid APIs through RapidAPI, but TransLoc is free, so you shouldn't need to worry about billing. Once you get your key, place it in a file named `TransLocKey.txt`.

## Running
Once you've installed Flask and obtained the necessary API keys, running the project is very straightforward. Flask requires you to set up the `FLASK_APP` environment variable to the directory where you downloaded the code and the `FLASK_ENV` environment variable to `production`. Then, you can start the Flask server with the command `flask run`. Flask will give you an IP address and port to point your favorite web browser at.
