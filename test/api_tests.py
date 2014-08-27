import sys, os
sys.path.append(os.path.abspath('../app'))

import app
import unittest, json, random

class FoodTrucksTests(unittest.TestCase):

    def setUp(self):
        self.app = app.app.test_client()

    def tearDown(self):
        pass

    def test_main_app(self):
        """
        Tests the main application page.
        """
        resp = self.app.get('/')
        # ensure relevant pieces of UI are returned
        assert 'Foggy Fork' in resp.data
        assert 'A San Francisco Food Truck Map' in resp.data
        assert 'Where in the fog are you looking for food?' in resp.data
        assert '<div id="map-canvas"></div>' in resp.data

    def test_trucks_api(self):
        """
        Tests the JSON returned from the trucks API.
        """
        resp = self.app.get('/trucks')
        self.assertEqual(resp.status_code, 200)

        # ensure proper JSON is returned
        data = json.loads(resp.data)
        assert 'resp' in data
        for item in data['resp']:
            # address is not actually required
            assert 'name' in item
            assert 'fooditems' in item
            assert 'latitude' in item
            assert 'longitude' in item
            assert 'schedule' in item

    def test_trucks_api_food_query_string(self):
        """
        Tests that filtering by food works correctly.
        """
        query_items = ["donut", "hot dog", "taco", "chocolate", "soda"]
        for food in query_items:
            resp = self.app.get('/trucks?food=%s' % food)
            self.assertEqual(resp.status_code, 200)

            data = json.loads(resp.data)['resp']
            for item in data:
                assert food in item['fooditems'].lower()

    def test_trucks_api_bounds_query_string(self):
        """
        Tests that filtering by bounds works correctly.
        """
        # SF boundary coordinates - we want to test within these
        swBound = (37.708418, -122.500943)
        neBound = (37.812780, -122.383870)

        for i in range(0, 5):
            # generate some random boundaries to test within
            swLat = random.uniform(swBound[0], neBound[0])
            swLng = random.uniform(swBound[1], neBound[1])
            neLat = random.uniform(swBound[0], neBound[0])
            neLng = random.uniform(swBound[1], neBound[1])
            query_bounds = ",".join([str(x) for x in [swLat, swLng, neLat, neLng]])

            # make the request
            resp = self.app.get('/trucks?bounds=%s' % query_bounds)
            self.assertEqual(resp.status_code, 200)

            # ensure the returned items fall in the correct bounds
            data = json.loads(resp.data)['resp']
            for item in data:
                lat = float(item['latitude'])
                lng = float(item['longitude'])
                assert lat >= swLat
                assert lat <= neLat
                assert lng >= swLng
                assert lng <= neLng

    def test_trucks_api_empty_food(self):
        """
        Tests an empty response with food query parameter.
        (uses a nonexistant food item)
        """
        resp = self.app.get('/trucks?food=asfdasdf')
        self.assertEqual(resp.status_code, 200)

        expected = '{ "resp": [] }'
        self.assertEqual(expected.split(), resp.data.split())

    def test_trucks_api_empty_food(self):
        """
        Tests an empty response with bounds query parameter.
        (uses the same coordinate for NE and SW bounds)
        """
        resp = self.app.get('/trucks?bounds=37.74552131083975,-122.45653323673707,37.74552131083975,-122.45653323673707')
        self.assertEqual(resp.status_code, 200)

        expected = '{ "resp": [] }'
        self.assertEqual(expected.split(), resp.data.split())

    def test_trucks_api_error(self):
        """
        Tests a 404 error.
        """
        resp = self.app.get('/asfdasdf')
        self.assertEqual(resp.status_code, 404)
        assert "NOT FOUND" in resp.status

if __name__ == '__main__':
    unittest.main()