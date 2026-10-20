import os

os.makedirs('instance', exist_ok=True)
os.makedirs('uploads', exist_ok=True)

from app import app

if __name__ == '__main__':
    app.run(debug=True)
