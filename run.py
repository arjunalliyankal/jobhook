from app import create_app
import os

app = create_app(os.getenv("FLASK_ENV", "development"))

if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=5000,
        debug=app.config["DEBUG"],
        reloader_type="stat",   # avoids WinError 10038 + stdlib scanning with watchdog on Python 3.14
    )
