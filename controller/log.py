from flask import current_app, jsonify, make_response, request
from models.log import ActivityLog
from models.user import User
from models.shared import db
from sqlalchemy.exc import SQLAlchemyError
import json


def user_logs(user_id):
    try:
        # Get the limit and offset values from the request
        limit = int(request.args.get('limit', 10))
        offset = int(request.args.get('page', 1))-1

        logs = ActivityLog.query.filter_by(
            user_id=user_id).offset(offset*limit).limit(limit).all()

        response_data = []
        for log in logs:
            response_data.append({
                'id': log.id,
                'url': log.url,
                'userId': log.user_id,
                'payload': log.payload,
                'createdAt': log.created_at.strftime('%Y-%m-%d %H:%M:%S')
            })

        return make_response(jsonify({"code": 200, "msg": "Success", "data": response_data}), 200)

    except SQLAlchemyError as e:
        current_app.logger.error(e)
        return make_response(jsonify({"code": 500, "msg": str(e)}), 500)

    except Exception as e:
        current_app.logger.error(e)
        return make_response(jsonify({"code": 500, "msg": str(e)}), 500)

    finally:
        db.session.close()


def read_multi():
    try:
        # Get the limit and offset values from the request
        limit = int(request.args.get('limit', 10))
        offset = int(request.args.get('page', 1)) - 1

        # Query the total count of ActivityLog
        total_count = ActivityLog.query.count()

        # Query the ActivityLog table with limit, offset, order_by and join with User
        logs = db.session.query(ActivityLog, User.username).join(
            User, ActivityLog.user_id == User.id
        ).order_by(ActivityLog.created_at.desc()).offset(offset*limit).limit(limit).all()

        response_data = []
        for log, username in logs:
            formatted_payload = None
            if log.payload:
                payload_str = json.dumps(log.payload)
                formatted_payload = payload_str[:47] + \
                    '...' if len(payload_str) > 50 else payload_str

            response_data.append({
                'id': log.id,
                'url': log.url,
                'userId': log.user_id,
                'userName': username,
                'payload': formatted_payload,
                'createdAt': log.created_at.strftime('%Y-%m-%d %H:%M:%S')
            })

        return make_response(jsonify({"code": 200, "msg": "Logs found", "data": response_data, "totalCount": total_count}), 200)

    except SQLAlchemyError as e:
        current_app.logger.error(e)
        return make_response(jsonify({"code": 500, "msg": str(e)}), 500)

    except Exception as e:
        current_app.logger.error(e)
        return make_response(jsonify({"code": 500, "msg": str(e)}), 500)

    finally:
        db.session.close()
