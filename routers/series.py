from flask import Blueprint, request
from controller.series import create, read, read_multi, update, delete
from controller.access import check_permission
from flask_jwt_extended import get_jwt_identity

series = Blueprint("series", __name__)


@series.route("", methods=["GET"])
@check_permission('series.read')
def get_serieses():

    return read_multi()


@series.route("/<int:series_id>", methods=["GET"])
@check_permission('series.read')
def get_series(series_id):

    return read(series_id)


@series.route("", methods=["POST"])
@check_permission('series.create')
def create_series():
    data = request.get_json()
    created_by = get_jwt_identity()

    return create(data, created_by)


@series.route("<int:series_id>", methods=["PATCH"])
@check_permission('series.edit')
def update_series(series_id):
    data = request.get_json()

    return update(series_id, data)


@series.route("<int:series_id>", methods=["DELETE"])
@check_permission('series.delete')
def delete_series(series_id):

    return delete(series_id)
