from flask import Response
from flask_swagger_ui import get_swaggerui_blueprint

# Get the path to the Swagger JSON file
SWAGGER_URL = '/api/docs'
# Update with the path to your Swagger YAML file
API_URL = '/api/docs/swagger'

# Create the Swagger UI blueprint
swagger_ui_blueprint = get_swaggerui_blueprint(
    SWAGGER_URL,
    API_URL,
    config={
        'app_name': "DST API"  # Customize the app name
    }
)


@swagger_ui_blueprint.route("/swagger", methods=["GET"])
def get():
    with open('swagger.yaml', 'r') as file:
        content = file.read()
    return Response(content, mimetype='text/plain')
