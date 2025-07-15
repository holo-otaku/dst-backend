from flask import current_app, jsonify, make_response, request
from models.series import Series, Field, Item, ItemAttribute
from models.image import Image
from models.shared import db
from models.mapping_table import data_type_map
from controller.erp import get_erp_fields_metadata
from sqlalchemy.exc import SQLAlchemyError
from flask_jwt_extended import get_jwt_identity
import os
from modules.exception import handle_exceptions


@handle_exceptions
def create(data, created_by):
    name = data.get("name")

    if not name or not created_by:
        return make_response(jsonify({"code": 400, "msg": "Incomplete data"}), 400)

    series = Series(name=name, created_by=created_by)

    # Check if 'fields' data is provided in the request
    fields_data = data.get("fields", [])
    if fields_data:
        # Check search_erp only one
        erp_count = 0
        for index, field_data in enumerate(fields_data):
            field_name = field_data.get("name")
            field_data_type = field_data.get("dataType").lower()

            if field_data_type not in data_type_map:
                return make_response(
                    jsonify({"code": 400, "msg": f"{field_name} DataType Error"}), 400
                )

            field_is_filtered = field_data.get("isFiltered", False)
            field_is_required = field_data.get("isRequired", False)
            field_search_erp = field_data.get("searchErp", False)
            field_is_limit_field = field_data.get("isLimitField", False)
            field_is_erp = field_data.get("isErp", False)

            if field_search_erp:
                erp_count += 1
                if erp_count > 1:
                    return make_response(
                        jsonify({"code": 400, "msg": "Erp can only be set once !"}), 400
                    )

            # Create a new Field object and associate it with the series
            field = Field(
                name=field_name,
                data_type=field_data_type,
                is_filtered=field_is_filtered,
                is_required=field_is_required,
                search_erp=field_search_erp,
                is_limit_field=field_is_limit_field,
                is_erp=field_is_erp,
                sequence=index,
            )
            series.fields.append(field)

    db.session.add(series)
    db.session.commit()

    result = {"id": series.id, "name": series.name, "createdBy": series.created_by}
    return make_response(jsonify({"code": 201, "msg": "Success", "data": result}), 201)


@handle_exceptions
def read(series_id):
    series = (
        db.session.query(Series)
        .filter(Series.id == series_id, Series.status == 1)
        .first()
    )

    if not series:
        return make_response(jsonify({"code": 404, "msg": "Series not found"}), 404)

    data = {
        "id": series.id,
        "name": series.name,
        "createdBy": str(series.creator.username),
        "createdAt": series.created_at.strftime("%Y-%m-%d %H:%M:%S"),
    }

    field_data = []
    has_search_erp = False
    # Process fields that are already in the database
    for f in series.fields:
        # Skip ERP fields for now, they will be handled separately
        if f.is_erp:
            continue

        if f.search_erp:
            has_search_erp = True

        field_data.append(
            {
                "id": int(f.id),
                "name": str(f.name),
                "dataType": str(f.data_type),
                "isFiltered": bool(f.is_filtered),
                "isRequired": bool(f.is_required),
                "searchErp": bool(f.search_erp),
                "isErp": bool(f.is_erp),
                "isLimitField": bool(f.is_limit_field),
                "sequence": int(f.sequence),
            }
        )

    # If a field with search_erp is found, fetch and merge ERP fields
    if has_search_erp:
        erp_fields_metadata = get_erp_fields_metadata()

        # Get all existing ERP fields for this series to check against
        existing_erp_fields = {
            field.name: field for field in series.fields if field.is_erp
        }

        for erp_meta in erp_fields_metadata:
            erp_field_name = erp_meta["name"]

            # Check if this ERP field is already saved in our DB
            if erp_field_name in existing_erp_fields:
                # If yes, use its data
                f = existing_erp_fields[erp_field_name]
                field_data.append(
                    {
                        "id": int(f.id),
                        "name": str(f.name),
                        "dataType": str(f.data_type),
                        "isFiltered": bool(f.is_filtered),
                        "isRequired": bool(f.is_required),
                        "searchErp": bool(f.search_erp),
                        "isErp": bool(f.is_erp),
                        "isLimitField": bool(f.is_limit_field),
                        "sequence": int(f.sequence),
                    }
                )
            else:
                # If no, present it as a new, unsaved field
                field_data.append(
                    {
                        "id": None,
                        "name": erp_field_name,
                        "dataType": erp_meta["dataType"],
                        "isFiltered": False,
                        "isRequired": False,
                        "searchErp": False,
                        "isErp": True,
                        "isLimitField": False,  # Default for non-saved ERP fields
                        "sequence": 999,  # High sequence to appear at the end
                    }
                )

    data["fields"] = sorted(
        field_data,
        key=lambda x: x["sequence"] if x["sequence"] is not None else float("inf"),
    )

    return make_response(jsonify({"code": 200, "msg": "Success", "data": data}), 200)


@handle_exceptions
def read_multi():
    page = int(request.args.get("page", 1))
    limit = int(request.args.get("limit", 10))
    keyword = str(request.args.get("keyword", ""))
    show_field = bool(int(request.args.get("showField", False)))

    # Initialize the base query
    base_query = db.session.query(Series).filter_by(status=1).order_by(Series.name)

    if keyword:
        base_query = base_query.filter(Series.name.ilike(f"%{keyword}%"))

    # Get the total count before applying pagination
    total_count = base_query.count()

    # Apply pagination to the query
    series = base_query.paginate(page=page, per_page=limit).items

    result = []
    for s in series:
        data = {
            "id": s.id,
            "name": s.name,
            "createdBy": s.creator.username,
            "createdAt": s.created_at.strftime("%Y-%m-%d %H:%M:%S"),
        }

        if show_field:
            # Filter out ERP fields for the multi-read view for simplicity
            internal_fields = [f for f in s.fields if not f.is_erp]
            sorted_fields = sorted(internal_fields, key=lambda x: x.sequence)

            field_data = [
                {
                    "id": f.id,
                    "name": f.name,
                    "dataType": f.data_type,
                    "isFiltered": f.is_filtered,
                    "isRequired": f.is_required,
                    "searchErp": f.search_erp,
                    "isErp": f.is_erp,
                    "isLimitField": f.is_limit_field,
                    "sequence": f.sequence,
                }
                for f in sorted_fields
            ]
            data["fields"] = field_data

        result.append(data)

    return make_response(
        jsonify(
            {"code": 200, "msg": "Success", "data": result, "totalCount": total_count}
        ),
        200,
    )


@handle_exceptions
def update(series_id, data):
    series = db.session.get(Series, series_id)
    if not series:
        return make_response(jsonify({"code": 404, "msg": "Series not found"}), 404)

    series.name = data.get("name", series.name)

    # Consolidate all fields to check for duplicate searchErp
    all_fields_data = data.get("fields", []) + data.get("create", [])
    if sum(1 for f in all_fields_data if f.get("searchErp")) > 1:
        return make_response(
            jsonify(
                {
                    "code": 400,
                    "msg": "Only one field can be set as searchErp in a series!",
                }
            ),
            400,
        )

    # Handle field updates
    fields_data = data.get("fields", [])
    for field_data in fields_data:
        field_id = field_data.get("id")
        if not field_id:
            continue  # Should be in create list

        field = db.session.get(Field, field_id)
        if not field:
            return make_response(
                jsonify({"code": 404, "msg": f"Field with ID {field_id} not found"}),
                404,
            )

        # Prevent data type change if attributes exist
        if (
            field.data_type != field_data.get("dataType").lower()
            and db.session.query(ItemAttribute).filter_by(field_id=field.id).first()
        ):
            return make_response(
                jsonify(
                    {
                        "code": 400,
                        "msg": f"Cannot update data type of field '{field.name}' as it is in use.",
                    }
                ),
                400,
            )

        field.name = field_data.get("name", field.name)
        field.data_type = field_data.get("dataType", field.data_type).lower()
        field.is_filtered = field_data.get("isFiltered", field.is_filtered)
        field.is_required = field_data.get("isRequired", field.is_required)
        field.search_erp = field_data.get("searchErp", field.search_erp)
        field.is_limit_field = field_data.get("isLimitField", field.is_limit_field)
        # is_erp is set at creation and should not be changed
        field.sequence = field_data.get("sequence", field.sequence)

    # Handle field creation
    creates_data = data.get("create", [])
    for create_data in creates_data:
        new_field = Field(
            name=create_data.get("name"),
            data_type=create_data.get("dataType").lower(),
            is_filtered=create_data.get("isFiltered", False),
            is_required=create_data.get("isRequired", False),
            search_erp=create_data.get("searchErp", False),
            is_erp=create_data.get("isErp", False),  # Important flag
            is_limit_field=create_data.get("isLimitField", False),
            series_id=series_id,
            sequence=create_data.get("sequence"),
        )
        db.session.add(new_field)
        db.session.flush()  # Flush to get new_field.id

        # Add a null ItemAttribute for this new field to all existing items in the series
        items_in_series = (
            db.session.query(Item.id).filter(Item.series_id == series_id).all()
        )
        for item_id in items_in_series:
            new_item_attribute = ItemAttribute(
                item_id=item_id[0], field_id=new_field.id, value=None
            )
            db.session.add(new_item_attribute)

    # Handle field deletion
    delete_ids = data.get("delete", [])
    for delete_id in delete_ids:
        field_to_delete = db.session.get(Field, delete_id)
        if not field_to_delete:
            continue

        # If field type is "picture", delete associated images
        if field_to_delete.data_type == "picture":
            item_attributes = (
                db.session.query(ItemAttribute).filter_by(field_id=delete_id).all()
            )
            for attr in item_attributes:
                if attr.value:
                    image_to_delete = db.session.get(Image, attr.value)
                    if image_to_delete:
                        if os.path.exists(image_to_delete.path):
                            os.remove(image_to_delete.path)
                        db.session.delete(image_to_delete)

        # Delete all item attributes associated with this field
        db.session.query(ItemAttribute).filter_by(field_id=delete_id).delete(
            synchronize_session=False
        )

        # Finally, delete the field itself
        db.session.delete(field_to_delete)

    db.session.commit()

    return make_response(jsonify({"code": 200, "msg": "Success"}), 200)


@handle_exceptions
def delete(series_id):
    series = db.session.get(Series, series_id)

    if not series:
        return make_response(jsonify({"code": 404, "msg": "Series not found"}), 404)

    # Set series status to 0 (deleted)
    series.status = 0

    db.session.commit()
    return make_response(jsonify({"code": 200, "msg": "Series deleted"}), 200)
