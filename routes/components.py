# Author    : Clinton Lohr
# Date      : 05/30/2023
# Course    : CS 493 - Cloud Application Development
# Assignment: Portfolio - Final Project


from google.cloud import datastore
from flask import request, Blueprint
from validate import create_response, check_content_type
import constants

client = datastore.Client()                                           # Create a client to access Datastore
bp = Blueprint('components', __name__, url_prefix='/components')      # Create a blueprint for the bikes entity

# app_url = "http://127.0.0.1:8080"                                     URL for Local self link
app_url = "https://portfolio-lohrcl.uc.r.appspot.com"                 # URL for GCP self link


"""
Route to handle creating a component entity and listing all component entities in the '/components' collection.
"""
@bp.route('', methods=['POST', 'GET'])
def components_get_post():

    # Create dictionary object for response message
    message = {}

    # Create a new component entity
    if request.method == 'POST':
        content = request.get_json()

        # Check that the request object includes the required attributes
        if len(content) != 3:

            # Call error handler if request object content is invalid
            message["code"] = "Bad Request"
            message["description"] = "The request object is missing at least one of the required attributes"
            return create_response(message, 400)

        content_error = check_content_type(message)
        if content_error:
            if content_error['code'] == 415:
                content_error['code'] = "Unsupported Media Type"
                return create_response(content_error, 415)
            content_error['code'] = "Not Acceptable"
            return create_response(content_error, 406)

        content = request.get_json()
        # Create new component entity and update its attributes
        new_component = datastore.entity.Entity(key=client.key(constants.COMPONENTS))
        new_component.update({"manufacturer": content["manufacturer"], "description": content["description"],
                              "condition": content["condition"]})

        # Add 'carrier' attribute to the entity
        new_component["carrier"] = None
        client.put(new_component)

        # Add id and self link to the response body
        new_component["id"] = new_component.key.id
        new_component["self"] = app_url + "/components/" + str(new_component.key.id)

        return create_response(new_component, 201)

    # List all component entities
    elif request.method == 'GET':

        # Fetch all component entities from the '/components' collection
        query = client.query(kind=constants.COMPONENTS)

        # set limit and offset to limit the records per response
        q_limit = int(request.args.get('limit', '5'))
        q_offset = int(request.args.get('offset', '0'))
        g_iterator = query.fetch(limit=q_limit, offset=q_offset)
        pages = g_iterator.pages
        results = list(next(pages))

        # Create a 'next' link by adding the limit to the current offset
        if g_iterator.next_page_token:
            next_offset = q_offset + q_limit
            next_url = request.base_url + "?limit=" + str(q_limit) + "&offset=" + str(next_offset)
        else:
            next_url = None

        # Add component id and self link to response body
        for e in results:
            e["id"] = e.key.id
            e["self"] = app_url + "/components/" + str(e.key.id)

            # Add bike id and self link to the response body
            if e['carrier']:
                carrier = e['carrier']
                bike_id = carrier['id']
                carrier['self'] = app_url + "/bikes/" + str(bike_id)

        # Create a dictionary object to hold the list of components
        output = {"components": results}

        # Add the total number of items in the '/components' collection to the response body
        output['total_items'] = len(results)

        # Add 'next' link to the response body
        if next_url:
            output["next"] = next_url\

        return create_response(output, 200)

    # Invalid request method
    else:
        message["code"] = "Method Not Allowed"
        message["description"] = "Invalid Request Method"
        return create_response(message, 405)


"""
Route to handle modifying, deleting, and listing an existing component entity in the '/components' collection
given a component_id.
"""
@bp.route('/<component_id>', methods=['PUT', 'PATCH', 'DELETE', 'GET'])
def components_put_delete(component_id):

    # Create dictionary object for response message
    message = {}

    # Get component entity with 'component_id' from database
    component_key = client.key(constants.COMPONENTS, int(component_id))
    component = client.get(key=component_key)

    # Call error handler if component does not exist
    if not component:
        message["code"] = "Not Found"
        message["description"] = "No component with this component_id exists"
        return create_response(message, 404)

    # Modify a component entity
    if request.method == 'PUT':
        content = request.get_json()

        # Check if input includes required attributes
        if len(content) != 3:
            # Call error handler if request object content is invalid
            message["code"] = "Bad Request"
            message["description"] = "The request object is missing at least one of the required attributes"
            return create_response(message, 400)

        content_error = check_content_type(message)
        if content_error:
            if content_error['code'] == 415:
                content_error['code'] = "Unsupported Media Type"
                return create_response(content_error, 415)
            content_error['code'] = "Not Acceptable"
            return create_response(content_error, 406)

        # Update component attributes
        component.update({"manufacturer": content["manufacturer"], "description": content["description"],
                         "condition": content["condition"]})
        client.put(component)

        # Check if the component is currently assigned to a bike
        if component['carrier']:
            carrier = component['carrier']
            bike_key = client.key(constants.BIKES, int(carrier['id']))
            bike = client.get(key=bike_key)

            # Iterate through all components on a bike and update component with component_id
            for i in bike['specs']:
                if int(i['id']) == int(component_id):
                    bike['specs'].remove(i)
                    component_data = {'id': int(component_id), 'description': content['description']}
                    bike['specs'].append(component_data)
                    client.put(bike)

        return ('', 204)

    elif request.method == 'PATCH':
        content = request.get_json()

        # Checks if the requested attributes to modify are valid
        for key in content:
            component.update({str(key): content[str(key)]})
        client.put(component)

        # Check if the component is currently assigned to a bike
        if component['carrier']:
            carrier = component['carrier']
            bike_key = client.key(constants.BIKES, int(carrier['id']))
            bike = client.get(key=bike_key)

            # Iterate through all components on a bike and update component with component_id
            for i in bike['specs']:
                if int(i['id']) == int(component_id):
                    bike['specs'].remove(i)

                    # Update description
                    if 'description' in content:
                        component_data = {'id': int(component_id), 'description': content['description']}

                    # Don't update description
                    else:
                        component_data = {'id': int(component_id), 'description': component['description']}

                    bike['specs'].append(component_data)
                    client.put(bike)

        return ('', 204)

    # Delete a component entity
    elif request.method == 'DELETE':

        # Check if the component is currently on a bike
        if component['carrier']:

            # Get the id of the bike carrying the component
            bike = component["carrier"]
            bike_id = bike['id']

            # Get bike entity with 'bike_id' from database
            bike_key = client.key(constants.BIKES, int(bike_id))
            bike = client.get(key=bike_key)

            # Iterate through the bike's components a remove the component matching component_id
            for i in bike['specs']:
                if int(i['id']) == int(component_id):
                    bike['specs'].remove(i)
                    client.put(bike)
                    break

        client.delete(component)
        return ('', 204)

    # Get a component entity
    elif request.method == 'GET':

        # Add self link to carrier if component is on a bike
        if component['carrier']:
            component['carrier']['self'] = app_url + "/bikes/" + str(component['carrier']['id'])

        # Add id and self link to the response body
        component["id"] = component.key.id
        component["self"] = app_url + "/components/" + str(component.key.id)
        return create_response(component, 200)

    # Invalid request method
    else:
        message["code"] = "Method Not Allowed"
        message["description"] = "Invalid Request Method"
        return create_response(message, 405)
