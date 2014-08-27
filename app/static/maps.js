var foodTrucks = function () {
    /* something new to me */
    "use strict";

    /* default map center - SF */
    var mapCenter = new google.maps.LatLng(37.7833, -122.4167),
    /* default zoom with and without geolocation */
    defaultGeoZoom = 15,
    defaultZoom = 13,

    /* the google map*/
    map = new google.maps.Map($("#map-canvas")[0], {
        center: mapCenter,
        zoom: defaultZoom
    }),

    /* the search box and google places autocomplete */
    searchBox = new google.maps.places.SearchBox($('#search')[0]),

    /* a food truck marker icon */
    mapMarkerIcon = {
        url: "static/images/foodtruck.png",
        scaledSize: new google.maps.Size(26, 45),
        origin: new google.maps.Point(0, 0),
        anchor: new google.maps.Point(0, 0)
    },

    /* a search item marker icon */
    searchMarkerIcon = {
        url: "static/images/searchpin.png",
        scaledSize: new google.maps.Size(26, 45),
        origin: new google.maps.Point(0, 0),
        anchor: new google.maps.Point(0, 0)
    },

    /* the search marker and dictionary of markers */
    searchMarker = new google.maps.Marker({
        map: map,
        animation: google.maps.Animation.DROP,
        icon: searchMarkerIcon
    }),
    markers = {},

    /* an info window that gives more details about a marker */
    infoWindow = new google.maps.InfoWindow({
        content: "",
        maxWidth: 250
    }),

    /**
     * Adds map event listeners - does this only on the first bounds change.
     * This is a little funky due to the issue listed here: 
     *      https://code.google.com/p/gmaps-api-issues/issues/detail?id=1371
     */
    addMapListeners = function () {
        google.maps.event.addListenerOnce(map, 'bounds_changed', function () {
            /* revist the markers within the new bounds on zoom change */
            google.maps.event.addListener(map, 'zoom_changed', function () {
                onMapChange(map);
            });
            /* revist the markers within the new bounds at the end of dragging map */
            google.maps.event.addListener(map, 'dragend', function () {
                onMapChange(map);
            });

            /* bias the search box results to be within current map bounds */
            var bounds = map.getBounds();
            searchBox.setBounds(bounds);

            /* set the initial zoom */
            map.setZoom(defaultGeoZoom);
        });
    },

    /**
     * Callback function to be used when the map changes zoom level or is dragged.
     */
    onMapChange = function () {
        /* the new map bounds */
        var bounds = map.getBounds(),
        /* create a new query string with the current bounds */
        queryString = constructQueryString(bounds);

        /* get truck data and add a map marker for each truck */
        $.getJSON($SCRIPT_ROOT + '/trucks' + queryString, function (data) {
            var trucks = data.resp;

            /* handle any error responses */
            handleRequestError(trucks);

            /* for each truck, drop the marker if it doesn't already exist */
            $.each(trucks, function (i) {
                setTimeout(function () {
                    var key = String(trucks[i].latitude) + String(trucks[i].longitude);
                    if (markers[key] === undefined) {
                        markers[key] = createMarker(map, trucks[i]);
                    } else if (markers[key].map === null) {
                            markers[key].setMap(map);
                    }
                }, i * 5);
            });
        });
    },

    /**
     * Adds a listener to detect toggle button state changes and update
     * the map accordingly.
     */
    addToggleButtonListener = function () {
        /* update the map based on toggle button state changes */
        $('.toggle-btn').click(function () {
            $(this).toggleClass("toggle-btn-down");

            /* get the updated query string */
            var bounds = map.getBounds(),
            queryString = constructQueryString(bounds);

            /* get the matching markers and update map */
            $.getJSON($SCRIPT_ROOT + '/trucks' + queryString, function (data) {
                var trucks = data.resp,
                matchingKeys = [];

                /* handle any error responses */
                handleRequestError(trucks);

                /* compile a list of matching markers */
                $.each(trucks, function (i) {
                    matchingKeys.push(String(trucks[i].latitude) + String(trucks[i].longitude));
                });

                /* go through existing markers and remove from map if not matching */
                var key;
                for (key in markers) {
                    if (markers.hasOwnProperty(key)) {
                        if (matchingKeys.indexOf(key) < 0) {
                            markers[key].setMap(null);
                        } else {
                            markers[key].setMap(map);
                        }
                    }
                }
            });
        });
    },

    /**
     * Adds a listener to detect changes in the search box items and updates the map
     * accordingly.
     */
    addPlaceSearchListener = function () {
        /* add a listener to zoom the map on a selected search box item */
        google.maps.event.addListener(searchBox, 'places_changed', function () {
            /* get the top search result - later on we can extend to handle more results */
            var topResult = searchBox.getPlaces()[0],
            bounds = new google.maps.LatLngBounds();

            /* add a marker and fit the map bounds appropriately */
            searchMarker.setPosition(topResult.geometry.location);
            searchMarker.setTitle(topResult.name);
            bounds.extend(topResult.geometry.location);

            /* update the map bounds and zoom */
            map.fitBounds(bounds);
            map.setZoom(defaultGeoZoom);
        });
    },

    /*
     * Initializes any DOM element listeners.
     */
    addDOMListeners = function () {
        /* Clear the search box after losing focus */
        $("#search").focus(function () {
            $(this).val("");
        });
    },

    /**
     * Attempts to use HTML5 geolocation to get the user's current location
     * and adds a blue dot to the map at that point.
     */
    geolocate = function (map) {
        /* HTML5 geolocation */
        if (navigator.geolocation) {
            /* on successful geolocation, center the map at that location */
            navigator.geolocation.getCurrentPosition(function (position) {
                map.setCenter(new google.maps.LatLng(position.coords.latitude, position.coords.longitude));
                map.setZoom(defaultGeoZoom + 1);
            }, function (error) {
                /* handle error most likely thrown if user denies location services */
                handleGeoError();
            }, {
                /* timeout after 5 seconds and re-use same location within 60 seconds*/
                timeout: 5000,
                maximumAge: 60000
            });

            /* add a listener to update the position if necessary */
            navigator.geolocation.watchPosition(function (position) {
                /* upon clicking the geolocation button, re-center map around the current position*/
                $("#geolocate").click(function () {
                    map.setCenter(new google.maps.LatLng(position.coords.latitude, position.coords.longitude));
                    map.setZoom(defaultGeoZoom + 1);
                });
            });
        } else {
            /* handle no HTML5 support */
            handleGeoError();
        }

        /* add a geolocation marker to the map */
        var geomarker = new GeolocationMarker(map);
        geomarker.setCircleOptions({ visible: false });
    },

    /**
     * Adds an error message above the search bar indicating that location services are unavailable.
     */
    handleGeoError = function () {
        map.setCenter(mapCenter);
        map.setZoom(defaultZoom);
        $("#main").append("<div class='geo-error'><p>Your browser does not support geolocation or you have geolocation turned off.</p></div>");
    },

    /**
     * Handles a dataset request error by hiding the map and adding an error message in its place.
     */
    handleRequestError = function (response) {
        if (response.error !== undefined) {
            $("#map-canvas").hide();
            $("#main").append("<div class='map-error'><p>" + response.error + "</p></div>");
        }
    },

    /**
     * Creates a new marker and adds it to the map with the relevant infoWindow details.
     */
    createMarker = function (map, truckData) {
        /* initialize the truck's data */
        var name = truckData.name,
        location = new google.maps.LatLng(truckData.latitude, truckData.longitude),
        marker = new google.maps.Marker({
            position: location,
            map: map,
            animation: google.maps.Animation.DROP,
            title: name,
            icon: mapMarkerIcon
        });

        /* add a click listener to pop up an info window on clicking the marker */
        google.maps.event.addListener(marker, 'click', function () {
            infoWindow.content = getInfoWindowContent(name, truckData.address, truckData.fooditems, truckData.schedule);
            infoWindow.open(map, marker);
        });
        return marker;
    },

    /**
     * Constructs a query string based on the given bounds and whether or not the 
     * toggle buttons are turned on or off.
     */
    constructQueryString = function (bounds) {
        var queryString = "";

        /* search within current map boundaries */
        if (bounds !== undefined) {
            var ne = bounds.getNorthEast(),
                sw = bounds.getSouthWest();
            queryString = "?bounds=" + sw.lat() + "," + sw.lng() + "," + ne.lat() + "," + ne.lng();

            /* search for matching food items */
            if ($(".toggle-btn-down").length > 0) {
                queryString += "&food=";
                $(".toggle-btn-down").each(function () {
                    queryString += ($(this).attr('id') + ",");
                });
            }
        }
        return queryString;
    },

    /**
     * Constructs the HTML for the info window and the given details.
     */
    getInfoWindowContent = function (name, address, fooditems, schedule) {
        return '<div><h3>' + name + '</h3>' +
                    '<div><p>' + address + '</p>' +
                    '<p>' + fooditems + '</p>' +
                    '<p><a href=' + schedule + ' target="_blank">Download Schedule</a></p></div></div>';
    },

    /**
     * Initializes everything necessary for the map performance.
     */
    initialize = function () {
        /* add all listeners */
        addMapListeners();
        addToggleButtonListener();
        addPlaceSearchListener();
        addDOMListeners();

        /* add the geolocation pin */
        geolocate(map);
    };

    /* call the initialization function */
    google.maps.event.addDomListener(window, 'load', initialize());
};

/* set everthing up when page is ready */
$(document).ready(function () {
    foodTrucks();
});
