# Author    : Clinton Lohr
# Date      : 05/30/2023
# Course    : CS 493 - Cloud Application Development
# Assignment: Portfolio - Final Project


from google.cloud import datastore
from flask import request, Blueprint
from validate import verify_jwt, create_response
import constants

client = datastore.Client()                                # Create a client to access Datastore
bp = Blueprint('users', __name__, url_prefix='/users')     # Create a blueprint for the bikes entity

# app_url = "http://127.0.0.1:8080"                                     URL for Local self link
app_url = "https://portfolio-lohrcl.uc.r.appspot.com"                 # URL for GCP self link


"""
Route to handle listing all user entities in the '/users' collection.
"""
@bp.route('', methods=['GET'])
def users_get_all():

    # Create dictionary object for response message
    message = {}

    # List all users
    if request.method == 'GET':

        # Fetch all user entities from the '/users' collection
        query = client.query(kind=constants.USERS)
        results = list(query.fetch())

        # Iterate through all users
        for i in results:

            # Iterate through all bike rentals by the user
            for j in i["rental"]:

                # Add bike self link to response body
                j['self'] = app_url + "/bikes/" + str(j['id'])

            # Add user id and self link to the response body
            i['id'] = i.key.id
            i['self'] = app_url + "/users/" + str(i.key.id)

        # Create a dictionary object to hold the list of users
        output = {"users": results}

        # Add the total number of items in the '/users' collection to the response body
        output['total_items'] = len(results)

        return create_response(output, 200)

    # Invalid request method
    else:
        message["code"] = "Method Not Allowed"
        message["description"] = "Invalid Request Method"
        return create_response(message, 405)


"""
Route to handle getting a single user from the '/users' collection with user_id.
"""
@bp.route('/<user_id>', methods=['GET'])
def user_get(user_id):

    # Create dictionary object for response message
    message = {}

    # Get user entity with 'user_id' from database
    user_key = client.key(constants.USERS, int(user_id))
    user = client.get(key=user_key)

    # Call error handler if user does not exist
    if not user:
        message['code'] = "Not Found"
        message['description'] = "No user with this user_id exists"
        return create_response(message, 404)

    # Iterate through all bikes rented by the user
    for i in user["rental"]:
        # Add bike self link to response body
        i['self'] = app_url + "/bikes/" + str(i['id'])

    # Add user id and self link to the response body
    user['id'] = user_id
    user['self'] = app_url + "/users/" + str(user_id)

    return create_response(user, 200)


"""
Route to handle renting the bike with bike_id to the user with user_id.
"""
@bp.route('/<user_id>/bikes/<bike_id>', methods=['PUT', 'DELETE'])
def users_put_delete(user_id, bike_id):

    # Validate JWT
    payload = verify_jwt(request)

    # Create dictionary object for response message
    message = {}

    # Get bike entity with 'bike_id' from database
    bike_key = client.key(constants.BIKES, int(bike_id))
    bike = client.get(key=bike_key)

    # Get users entity with 'users_id' from database
    user_key = client.key(constants.USERS, int(user_id))
    user = client.get(key=user_key)

    # Call error handler if bike or user does not exist
    if not user or not bike:
        message["code"] = "Not Found"
        message["description"] = "The specified bike and/or user does not exist"
        return create_response(message, 404)

    # Get the JWT for the user and the user renting the bike with bike_id
    user_jwt = str(payload['sub'])
    rentee_jwt = str(user['renter_id'])

    # Add a bike to a user
    if request.method == 'PUT':

        """
        # Check if the user making the request is authorized to modify the bike
        if user_jwt != rentee_jwt:
            message['code'] = "Unauthorized"
            message['description'] = "You cannot modify a bike that you aren't renting"
            return create_response(message, 401)
        """
        # Call error handler if the user is already assigned to another bike
        if bike["rentee"]:
            message["code"] = "Forbidden"
            message["description"] = "This bike is currently rented out"
            return create_response(message, 403)

        # Create bike data for users entity
        bike_data = {'id': int(bike_id)}

        # Add users to bike already carrying users
        user['rental'].append(bike_data)
        client.put(user)

        # Update 'carrier' attribute value for user with users_id
        bike['rentee'] = int(user_id)
        client.put(bike)
        return ('', 204)

    # Remove a bike from a user
    elif request.method == 'DELETE':

        # Check if the user making the request is authorized to modify the bike
        if user_jwt != rentee_jwt:
            message["code"] = "Unauthorized"
            message["description"] = "You cannot return a bike that is rented to another user"
            return create_response(message, 401)

        # Check that bike is carrying a user
        if user['rental']:

            # Iterate through all users on bike and remove users with matching user_id
            for i in user['rental']:
                if int(i['id']) == int(bike_id):
                    user['rental'].remove(i)
                    client.put(user)

                    # Update 'carrier' attribute value for users with user_id
                    bike['rentee'] = None
                    client.put(bike)

                    return ('', 204)

        # Call error handler if bike with bike_id is not carrying users with users_id
        message["code"] = "Not Found"
        message["description"] = "No bike with this bike_id is rented to a user with this user_id"
        return create_response(message, 404)

    else:
        message["code"] = "Method Not Allowed"
        message["description"] = "Invalid Request Method"
        return create_response(message, 405)
