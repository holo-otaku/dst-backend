from flask import Blueprint, request
from controller.archive import create, delete
from controller.access import check_permission

archive = Blueprint("archive", __name__)


@archive.route("", methods=["POST"])
@check_permission("archive.create")
def create_archive():
    data = request.get_json()

    return create(data)


@archive.route("", methods=["DELETE"])
@check_permission("archive.delete")
def delete_archive():
    data = request.get_json()

    return delete(data)
