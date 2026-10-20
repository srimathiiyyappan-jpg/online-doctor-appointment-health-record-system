import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg'}
MAX_CONTENT_LENGTH = 2 * 1024 * 1024
DATABASE_PATH = os.environ.get('APP_DB_PATH', os.path.join(BASE_DIR, 'instance', 'healthcare_app.db'))
