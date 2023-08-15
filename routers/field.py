from flask import Blueprint, request
from controller.field import update
from controller.access import check_permission

field = Blueprint("field", __name__)


@field.route("/<int:field_id>", methods=["PATCH"])
@check_permission('series.edit')
def update_field(field_id):
    data = request.get_json()

    return update(field_id, data)
