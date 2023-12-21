# Author    : Clinton Lohr
# Date      : 05/30/2023
# Course    : CS 493 - Cloud Application Development
# Assignment: Portfolio - Final Project


from google.cloud import datastore
from flask import request, Blueprint
import constants
from validate import verify_jwt, create_response, check_content_type


client = datastore.Client()                                # Create a client to access Datastore
bp = Blueprint('bikes', __name__, url_prefix='/bikes')     # Create a blueprint for the bikes entity

# app_url = "http://127.0.0.1:8080"                                     URL for Local self link
app_url = "https://portfolio-lohrcl.uc.r.appspot.com"                 # URL for GCP self link


"""
Route to handle creating a bike entity and listing all bike entities belonging to the authorized user 
in the '/bikes' collection.
"""
@bp.route('', methods=['POST', 'GET'])
def bikes_get_post():

    # Validate JWT
    payload = verify_jwt(request)

    # Create dictionary object for response message
    message = {}

    # Create a new bike entity
    if request.method == 'POST':

        # Checks if the requested content-type and mime-type are accepted
        content_error = check_content_type(message)
        if content_error:
            if content_error['code'] == 415:
                content_error['code'] = "Unsupported Media Type"
                return create_response(content_error, 415)
            content_error['code'] = "Not Acceptable"
            return create_response(content_error, 406)
        content = request.get_json()

        # Check that the request object includes the required attributes
        if len(content) != 4:
            # Call error handler if request object content is invalid
            message["code"] = "Bad Request"
            message["description"] = "The request object is missing at least one of the required attributes"
            return create_response(message, 400)

        # Create new bike entity and update its attributes
        new_bike = datastore.entity.Entity(key=client.key(constants.BIKES))
        new_bike.update({'manufacturer': content['manufacturer'], 'type': content['type'],
                         'model_year': content['model_year'], 'bike_size': content['bike_size']})

        # Add 'specs' and 'rentee' attributes to the bike entity
        new_bike['specs'] = []
        new_bike['rentee'] = None
        client.put(new_bike)

        # Add id and self link to the response body
        new_bike["id"] = new_bike.key.id
        new_bike["self"] = app_url + "/bikes/" + str(new_bike.key.id)

        return create_response(new_bike, 201)

    # List all bike entities belonging to the authorized user
    elif request.method == 'GET':

        # Get the value representing the owner for the JWT
        owner = payload['sub']
        rentee_id = None
        bike_arr = []


        # Fetch all bike entities from the '/bikes' collection
        query = client.query(kind=constants.BIKES)
        bike_list = list(query.fetch())

        # Iterate through all bikes in the /bikes collection
        for i in bike_list:
            if i['rentee']:
                user_key = client.key(constants.USERS, int(i['rentee']))
                user = client.get(key=user_key)
                user_id = user['renter_id']

                # Save the 'rentee id' if the user id matches the JWT owner
                if str(user_id) == str(owner):
                    rentee_id = int(i['rentee'])
                    break

        # Return empty array if no bikes match the rentee_id
        if not rentee_id:
            output = {"bikes": []}
            output['total_items'] = 0
            return create_response(output, 200)

        # Filter query results to those bikes that match the 'rentee_id'
        query.add_filter("rentee", "=", rentee_id)
        # set limit and offset to limit the records per response
        q_limit = int(request.args.get('limit', '5'))
        q_offset = int(request.args.get('offset', '0'))
        l_iterator = query.fetch(limit=q_limit, offset=q_offset)
        pages = l_iterator.pages
        results = list(next(pages))

        # Create a 'next' link by adding the limit to the current offset
        if l_iterator.next_page_token:
            next_offset = q_offset + q_limit
            next_url = request.base_url + "?limit=" + str(q_limit) + "&offset=" + str(next_offset)
        else:
            next_url = None

        # Add bike entity id and self link to response body
        for e in results:
            e["id"] = e.key.id
            e["self"] = app_url + "/bikes/" + str(e.key.id)

            # Add component entity id and self link to the response body
            for i in e['specs']:
                component_id = i['id']
                i['self'] = app_url + "/components/" + str(component_id)

        # Create a dictionary object to hold the list of bikes
        output = {"bikes": results}

        # Add 'next' link to the response body
        if next_url:
            output["next"] = next_url

        # Add the total number of items in the '/bikes' collection to the response body
        output['total_items'] = len(results)

        return create_response(output, 200)

    # Invalid request method
    else:
        message["code"] = "Method Not Allowed"
        message["description"] = "Invalid Request Method"
        return create_response(message, 405)


"""
Route to handle modifying, deleting, and listing an existing bike entity belonging to the authorized user
 in the '/bikes' collection given a bike_id.
"""
@bp.route('/<bike_id>', methods=['PUT', 'PATCH', 'DELETE', 'GET'])
def bikes_put_patch_delete_get(bike_id):

    # Create dictionary object for response message
    message = {}

    # Get bike entity with 'bike_id' from database
    bike_key = client.key(constants.BIKES, int(bike_id))
    bike = client.get(key=bike_key)

    # Call error handler if bike does not exist
    if not bike:
        message['code'] = "Not Found"
        message['description'] = "No bike with this bike_id exists"
        return create_response(message, 404)

    # Validate JWT
    payload = verify_jwt(request)

    # Get the JWT for the user and the user renting the bike with bike_id
    user_jwt = str(payload['sub'])
    rentee_id = bike['rentee']

    # Check if bike is currently rented out
    if not rentee_id:
        message['code'] = "Unauthorized"
        message['description'] = "You must rent this bike before making any requests"
        return create_response(message, 401)

    # Get the user currently renting the bike with bike_id
    rentee_key = client.key(constants.USERS, int(rentee_id))
    rentee = client.get(key=rentee_key)
    rentee_jwt = str(rentee['renter_id'])

    # Modify a bike entity
    if request.method == 'PUT':

        # Check if the user making the request is authorized to modify the bike
        if user_jwt != rentee_jwt:

            # Call error handler if the bike is not rented by the user for the JWT
            message['code'] = "Forbidden"
            message['description'] = "You cannot modify a bike that you aren't renting"
            return create_response(message, 403)

        # Checks if the requested content-type and mime-type are accepted
        content_error = check_content_type(message)
        if content_error:
            if content_error['code'] == 415:
                content_error['code'] = "Unsupported Media Type"
                return create_response(content_error, 415)
            content_error['code'] = "Not Acceptable"
            return create_response(content_error, 406)
        content = request.get_json()

        # Check that the request object includes the required attributes
        if len(content) != 4:

            # Call error handler if request object content is invalid
            message["code"] = "Bad Request"
            message["description"] = "The request object is missing at least one of the required attributes"
            return create_response(message, 400)

        # Update bike attributes
        bike.update({'manufacturer': content['manufacturer'], 'type': content['type'],
                    'model_year': content['model_year'], 'bike_size': content['bike_size']})
        client.put(bike)

        return ('', 204)

    # Modify a bike entity
    elif request.method == 'PATCH':

        # Call error handler if the bike is not rented by the user for the JWT
        if user_jwt != rentee_jwt:
            message['code'] = "Forbidden"
            message['description'] = "You cannot modify a bike that you aren't renting"
            return create_response(message, 403)

        # Checks if the requested content-type and mime-type are accepted
        content_error = check_content_type(message)
        if content_error:
            if content_error['code'] == 415:
                content_error['code'] = "Unsupported Media Type"
                return create_response(content_error, 415)
            content_error['code'] = "Not Acceptable"
            return create_response(content_error, 406)
        content = request.get_json()

        # Checks if the requested attributes to modify are valid
        for key in content:
            bike.update({str(key): content[str(key)]})
        client.put(bike)

        return ('', 204)

    # Delete a bike entity
    elif request.method == 'DELETE':

        # Call error handler if the bike is not rented by the user for the JWT
        if user_jwt != rentee_jwt:
            message['code'] = "Forbidden"
            message['description'] = "You cannot remove a bike that you aren't renting"
            return create_response(message, 403)

        # Fetch all components from the '/components' collection and update its 'carrier' status
        for i in bike['specs']:
            component_id = i['id']
            component_key = client.key(constants.COMPONENTS, int(component_id))
            component = client.get(key=component_key)
            component['carrier'] = None
            client.put(component)

        # Check if the bike is currently being rented by a user and update the 'rental' and 'rentee' status
        if bike['rentee']:
            user_id = bike['rentee']
            user_key = client.key(constants.USERS, int(user_id))
            rentee = client.get(key=user_key)

            for item in rentee['rental']:
                if int(item['id']) == int(bike_id):
                    rentee['rental'].remove(item)
                    client.put(rentee)
                    break
        client.delete(bike_key)

        return ('', 204)

    # Get a bike entity
    elif request.method == 'GET':

        # Call error handler if the bike is not rented by the user for the JWT
        if user_jwt != rentee_jwt:
            message['code'] = "Forbidden"
            message['description'] = "You cannot view a bike that you aren't renting"
            return create_response(message, 403)

        # Add self link for components to response body
        for i in bike['specs']:
            components_id = i['id']
            i['self'] = app_url + "/components/" + str(components_id)

        # Add id and self link to the response body
        bike["id"] = bike.key.id
        bike["self"] = app_url + "/bikes/" + str(bike.key.id)
        return create_response(bike, 200)

    # Invalid request method
    else:
        message["code"] = "Method Not Allowed"
        message["description"] = "Invalid Request Method"
        return create_response(message, 405)


"""
Route to handle adding a component or removing a component from a bike.
"""
@bp.route('/<bike_id>/components/<component_id>', methods=['PUT', 'DELETE'])
def add_delete_bike_components(bike_id, component_id):

    # Create dictionary object for response message
    message = {}

    # Validate JWT
    payload = verify_jwt(request)

    # Get bike entity with 'bike_id' from database
    bike_key = client.key(constants.BIKES, int(bike_id))
    bike = client.get(key=bike_key)

    # Get components entity with 'components_id' from database
    component_key = client.key(constants.COMPONENTS, int(component_id))
    component = client.get(key=component_key)

    # Call error handler if bike or component does not exist
    if not component or not bike:
        message['code'] = "Not Found"
        message['description'] = "The specified bike and/or component does not exist"
        return create_response(message, 404)

    # Add a component to a bike
    if request.method == 'PUT':

        # Call error handler if the component is already assigned to another bike
        if component["carrier"]:
            message['code'] = "Forbidden"
            message['description'] = "The components is already installed on another bike"
            return create_response(message, 403)

        # Create components data for bike entity
        component_data = {'id': component.id, 'description': component['description']}

        # Create bike data for components entity
        bike_data = {'id': bike.id, 'manufacturer': bike['manufacturer']}

        # Add components to bike already carrying components
        if 'specs' in bike.keys():
            bike['specs'].append(component_data)

        # Add components to empty bike
        else:
            bike['specs'] = component_data
        client.put(bike)

        # Update 'carrier' attribute value for component with components_id
        component['carrier'] = bike_data
        client.put(component)

        return ('', 204)

    # Remove a components from a bike
    elif request.method == 'DELETE':

        # Check that bike is carrying a component
        if 'specs' in bike.keys():

            # Iterate through all components on bike and remove components with matching component_id
            for i in bike['specs']:
                if i['id'] == component.id:
                    bike['specs'].remove(i)
                    client.put(bike)

                    # Update 'carrier' attribute value for components with component_id
                    component['carrier'] = None
                    client.put(component)

                    return ('', 204)

        # Call error handler if bike with bike_id is not carrying components with components_id
        message['code'] = "Not Found"
        message['description'] = "No bike with this bike_id is carrying the component with this components_id"
        return create_response(message, 404)

    # Invalid request method
    else:
        message["code"] = "Method Not Allowed"
        message["description"] = "Invalid Request Method"
        return create_response(message, 405)


"""
Route to handle listing all components being carried by the bike rented by the authorized user with bike_id.
"""
@bp.route('/<bike_id>/components', methods=['GET'])
def get_components(bike_id):

    # Create dictionary object for response message
    message = {}

    # Validate JWT
    payload = verify_jwt(request)

    # Get bike entity with 'bike_id' from database
    bike_key = client.key(constants.BIKES, int(bike_id))
    bike = client.get(key=bike_key)

    # Call error handler if bike does not exist
    if not bike:
        message['code'] = "Not Found"
        message['description'] = "The specified bike does not exist"
        return create_response(message, 404)

    # List all components currently assigned to a bike
    if request.method == 'GET':

        # Create an array to hold components elements
        component_arr = []

        # Iterate through each component on the bike
        for i in bike['specs']:

            # Get the id of the components being carried by the bike
            component_id = i['id']

            # Get components entity with 'components_id' from database
            components_key = client.key(constants.COMPONENTS, int(component_id))
            component = client.get(key=components_key)

            # Add the component id and self link to the response body
            component['id'] = component_id
            component['self'] = app_url + "/components/" + str(component_id)

            # Add the bike id and self link to the response body
            carrier = component['carrier']
            carrier['id'] = int(bike_id)
            carrier['self'] = app_url + "/bikes/" + str(bike_id)

            # Add the component entity to the components array
            component_arr.append(component)

        return create_response(component_arr, 200)

    # Invalid request method
    else:
        message["code"] = "Method Not Allowed"
        message["description"] = "Invalid Request Method"
        return create_response(message, 405)
