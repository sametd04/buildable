#!/bin/bash
# Quick start script for Buildable backend

# Check if .env exists
if [ ! -f .env ]; then
    echo "Warning: .env file not found. Please copy .env.example to .env and configure it."
    echo "Example: cp .env.example .env"
fi

# Run the FastAPI server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

