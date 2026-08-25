"""Container entry point that starts the app-level RunPod worker adapter."""

from app.runpod_handler import start_serverless


if __name__ == "__main__":
    start_serverless()
