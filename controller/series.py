from flask import current_app, jsonify, make_response, request
from models.series import Series, Field, Item, ItemAttribute
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
            # Check is_erp only one
            erp_count = 0
            for field_data in fields_data:
                field_name = field_data.get('name')
                field_data_type = field_data.get('dataType').lower()

                if field_data_type not in data_type_map:
                    return make_response(jsonify({"code": 400, "msg": f"{field_name} DataType Error"}), 400)

                field_is_filtered = field_data.get('isFiltered', False)
                field_is_required = field_data.get('isRequired', False)
                field_is_erp = field_data.get('isErp', False)

                if (field_is_erp):
                    erp_count += 1
                    if (erp_count > 1):
                        return make_response(jsonify({"code": 400, "msg": "Erp can only be set once !"}), 400)

                # Create a new Field object and associate it with the series
                field = Field(
                    name=field_name,
                    data_type=field_data_type,
                    is_filtered=field_is_filtered,
                    is_required=field_is_required,
                    is_erp=field_is_erp
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
                           'isRequired': f.is_required,
                           'isErp': f.is_erp} for f in series.fields]
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
                               'isRequired': f.is_required,
                               'isErp': f.is_erp} for f in s.fields]
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

        # Update the series name
        series.name = data.get('name')

        # Handle field updates
        fields_data = data.get('fields', [])
        for field_data in fields_data:
            field_id = field_data.get('id')
            field = db.session.get(Field, field_id)

            if not field:
                return make_response(jsonify({"code": 404, "msg": f"Field with ID {field_id} not found"}), 404)

            # Check if there are any item attributes using this field
            has_related_item_attributes = db.session.query(
                ItemAttribute).filter_by(field_id=field.id).first()
            if has_related_item_attributes and field.data_type != field_data.get('dataType'):
                return make_response(jsonify({"code": 400, "msg": f"Cannot update data type of field with ID {field_id} since it's being used in ItemAttribute"}), 400)

            field.name = field_data.get('name')
            field.data_type = field_data.get('dataType')
            field.is_filtered = field_data.get('isFiltered')
            field.is_required = field_data.get('isRequired')
            field.is_erp = field_data.get('isErp')

        # Handle field creation
        create_data = data.get('create')
        if create_data:
            new_field = Field(name=create_data.get('name'), data_type=create_data.get('dataType'),
                              is_filtered=create_data.get('isFiltered'), is_required=create_data.get('isRequired'),
                              is_erp=create_data.get('isErp'), series_id=series_id)
            db.session.add(new_field)
            db.session.flush()  # Ensure new_field has an ID

            # Create ItemAttribute for all items in this series with value as null
            items_in_series = db.session.query(Item).filter(
                Item.series_id == series_id).all()
            for item in items_in_series:
                new_item_attribute = ItemAttribute(
                    item_id=item.id, field_id=new_field.id, value=None)
                db.session.add(new_item_attribute)

        # Handle field deletion
        delete_ids = data.get('delete', [])
        for delete_id in delete_ids:
            field_to_delete = db.session.get(Field, delete_id)
            if field_to_delete:
                db.session.delete(field_to_delete)

        db.session.commit()

        return make_response(jsonify({"code": 200, "msg": "Success"}), 200)

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
