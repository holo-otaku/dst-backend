from flask import Blueprint, request
from controller.series import create, read, read_multi, update, delete
from flask_jwt_extended import jwt_required

series = Blueprint("series", __name__)


@series.route("", methods=["GET"])
@jwt_required()
def get_serieses():

    return read_multi()


@series.route("/<int:series_id>", methods=["GET"])
@jwt_required()
def get_series(series_id):

    return read(series_id)


@series.route("", methods=["POST"])
@jwt_required()
def create_series():
    data = request.get_json()

    return create(data)


@series.route("<int:series_id>", methods=["PUT"])
@jwt_required()
def update_series(series_id):
    data = request.get_json()

    return update(series_id, data)


@series.route("<int:series_id>", methods=["DELETE"])
@jwt_required()
def delete_series(series_id):

    return delete(series_id)
