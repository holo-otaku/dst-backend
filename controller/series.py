from flask import current_app, jsonify, make_response, request
from models.series import Series, Field, Item, ItemAttribute
from models.image import Image
from models.shared import db
from models.mapping_table import data_type_map
from sqlalchemy.exc import SQLAlchemyError
from flask_jwt_extended import get_jwt_identity
import os


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
            for index, field_data in enumerate(fields_data):
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
                    is_erp=field_is_erp,
                    sequence=index
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

            field_data = []
            for f in series.fields:
                unique_values = []
                if f.is_filtered and (f.data_type == "string" or f.data_type == "number"):
                    distinct_count = db.session.query(ItemAttribute.value).filter(
                        ItemAttribute.field_id == f.id).distinct().count()
                    if distinct_count <= 30:
                        unique_values = db.session.query(ItemAttribute.value).filter(
                            ItemAttribute.field_id == f.id).distinct().all()
                        unique_values = [
                            attr.value for attr in unique_values if attr.value is not None]

                field_data.append({
                    'id': f.id,
                    'name': f.name,
                    'dataType': f.data_type,
                    'isFiltered': f.is_filtered,
                    'isRequired': f.is_required,
                    'isErp': f.is_erp,
                    'values': unique_values,
                    "sequence": f.sequence,
                })

            data['fields'] = sorted(field_data, key=lambda x: x['sequence'])

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

        # Initialize the base query
        base_query = Series.query.filter_by(status=1)

        if keyword:
            base_query = base_query.filter(Series.name.ilike(f"%{keyword}%"))

        # Get the total count before applying pagination
        total_count = base_query.count()

        # Apply pagination to the query
        series = base_query.paginate(page=page, per_page=limit).items

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
                sorted_fields = sorted(s.fields, key=lambda x: x.sequence)

                field_data = [{'id': f.id,
                               'name': f.name,
                               'dataType': f.data_type,
                               'isFiltered': f.is_filtered,
                               'isRequired': f.is_required,
                               'isErp': f.is_erp,
                               'sequence': f.sequence} for f in sorted_fields]
                data['fields'] = field_data

            result.append(data)

        return make_response(jsonify({"code": 200, "msg": "Success", "data": result, "totalCount": total_count}), 200)

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
        series.name = data.get('name', series.name)

        # Check for duplicate isErp in update data and create data
        erp_count = sum(1 for field_data in data.get(
            'fields', []) if field_data.get('isErp'))
        erp_count += sum(1 for create_data in data.get('create',
                         []) if create_data.get('isErp'))

        if erp_count > 1:
            return make_response(jsonify({"code": 400, "msg": "Only one field can be set as Erp in a series!"}), 400)

        # Handle field updates
        fields_data = data.get('fields', [])
        for index, field_data in enumerate(fields_data):
            field_id = field_data.get('id')
            field = db.session.get(Field, field_id)

            if not field:
                return make_response(jsonify({"code": 404, "msg": f"Field with ID {field_id} not found"}), 404)

            # Check if there are any item attributes using this field
            has_related_item_attributes = db.session.query(
                ItemAttribute).filter_by(field_id=field.id).first()
            if has_related_item_attributes and field.data_type != field_data.get('dataType').lower():
                return make_response(jsonify({"code": 400, "msg": f"Cannot update data type of field with ID {field_id} since it's being used in ItemAttribute"}), 400)

            field.name = field_data.get('name')
            field.data_type = field_data.get('dataType')
            field.is_filtered = field_data.get('isFiltered')
            field.is_required = field_data.get('isRequired')
            field.is_erp = field_data.get('isErp')
            field.sequence = index  # Set sequence based on the order in fields_data

        # Handle field creation
        creates_data = data.get('create', [])
        for create_data in creates_data:
            new_field = Field(name=create_data.get('name'),
                              data_type=create_data.get('dataType').lower(),
                              is_filtered=create_data.get('isFiltered'),
                              is_required=create_data.get('isRequired'),
                              is_erp=create_data.get('isErp'),
                              series_id=series_id,
                              sequence=create_data.get('sequence'))
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
            # 获取要删除的字段
            field_to_delete = db.session.get(Field, delete_id)
            if not field_to_delete:
                continue  # 如果字段不存在，跳过此次循环

            # 如果字段的数据类型是 "picture"，则删除与其关联的所有图片
            if field_to_delete.data_type == "picture":
                # 查询所有与此字段关联的 item_attribute
                item_attributes = db.session.query(
                    ItemAttribute).filter_by(field_id=delete_id).all()

                for item_attribute in item_attributes:
                    image_to_delete = db.session.query(
                        Image).get(item_attribute.value)
                    if image_to_delete and os.path.exists(image_to_delete.path):
                        os.remove(image_to_delete.path)
                        db.session.delete(image_to_delete)

            # 删除与此字段关联的所有 item_attribute
            db.session.query(ItemAttribute).filter_by(
                field_id=delete_id).delete()

            # 最后删除字段本身
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
