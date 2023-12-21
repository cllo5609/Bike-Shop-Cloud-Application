# Author    : Clinton Lohr
# Date      : 05/30/2023
# Course    : CS 493 - Cloud Application Development
# Assignment: Portfolio - Final Project


from google.cloud import datastore
from flask import Flask, redirect, render_template, session, url_for, request, jsonify
import bikes
import components
import users
import constants
from validate import verify_jwt, AuthError
import json
from authlib.integrations.flask_client import OAuth
from six.moves.urllib.parse import urlencode, quote_plus

app = Flask(__name__)                   # Create an application using Flask
app.register_blueprint(users.bp)        # Register the users blueprint
app.register_blueprint(bikes.bp)        # Register the bikes blueprint
app.register_blueprint(components.bp)   # Register the components blueprint
app.secret_key = constants.SECRET_KEY   # Set secret key for session dictionary access

client = datastore.Client()             # Create a client to access Datastore

# Create OAuth for the Flask application
oauth = OAuth(app)

# Register application for OAuth client
auth0 = oauth.register(
    'auth0',
    client_id=constants.CLIENT_ID,
    client_secret=constants.CLIENT_SECRET,
    api_base_url="https://" + constants.DOMAIN,
    access_token_url="https://" + constants.DOMAIN + "/oauth/token",
    authorize_url="https://" + constants.DOMAIN + "/authorize",
    client_kwargs={
        'scope': 'openid profile email',
    },
    server_metadata_url="https://" + constants.DOMAIN + "/.well-known/openid-configuration"
)


"""
Route that responds with a welcome page and a link to generate a JWT using Auth0 and 
displays user information after the user creates or logs into an account.

***
    The code for the 'def home()' function is adapted from https://auth0.com/docs/quickstart/webapp/python
    Configure Auth0 for a Python web application
***
"""
@app.route('/')
def home():
    return render_template("home.html", session=session.get('user'),
                           pretty=json.dumps(session.get('user'), indent=4))


"""
Route that redirects users to the Auth0 login page to generate a JWT.

***
    The code for the 'def login()' function is adapted from https://auth0.com/docs/quickstart/webapp/python
    Configure Auth0 for a Python web application
***
"""
@app.route("/login")
def login():
    return oauth.auth0.authorize_redirect(
        redirect_uri=url_for("callback", _external=True)
    )


"""
Route that redirects users to the 'User Information' page and displays the user's access token,
id token and 'sub' values.
This route also calls the helper function 'create_user' to create a new user entity and store user
information in Datastore. 

***
    The code for the 'def login()' function is adapted from https://auth0.com/docs/quickstart/webapp/python
    Configure Auth0 for a Python web application
***
"""
@app.route("/callback", methods=["GET", "POST"])
def callback():
    token = oauth.auth0.authorize_access_token()
    create_user(token)
    session["user"] = token
    return redirect("/")


"""
Route that allows users to logout of their Auth0 account and redirects users back to the 'Welcome' page.

***
    The code for the 'def login()' function is adapted from https://auth0.com/docs/quickstart/webapp/python
    Configure Auth0 for a Python web application
***
"""
@app.route("/logout")
def logout():
    session.clear()
    return redirect(
        "https://" + constants.DOMAIN + "/v2/logout?" + urlencode(
            {
                "returnTo": url_for("home", _external=True),
                "client_id": constants.CLIENT_ID,
            },
            quote_via=quote_plus,
        )
    )


"""
Route that decodes the JWT token provided by Auth0
"""
@app.route('/decode', methods=['GET'])
def decode_jwt():
    payload = verify_jwt(request)
    return payload


"""
Error handler route to form the JSON error message response.
"""
@app.errorhandler(AuthError)
def handle_auth_error(ex):
    response = jsonify(ex.error)
    response.status_code = ex.status_code
    return response


"""
Helper function to create a new user entity with the information provided by the JWT. User entities
 are stored in Datastore.
"""
def create_user(user_token):
    user_info = user_token['userinfo']
    query = client.query(kind=constants.USERS)
    results = list(query.fetch())
    for i in results:
        if str(i['renter_id']) == str(user_info['sub']):
            return

    new_user = datastore.entity.Entity(key=client.key(constants.USERS))
    new_user.update({'nickname': user_info['nickname'], 'email': user_info['email'],
                     'verified': user_info['email_verified'], 'renter_id': user_info['sub'], 'rental': []})
    client.put(new_user)


"""
Route to delete all entities in all collections currently stored in Datastore. Collections include 
'users', 'bikes' and 'components'
"""
@app.route('/delete', methods=['DELETE'])
def delete_all():
    comps_query = client.query(kind=constants.COMPONENTS)
    bikes_query = client.query(kind=constants.BIKES)
    users_query = client.query(kind=constants.USERS)
    results = list(comps_query.fetch()) + list(bikes_query.fetch()) + list(users_query.fetch())
    for i in results:
        client.delete(i)
    return ('', 204)


if __name__ == '__main__':
    app.run(host='127.0.0.1', port=8080, debug=True)


