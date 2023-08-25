from flask import request
from flask_jwt_extended import jwt_required, get_jwt_identity
from models.shared import db
from models.log import ActivityLog


class middlewares():
    def __init__(self, app) -> None:
        @app.after_request
        def log_response_status(response):
            if any(endpoint in request.path for endpoint in ["login", "refresh"]):
                return response

            user_id = get_jwt_identity() if jwt_required(optional=True) else None
            log_data = {
                'url': request.path,
                'user_id': user_id
            }

            if any(endpoint in request.path for endpoint in ["user"]):
                pass
            else:
                # Log URL, user ID, and payload (if available)
                payload = request.get_json(silent=True)

                if payload:
                    log_data['payload'] = payload

            # Store log_data in your database or wherever you want
            activity_log = ActivityLog(
                url=log_data['url'], user_id=log_data['user_id'], payload=log_data.get('payload'))
            db.session.add(activity_log)
            db.session.commit()

            return response
