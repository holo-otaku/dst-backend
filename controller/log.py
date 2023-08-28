from flask import current_app, jsonify, make_response, request
from models.log import ActivityLog
from models.shared import db
from sqlalchemy.exc import SQLAlchemyError


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
        offset = int(request.args.get('page', 1))-1

        # Query the ActivityLog table with limit and offset
        logs = ActivityLog.query.offset(offset*limit).limit(limit).all()

        response_data = []
        for log in logs:
            response_data.append({
                'id': log.id,
                'url': log.url,
                'userId': log.user_id,
                'payload': log.payload,
                'createdAt': log.created_at.strftime('%Y-%m-%d %H:%M:%S')
            })

        return make_response(jsonify({"code": 200, "msg": "Roles found", "data": response_data}), 200)

    except SQLAlchemyError as e:
        current_app.logger.error(e)
        return make_response(jsonify({"code": 500, "msg": str(e)}), 500)

    except Exception as e:
        current_app.logger.error(e)
        return make_response(jsonify({"code": 500, "msg": str(e)}), 500)

    finally:
        db.session.close()
