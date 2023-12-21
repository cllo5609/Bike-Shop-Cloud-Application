# Author    : Clinton Lohr
# Date      : 05/30/2023
# Course    : CS 493 - Cloud Application Development
# Assignment: Portfolio - Final Project


from flask import make_response, request
from six.moves.urllib.request import urlopen
from jose import jwt
import json
import constants


# This code is adapted from https://auth0.com/docs/quickstart/backend/python/01-authorization?_ga =
# 2.46956069.349333901.1589042886 - 466012638.1589042885  # create-the-jwt - validation - decorator
class AuthError(Exception):

    def __init__(self, error, status_code):
        self.error = error
        self.status_code = status_code


# Verify the JWT in the request's Authorization header
def verify_jwt(request):
    if 'Authorization' in request.headers:
        auth_header = request.headers['Authorization'].split()
        token = auth_header[1]
    else:
        raise AuthError({"code": "no auth header",
                        "description":
                        "Authorization header is missing"}, 401)

    jsonurl = urlopen("https://" + constants.DOMAIN + "/.well-known/jwks.json")
    jwks = json.loads(jsonurl.read())
    try:
        unverified_header = jwt.get_unverified_header(token)
    except jwt.JWTError:
            raise AuthError({"code": "invalid_header", "description": "Invalid header. "
                         "Use an RS256 signed JWT Access Token"}, 401)

    if unverified_header["alg"] == "HS256":
        raise AuthError({"code": "invalid_header",
                        "description":
                        "Invalid header. "
                        "Use an RS256 signed JWT Access Token"}, 401)

    rsa_key = {}
    for key in jwks["keys"]:
        if key["kid"] == unverified_header["kid"]:
            rsa_key = {
                "kty": key["kty"],
                "kid": key["kid"],
                "use": key["use"],
                "n": key["n"],
                "e": key["e"]
            }
    if rsa_key:
        try:
            payload = jwt.decode(
                token,
                rsa_key,
                algorithms=constants.ALGORITHMS,
                audience=constants.CLIENT_ID,
                issuer="https://" + constants.DOMAIN + "/"
            )
        except jwt.ExpiredSignatureError:
            raise AuthError({"code": "token_expired",
                             "description": "token is expired"}, 401)
        except jwt.JWTClaimsError:
            raise AuthError({"code": "invalid_claims",
                             "description":
                                 "incorrect claims,"
                                 " please check the audience and issuer"}, 401)
        except Exception:
            raise AuthError({"code": "invalid_header",
                             "description":
                                 "Unable to parse authentication"
                                 " token."}, 401)
        return payload
    else:
        raise AuthError({"code": "no_rsa_key",
                         "description":
                             "No RSA key in JWKS"}, 401)


"""
Helper function to create an error message if an error has occurred.
"""
def create_response(message, status_code):
    res = make_response(json.dumps(message))
    res.mimetype = 'application/json'
    res.status_code = status_code
    return res


"""
Helper function to check if the correct content-type and accepted mime-type was requested.
"""
def check_content_type(message):
    # Checks if the request by the client is made with a valid content-type
    if 'application/json' not in request.content_type:
        message["code"] = 415
        message["description"] = "Content type for this request must be application/json"

    # Checks if the mime-type requested by the client is valid
    elif 'application/json' not in request.accept_mimetypes:
        message["code"] = 406
        message["description"] = "The chosen media type is not supported for this request"
    return message

