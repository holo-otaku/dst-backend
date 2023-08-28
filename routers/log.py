from flask import Blueprint, request
from controller.log import read_multi, user_logs
from controller.access import check_permission

log = Blueprint("log", __name__)


@log.route("", methods=["GET"])
@check_permission('log.read')
def get_logs():

    return read_multi()


@log.route('/user/<int:user_id>', methods=['GET'])
def get_user_logs(user_id):

    return user_logs(user_id)
