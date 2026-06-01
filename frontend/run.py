"""
Application Entry Point

Runs the Flask development server.
"""

import os
import sys

# Ensure frontend/app is imported, not Backend/app
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from app import create_app

# Create application instance
app = create_app(os.getenv('FLASK_ENV', 'development'))

if __name__ == '__main__':
    # Run development server
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=app.config['DEBUG']
    )
