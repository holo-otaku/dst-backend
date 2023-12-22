from flask import Blueprint
from controller.archive import update
from controller.access import check_permission

archive = Blueprint("archive", __name__)

@archive.route('/<int:item_id>', methods=['PATCH'])
@check_permission('archive.update')
def edit_archive(item_id):

    return update(item_id)
