from flask import request
from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity
from flask_jwt_extended.exceptions import NoAuthorizationError
from models.shared import db
from models.log import ActivityLog


class Middlewares():
    def __init__(self, app) -> None:
        @app.after_request
        def log_response_status(response):
            try:
                # Skip logging for login and refresh endpoints
                if any(endpoint in request.path for endpoint in ["login", "refresh", "log", "health"]):
                    return response

                # Attempt to get user identity
                user_id = None
                try:
                    verify_jwt_in_request()  # Checks if JWT exists in the request
                    user_id = get_jwt_identity()
                except NoAuthorizationError:  # This exception is raised if JWT is missing
                    pass

                log_data = {
                    'url': request.path,
                    'user_id': user_id
                }

                # If endpoint contains 'user', skip logging payload
                if "user" not in request.path:
                    # Log URL, user ID, and payload (if available)
                    payload = request.get_json(silent=True)

                    if payload:
                        log_data['payload'] = payload
                else:
                    return response

                # Store log_data in your database
                activity_log = ActivityLog(
                    url=log_data['url'], user_id=log_data['user_id'])

                if log_data.get('payload'):
                    activity_log.payload = log_data['payload']

                db.session.add(activity_log)
                db.session.commit()

                return response
            except:
                return response
