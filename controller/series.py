from flask import current_app, jsonify, make_response, request
from models.series import Series, Field, Item
from models.user import User
from models.shared import db
from models.mapping_table import data_type_map
from sqlalchemy.exc import SQLAlchemyError
from flask_jwt_extended import get_jwt_identity


def create(data):
    try:
        name = data.get('name')
        created_by = get_jwt_identity()

        if not name or not created_by:
            return make_response(jsonify({"code": 400, "msg": "Incomplete data"}), 400)

        series = Series(name=name, created_by=created_by)

        # Check if 'fields' data is provided in the request
        fields_data = data.get('fields', [])
        if fields_data:
            for field_data in fields_data:
                field_name = field_data.get('name')
                field_data_type = field_data.get('dataType').lower()

                if field_data_type not in data_type_map:
                    return make_response(jsonify({"code": 400, "msg": f"{field_name} DataType Error"}), 400)

                field_is_filtered = field_data.get('isFiltered', False)
                field_is_required = field_data.get('isRequired', False)

                # Create a new Field object and associate it with the series
                field = Field(
                    name=field_name,
                    data_type=field_data_type,
                    is_filtered=field_is_filtered,
                    is_required=field_is_required
                )
                series.fields.append(field)

        db.session.add(series)
        db.session.commit()

        result = {'id': series.id, 'name': series.name,
                  'createdBy': series.created_by}
        return make_response(jsonify({"code": 201, "msg": "Success", "data": result}), 201)

    except SQLAlchemyError as e:
        db.session.rollback()
        current_app.logger.error(e)
        return make_response(jsonify({"code": 500, "msg": str(e)}), 500)

    except Exception as e:
        current_app.logger.error(e)
        return make_response(jsonify({"code": 500, "msg": str(e)}), 500)

    finally:
        db.session.close()


def read(series_id):
    try:
        series = Series.query.filter_by(id=series_id, status=1).first()

        if series:
            data = {'id': series.id,
                    'name': series.name,
                    'createdBy': series.creator.username,
                    'createdAt': series.created_at.strftime("%Y-%m-%d %H:%M:%S")}

            field_data = [{'id': f.id,
                           'name': f.name,
                           'dataType': f.data_type,
                           'isFiltered': f.is_filtered,
                           'isRequired': f.is_required} for f in series.fields]
            data['fields'] = field_data

            return make_response(jsonify({"code": 200, "msg": "Success", "data": data}), 200)
        else:
            return make_response(jsonify({"code": 404, "msg": "Series not found"}), 404)

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
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 10))
        keyword = str(request.args.get('keyword', ''))

        if keyword:
            series = Series.query.filter(
                Series.name.ilike(f"%{keyword}%"),
                Series.status == 1
            ).all()
        else:
            series = Series.query.filter_by(
                status=1).paginate(page=page, per_page=limit)

        result = []
        show_field = bool(int(request.args.get('showField', False)))
        for s in series:
            data = {
                'id': s.id,
                'name': s.name,
                'createdBy': s.creator.username,
                'createdAt': s.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            }

            if show_field:
                field_data = [{'id': f.id,
                               'name': f.name,
                               'dataType': f.data_type,
                               'isFiltered': f.is_filtered,
                               'isRequired': f.is_required} for f in s.fields]
                data['fields'] = field_data

            result.append(data)

        return make_response(jsonify({"code": 200, "msg": "Success", "data": result}), 200)

    except SQLAlchemyError as e:
        current_app.logger.error(e)
        return make_response(jsonify({"code": 500, "msg": str(e)}), 500)

    except Exception as e:
        current_app.logger.error(e)
        return make_response(jsonify({"code": 500, "msg": str(e)}), 500)

    finally:
        db.session.close()


def update(series_id, data):
    try:
        series = db.session.get(Series, series_id)

        if not series:
            return make_response(jsonify({"code": 404, "msg": "Series not found"}), 404)

        # Check if any items are associated with the series
        has_related_items = db.session.query(
            Item).filter_by(series_id=series.id).first()
        if has_related_items:
            return make_response(jsonify({"code": 400, "msg": "Cannot update series with associated items"}), 400)

        name = data.get('name')

        created_by = get_jwt_identity()
        user = db.session.get(User, created_by)

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
                field_is_filtered = field_data.get('isFiltered', False)
                field_is_required = field_data.get('isRequired', False)

                # Create a new Field object and associate it with the series
                field = Field(
                    name=field_name, data_type=field_data_type, is_filtered=field_is_filtered, is_required=field_is_required)
                series.fields.append(field)

        db.session.commit()

        result = {'id': series.id, 'name': series.name,
                  'created_by': series.creator.username}
        return make_response(jsonify({"code": 200, "msg": "Success", "data": result}), 200)

    except SQLAlchemyError as e:
        db.session.rollback()
        current_app.logger.error(e)
        return make_response(jsonify({"code": 500, "msg": str(e)}), 500)

    except Exception as e:
        current_app.logger.error(e)
        return make_response(jsonify({"code": 500, "msg": str(e)}), 500)

    finally:
        db.session.close()


def delete(series_id):
    try:
        series = db.session.get(Series, series_id)

        if series:
            # Set series status to 0 (deleted)
            series.status = 0

            db.session.commit()
            return make_response(jsonify({"code": 200, "msg": "Series deleted"}), 200)
        else:
            return make_response(jsonify({"code": 404, "msg": "Series not found"}), 404)

    except SQLAlchemyError as e:
        db.session.rollback()
        current_app.logger.error(e)
        return make_response(jsonify({"code": 500, "msg": str(e)}), 500)

    except Exception as e:
        current_app.logger.error(e)
        return make_response(jsonify({"code": 500, "msg": str(e)}), 500)

    finally:
        db.session.close()
