from flask import current_app, jsonify, make_response, request
from models.series import *
from models.shared import db
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import and_, or_, text


def create(data):
    try:
        series_id = data.get('seriesId')
        name = data.get('name')
        attributes = data.get('attributes')

        if not series_id or not name or not attributes:
            return make_response(jsonify({"code": 400, "msg": "Incomplete data"}), 400)

        series = Series.query.get(series_id)
        if not series:
            return make_response(jsonify({"code": 404, "msg": "Series not found"}), 404)

        item = Item(series_id=series_id, name=name)
        db.session.add(item)

        field_ids = [attribute.get(
            'fieldId') for attribute in attributes if attribute.get('fieldId')]
        existing_fields = Field.query.filter(Field.id.in_(field_ids)).all()
        existing_field_ids = [field.id for field in existing_fields]

        for attribute in attributes:
            field_id = attribute.get('fieldId')
            value = attribute.get('value')

            if field_id in existing_field_ids:
                item_attribute = ItemAttribute(
                    item_id=item.id, field_id=field_id, value=value)
                db.session.add(item_attribute)
            else:
                return make_response(jsonify({"code": 400, "msg": f"Invalid field_id: {field_id}"}), 400)

        db.session.commit()

        result = {'id': item.id, 'name': item.name, 'seriesId': item.series_id}
        return make_response(jsonify({"code": 201, "msg": "Success", "data": result}), 201)

    except SQLAlchemyError as e:
        db.session.rollback()
        return make_response(jsonify({"code": 500, "msg": str(e)}), 500)

    finally:
        db.session.close()


def read(series_id):
    try:
        # Mapping of field data types to Python data types
        data_type_map = {
            'string': str,
            'number': (int, float),
            'boolean': bool,
            # Add other data types as needed
        }

        # Extract the filter criteria from the request body
        filters = request.json
        # Ensure the series_id is an integer
        series_id = int(series_id)

        # Pagination parameters
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 10))

        # Get the fields related to this series
        fields_query = db.session.query(Field).filter(
            Field.series_id == series_id)
        fields = {field.id: field for field in fields_query.all()}

        # Check if all required fields are in the request body
        required_fields_query = fields_query.filter(Field.is_required == True)
        required_fields = {
            field.id: field for field in required_fields_query.all()}
        for required_field_id in required_fields.keys():
            if not any(filter.get('fieldId') == required_field_id for filter in filters):
                return make_response(jsonify({"code": 400,
                                              "msg": f"Missing required field: {required_fields[required_field_id].name}"}), 400)

        # Create a SQL query to find the items
        items_query = db.session.query(Item).filter(
            Item.series_id == series_id)

        # Create a list to hold all filter conditions
        for filter_criteria in filters:
            field_id = filter_criteria['fieldId']
            field = fields[field_id]
            value = filter_criteria['value']
            operation = filter_criteria.get('operation', 'equals')

            # Check if the value is of the correct data type
            correct_type = data_type_map[field.data_type.lower()]
            if not isinstance(value, correct_type):
                return make_response(jsonify({
                    "code": 400,
                    "msg": f"Incorrect data type for field: {field.name}. Expected {field.data_type.lower()}, got {type(value).__name__}."
                }), 400)

            subquery = db.session.query(ItemAttribute.item_id).filter(
                and_(ItemAttribute.field_id == field_id, text(
                    f"CAST(item_attribute.value AS float) > {value}"))
                if operation == "greater" and field.data_type.lower() == "number" else
                and_(ItemAttribute.field_id == field_id, text(
                    f"CAST(item_attribute.value AS float) < {value}"))
                if operation == "less" and field.data_type.lower() == "number" else
                and_(ItemAttribute.field_id == field_id,
                     ItemAttribute.value == value)
            )

            items_query = items_query.filter(subquery.exists())

        # Paginate the items_query
        pagination = items_query.paginate(
            page=page, per_page=limit, error_out=False)
        items = pagination.items

        # Format the output
        data = []
        for item in items:
            fields_data = {field.id: db.session.query(ItemAttribute).filter(
                and_(ItemAttribute.item_id == item.id,
                     ItemAttribute.field_id == field.id)
            ).first().value for field in fields.values()}
            data.append({
                'itemId': item.id,
                'name': item.name,
                'seriesId': series_id,
                'fields': fields_data
            })

        return make_response(jsonify({"code": 200, "msg": "Success", "data": data}), 200)

    except SQLAlchemyError as e:
        db.session.rollback()
        return make_response(jsonify({"code": 500, "msg": str(e)}), 500)

    except Exception as e:
        return make_response(jsonify({"code": 500, "msg": str(e)}), 500)

    finally:
        db.session.close()
