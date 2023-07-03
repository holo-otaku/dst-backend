from flask import Blueprint, request
from controller.series import create, read, read_multi, update, delete
from controller.access import check_permission

series = Blueprint("series", __name__)


@series.route("/multi", methods=["GET"])
@check_permission('read')
def get_serieses():

    return read_multi()


@series.route("/<int:series_id>", methods=["GET"])
@check_permission('read')
def get_series(series_id):

    return read(series_id)


@series.route("", methods=["POST"])
@check_permission('create')
def create_series():
    data = request.get_json()

    return create(data)


@series.route("<int:series_id>", methods=["PATCH"])
@check_permission('edit')
def update_series(series_id):
    data = request.get_json()

    return update(series_id, data)


@series.route("<int:series_id>", methods=["DELETE"])
@check_permission('delete')
def delete_series(series_id):

    return delete(series_id)
