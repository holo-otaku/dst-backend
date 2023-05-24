from flask import current_app, jsonify, make_response, request
from models.series import *
from models.user import *
from models.shared import db
from sqlalchemy.exc import SQLAlchemyError


def create(data):
    try:
        name = data.get('name')
        created_by = data.get('createdBy')

        if not name or not created_by:
            return make_response(jsonify({"code": 400, "msg": "Incomplete data"}), 400)

        series = Series(name=name, created_by=created_by)

        # Check if 'fields' data is provided in the request
        fields_data = data.get('fields', [])
        if fields_data:
            for field_data in fields_data:
                field_name = field_data.get('name')
                field_data_type = field_data.get('dataType')
                field_is_required = field_data.get('isRequired', False)

                # Create a new Field object and associate it with the series
                field = Field(
                    name=field_name, data_type=field_data_type, is_required=field_is_required)
                series.fields.append(field)

        db.session.add(series)
        db.session.commit()

        result = {'id': series.id, 'name': series.name,
                  'createdBy': series.created_by}
        return make_response(jsonify({"code": 201, "msg": "Success", "data": result}), 201)

    except SQLAlchemyError as e:
        db.session.rollback()
        return make_response(jsonify({"code": 500, "msg": str(e)}), 500)

    finally:
        db.session.close()


def read(series_id):
    try:
        series = Series.query.get(series_id)
        if series:
            data = {'id': series.id,
                    'name': series.name,
                    'createdBy': series.creator.username,
                    'createdAt': series.created_at.strftime("%Y-%m-%d %H:%M:%S")}

            field = request.args.get('field', False)
            if field:
                field_data = [{'name': f.name, 'dataType': f.data_type,
                               'isRequired': f.is_required} for f in series.fields]
                data['fields'] = field_data

            return make_response(jsonify({"code": 200, "msg": "Success", "data": data}), 200)
        else:
            return make_response(jsonify({"code": 404, "msg": "Series not found"}), 404)

    except SQLAlchemyError as e:
        print("Failed to read series data: ", e)
        return make_response(jsonify({"code": 500, "msg": str(e)}), 500)

    finally:
        db.session.close()


def read_multi():
    try:
        series = Series.query.all()
        result = []
        field = request.args.get('field', False)
        for s in series:
            data = {
                'id': s.id,
                'name': s.name,
                'createdBy': s.creator.username,
                'createdAt': s.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            }

            if field:
                field_data = [{'name': f.name, 'dataType': f.data_type,
                               'isRequired': f.is_required} for f in s.fields]
                data['fields'] = field_data

            result.append(data)

        return make_response(jsonify({"code": 200, "msg": "Success", "data": result}), 200)

    except SQLAlchemyError as e:
        print("Failed to read series data: ", e)
        return make_response(jsonify({"code": 500, "msg": str(e)}), 500)

    finally:
        db.session.close()


def update(series_id, data):
    try:
        series = Series.query.get(series_id)

        if not series:
            return make_response(jsonify({"code": 404, "msg": "Series not found"}), 404)

        name = data.get('name')
        created_by = data.get('createdBy')

        if not name or not created_by:
            return make_response(jsonify({"code": 400, "msg": "Incomplete data"}), 400)

        user = User.query.get(created_by)
        if not user:
            return make_response(jsonify({"code": 400, "msg": "Invalid user"}), 400)

        series.name = name
        series.creator = user

        # Delete existing fields associated with the series
        Field.query.filter_by(series_id=series.id).delete()

        # Check if 'fields' data is provided in the request
        fields_data = data.get('fields', [])
        if fields_data:
            # Clear existing fields associated with the series
            series.fields.clear()

            for field_data in fields_data:
                field_name = field_data.get('name')
                field_data_type = field_data.get('dataType')
                field_is_required = field_data.get('isRequired', False)

                # Create a new Field object and associate it with the series
                field = Field(
                    name=field_name, data_type=field_data_type, is_required=field_is_required)
                series.fields.append(field)

        db.session.commit()

        result = {'id': series.id, 'name': series.name,
                  'created_by': series.creator.username}
        return make_response(jsonify({"code": 200, "msg": "Success", "data": result}), 200)

    except SQLAlchemyError as e:
        db.session.rollback()
        return make_response(jsonify({"code": 500, "msg": str(e)}), 500)

    finally:
        db.session.close()


def delete(series_id):
    try:
        series = Series.query.get(series_id)
        if series:
            # Delete associated fields
            Field.query.filter_by(series_id=series.id).delete()

            db.session.delete(series)
            db.session.commit()
            return make_response(jsonify({"code": 200, "msg": "Series deleted"}), 200)
        else:
            return make_response(jsonify({"code": 404, "msg": "Series not found"}), 404)

    except SQLAlchemyError as e:
        db.session.rollback()
        return make_response(jsonify({"code": 500, "msg": str(e)}), 500)

    finally:
        db.session.close()
