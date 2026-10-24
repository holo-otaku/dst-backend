from flask import send_from_directory
from flask import current_app, jsonify, make_response, request, send_file, abort
from models.image import Image
from models.series import Field, ItemAttribute
from models.shared import db
from utils.permissions import check_field_permission
from sqlalchemy.exc import SQLAlchemyError
import uuid
import os
from PIL import Image as PILImage
from modules.exception import handle_exceptions


@handle_exceptions
def create():
    # Check if the 'image_data' field exists in the form data
    if 'image_data' not in request.files:
        return make_response(jsonify({"code": 400, "msg": "Missing image_data in form data"}), 400)

    # Get the file from the form data
    image_file = request.files['image_data']

    # Reject anything Pillow can't parse as an image
    try:
        with PILImage.open(image_file.stream) as img:
            img.verify()
    except (OSError, SyntaxError):
        return make_response(jsonify({"code": 400, "msg": "image_data is not a valid image"}), 400)

    # Save the file under IMG_PATH and store only its path, like product images
    image_dir = current_app.config["IMG_PATH"]
    os.makedirs(image_dir, exist_ok=True)
    image_name = str(uuid.uuid4())[:8]
    image_path = os.path.join(image_dir, f"{image_name}.png")
    image_file.stream.seek(0)
    image_file.save(image_path)

    # Create an Image instance and set its properties
    image = Image(name=image_name, path=image_path)

    # Add the image to the database
    db.session.add(image)
    db.session.commit()

    # Return the image ID as the response
    return make_response(jsonify({"code": 201, "msg": "Image created", "image_id": image.id}), 201)


@handle_exceptions
def read(image_id):
    if not image_id:
        # If the image ID is not found in the database, return a 404 Not Found response
        abort(404)

    image = db.session.get(Image, image_id)

    if image is None:
        return make_response(jsonify({"code": 404, "msg": 'Image not found'}), 404)

    # 圖片屬於 limit 欄位時，套用和商品欄位相同的 limit-field.read 檢查
    limit_ref = db.session.query(Field.id).join(ItemAttribute, ItemAttribute.field_id == Field.id).filter(
        Field.data_type == 'picture',
        Field.is_limit_field.is_(True),
        ItemAttribute.value == str(image_id),
    ).first()
    if limit_ref and not check_field_permission("limit-field.read"):
        return make_response(jsonify({"code": 403, "msg": "Permission denied"}), 403)

    # Extract the directory and filename from the image path
    image_directory = os.path.dirname(image.path)
    image_filename = os.path.basename(image.path)

    # Files are always saved as .png, but uploads may be JPEG, so sniff the real format
    try:
        with PILImage.open(image.path) as img:
            image_format = img.format
    except OSError:
        image_format = None
    mimetype = PILImage.MIME.get(image_format, 'application/octet-stream')
    extension = {'JPEG': 'jpg', 'PNG': 'png'}.get(image_format, 'bin')

    return send_from_directory(directory=image_directory, path=image_filename, mimetype=mimetype, as_attachment=True, download_name='%s.%s' % (image_id, extension))
