from flask import Flask
from .config import config_by_name
from .extensions import mongo, jwt, cors, MongoJSONProvider
from .auth.routes import auth_bp
from .resume.routes import resume_bp
from .ats.routes import ats_bp
from .ai.cover_letter import cover_letter_bp
from .jobs.routes import jobs_bp
from .tracker.routes import tracker_bp
from .selenium_apply.routes import apply_bp
from .jobs.models import ScrapedJobModel
from .courses.routes import courses_bp
from .courses.models import ScrapedCourseModel
import os

def create_app(config_name="development"):
    # Template and static folders should be in the root directory
    app = Flask(__name__, template_folder="../templates", static_folder="../static")
    app.json = MongoJSONProvider(app)
    app.config.from_object(config_by_name[config_name])

    # Initialize extensions
    mongo.init_app(app)
    jwt.init_app(app)
    cors.init_app(app, resources={r"/api/*": {"origins": "*"}})

    # Ensure MongoDB indexes for scraped_jobs
    with app.app_context():
        try:
            ScrapedJobModel().ensure_indexes()
            ScrapedCourseModel().ensure_indexes()
        except Exception:
            pass  # Non-fatal — indexes will be created on first write


    # Create uploads folder if it doesn't exist
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], 'screenshots'), exist_ok=True)
    os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], 'resumes'), exist_ok=True)

    # We will register blueprints later as we create them
    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    app.register_blueprint(resume_bp, url_prefix="/api/resume")
    app.register_blueprint(ats_bp, url_prefix="/api/ats")
    app.register_blueprint(cover_letter_bp, url_prefix="/api/cover-letter")
    app.register_blueprint(jobs_bp, url_prefix="/api/jobs")
    app.register_blueprint(tracker_bp, url_prefix="/api/tracker")
    app.register_blueprint(apply_bp, url_prefix="/api/apply")
    app.register_blueprint(courses_bp, url_prefix="/api/courses")
    
    @app.route("/")
    def index():
        from flask import redirect
        return redirect("/dashboard")

    @app.route("/dashboard")
    def dashboard():
        from flask import render_template
        return render_template("dashboard/index.html")

    @app.route("/auth/login")
    def login():
        from flask import render_template
        return render_template("auth/login.html")

    @app.route("/auth/register")
    def register():
        from flask import render_template
        return render_template("auth/register.html")


    @app.route("/tracker")
    def tracker():
        from flask import render_template
        return render_template("tracker/board.html")

    @app.route("/jobs")
    def jobs_view():
        from flask import render_template
        return render_template("jobs/recommendations.html")
        
    @app.route("/ats")
    def ats_view():
        from flask import render_template
        return render_template("ats/results.html")

    @app.route("/cover-letter")
    def cover_letter_view():
        from flask import render_template
        return render_template("cover_letter/editor.html")
        
    @app.route("/courses")
    def courses_view():
        from flask import render_template
        return render_template("courses/dashboard.html")

    @app.route("/courses/saved")
    def courses_saved_view():
        from flask import render_template
        return render_template("courses/saved.html")
        
    return app
