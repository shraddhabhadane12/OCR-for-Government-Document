#!/bin/bash

# Set environment variables
export FLASK_ENV=production
export PYTHONPATH=/opt/render/project/src/backend

# Start the application
cd backend && python app.py