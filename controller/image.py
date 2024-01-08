from flask import send_from_directory
from flask import current_app, jsonify, make_response, request, send_file, abort
from models.image import Image
from models.shared import db
from sqlalchemy.exc import SQLAlchemyError
import uuid
import os
from modules.exception import handle_exceptions


@handle_exceptions
def create():
    # Check if the 'image_data' field exists in the form data
    if 'image_data' not in request.files:
        return make_response(jsonify({"code": 400, "msg": "Missing image_data in form data"}), 400)

    # Get the file from the form data
    image_file = request.files['image_data']

    # Read the image file as bytes
    image_bytes = image_file.read()

    # Create an Image instance and set its properties
    image = Image(data=image_bytes, name=str(uuid.uuid4())[:8])

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

    image = Image.query.get(image_id)

    if image is None:
        return make_response(jsonify({"code": 404, "msg": 'Image not found'}), 404)

    # Extract the directory and filename from the image path
    image_directory = os.path.dirname(image.path)
    image_filename = os.path.basename(image.path)

    return send_from_directory(directory=image_directory, path=image_filename, mimetype='image/jpeg', as_attachment=True, download_name='%s.jpg' % image_id)
