#!/usr/bin/env python

from flask import *
from urllib2 import urlopen, HTTPError
import json, decimal

app = Flask(__name__, static_folder='static')


""" Configuation Information """
GOOGLE_API_KEY = "AIzaSyDDnh_ZW0BjTrbmzct4c8ZipZUnt_oVgi4"      # google API key
SF_DATA_URL = "http://data.sfgov.org/resource/rqzj-sfat.json"   # the dataset location


""" API Functions """
class FoodTrucks():
    @app.route('/')
    def index():
        """
        Renders the home page of the application.
        """
        return render_template('index.html', api_key=GOOGLE_API_KEY)

    @app.errorhandler(400)
    @app.errorhandler(403)
    @app.errorhandler(404)
    @app.errorhandler(500)
    def handle_http_error(error):
        """
        Handles common errors by displaying a custom page.
        """
        app.logger.error(error)
        return render_template('error.html', error=error, description=error.get_description()), error.code

    @app.route('/docs')
    def get_api_documentation():
        return send_from_directory(app.static_folder, "docs.pdf")

    @app.route('/trucks')
    def get_food_truck_data():
        """
        The main API resource - handles incoming requests, pulls food truck permit
        data from data.sfgov.org, filters the data based on the request, and returns
        the relevant food truck information as a JSON response.

        **Query parameters:**
            *?bounds* - Takes in a list of four decimals representing the southwest and northeast
                        latitude and longitude coordinates of the bounding box within which the truck
                        permit must be located.

                        Example :   ``GET /trucks?bounds=37.74,-122.45,37.75,-122.4``
                                    Returns all trucks located within the bounds defined by the SW coordinate
                                    (37.74, -122.37) and the NE coordinate (37.75, -122.4)

            *?food* -   Takes in a list of food items the trucks must serve. If more than one item is given, each
                        truck returned must serve at least one item in the list, but not necessarily all items.

                        Example :   ``GET /trucks?food=donut,burger``
                                    Returns all trucks that serve at least donuts or burgers, based on their
                                    food item descriptions in the dataset.

        **Example Response:**
            ::

                { "resp": [
                    {
                      "address": "501 02ND ST", 
                      "fooditems": "Hot Dogs, Hamburgers, Nachos, Steaks, Pastas, Asian Dishes, Tri-Tip Sandwiches, Sodas & Water", 
                      "latitude": "37.7831711181211", 
                      "longitude": "-122.392901049469", 
                      "name": "Linda's Catering", 
                      "schedule": "http://bsm.sfdpw.org/PermitsTracker/reports/report.aspx?title=schedule&report=rptSchedule&params=permit=14MFF-0013&ExportPDF=1&Filename=14MFF-0013_schedule.pdf"
                    }
                  ]
                }
        """
        # parse the query parameters
        # get the bounds within which the truck must fall - if no bounds requested then don't limit the search
        bounds = request.args.get('bounds')
        if bounds != None:
            bounds = [float(x) for x in bounds.split(",")]
            sw = { "lat": bounds[0], "lng": bounds[1] }
            ne = { "lat": bounds[2], "lng": bounds[3] }

        # get the specific food items the trucks must serve - if no items requested then don't limit the search
        food_items = request.args.get("food")
        if food_items != None:
            food_items = [x for x in food_items.split(",") if x]

        # get the truck name
        requested_name = request.args.get("name")

        # grab the dataset for all trucks
        try:
            data = json.load(urlopen(SF_DATA_URL))
        except HTTPError:
            app.logger.error("Error - unable to open the dataset URL %s" % SF_DATA_URL)
            return Util.constructErrorResponse("Unable to load food truck data. Try again later.", 500)

        # parse and extract relevant details for each truck
        trucks = []
        for item in data:
            truck_data = {}
            # get the truck name and location
            truck_data['name'] = item['applicant']

            # only return trucks with approved permits and locations
            if item['status'] == "APPROVED":
                # in the future, we can do more work to locate trucks without specific coordinates,
                # but for now we will focus on ones with explicit locations
                if 'location' in item:
                    loc = item['location']
                    point = { "lat": float(loc['latitude']), "lng": float(loc['longitude']) }

                    # only return data if it is within the requested bounds
                    if bounds == None or Util.withinBounds(sw, ne, point):
                        truck_data['latitude'] = loc['latitude']
                        truck_data['longitude'] = loc['longitude']

                        # get some additional information about the truck
                        # in the future we can look at other details as well
                        additional = ['schedule', 'address', 'fooditems']
                        for key in additional:
                            if key in item:
                                if key == 'fooditems':
                                    # do a little work to make the list more readable
                                    truck_data[key] = item[key].replace(":", ",")
                                else:
                                    truck_data[key] = item[key]

                        # add the data for this truck only if one of the food query items match
                        if food_items == None:
                            if requested_name != None:
                                if truck_data['name'].lower() == requested_name.lower():
                                    trucks.append(truck_data)
                            else:
                                trucks.append(truck_data)
                        else:
                            for item in food_items:
                                if 'fooditems' in truck_data and Util.containsSubstring(truck_data['fooditems'], item):
                                    if requested_name != None:
                                        if truck_data['name'].lower() == requested_name.lower():
                                            trucks.append(truck_data)
                                    else:
                                        trucks.append(truck_data)

        # return a JSON response
        return jsonify(resp=trucks)

    @app.route('/author')
    def get_candidate_data():
        """
        This resource represents the application author!
        Returns author details as a JSON response.
        """
        data = {
            "name": "Kelsey Tripp",
            "title": "Software Engineer",
            "location": "San Francisco, CA",
            "education": "Brown University Computer Science Sc.B., 2013",
            "current-employer": "NetApp",
            "website": "www.katripp.com",
            "resume": "http://www.katripp.com/resources/KelseyTripp_Resume.pdf"
        }
        return jsonify(resp=data)


""" Utility Functions """
class Util():
    @staticmethod
    def withinBounds(swBounds, neBounds, point):
        """
        Determines if a given point is within the bounds defined by the
        southwest and northeast corners.

        swBounds - a dictionary representing the southwest coordinate with a latitude and longitude
        neBounds - a dictionary representing the northeast coordinate with a latitude and longitude
        point - a dictionary representing a coordinate to test with a latitude and longitude

        Returns True if the point is within the given bounds, False otherwise
        """

        if (point['lat'] < swBounds['lat'] or point['lat'] > neBounds['lat']):
            return False
        elif (point['lng'] < swBounds['lng'] or point['lng'] > neBounds['lng']):
            return False
        else:
            return True

    @staticmethod
    def containsSubstring(searchString, searchItem):
        """
        Determines if a given search item is within a search string.
        Search is case insensitive.

        searchItem - a string representing the item to search for
        searchString - a string in which to look for the searchItem

        Returns True if the searchItem is within the searchString, False otherwise
        """
        return searchItem.lower() in searchString.lower()

    @staticmethod
    def constructErrorResponse(errorMsg, errorCode):
        """
        Constructs an error response.
        """
        error = { "error": errorMsg,
                  "status": errorCode }
        return jsonify(resp=error)


""" The main application """
if __name__ == '__main__':
    app.run()
