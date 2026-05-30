from flask import Flask, jsonify, render_template, send_from_directory
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from config import config
from models import db
import os

# Import all modules
from modules.auth_module import auth_module
from modules.user_module import user_module
from modules.prediction_module import prediction_module, init_prediction_models
from modules.history_module import history_module
from modules.analytics_module import analytics_module
from modules.report_module import report_module
from modules.admin_module import admin_module

def create_app(config_name='development'):
    """Application factory with modular architecture"""
    app = Flask(__name__, template_folder='templates', static_folder='static')
    
    # Load configuration
    app.config.from_object(config[config_name])
    
    # Initialize extensions
    CORS(app)
    db.init_app(app)
    JWTManager(app)
    
    # Register all modules (blueprints)
    print("\n" + "="*60)
    print("Registering Backend Modules")
    print("="*60)
    
    modules = [
        (auth_module, "Module 1: Authentication Module"),
        (user_module, "Module 2: User Management Module"),
        (prediction_module, "Module 3: Prediction Module"),
        (history_module, "Module 4: History Module"),
        (analytics_module, "Module 5: Analytics Module"),
        (report_module, "Module 6: Report Generation Module"),
        (admin_module, "Module 7: Admin Module")
    ]
    
    for module, description in modules:
        app.register_blueprint(module)
        print(f"✓ {description} registered")
    
    print("="*60 + "\n")
    
    # Create database tables
    with app.app_context():
        db.create_all()
        print("✓ Database tables created")
        
        # Initialize ML models
        print("\nInitializing ML Models...")
        try:
            if init_prediction_models():
                print("✓ All models initialized successfully\n")
            else:
                print("⚠ Warning: ML models not available - prediction features disabled")
                print("  You can still test auth, user, history, and analytics modules\n")
        except Exception as e:
            print(f"⚠ Warning: ML initialization failed: {e}")
            print("  You can still test auth, user, history, and analytics modules\n")
    
    # Root endpoint - serve homepage
    @app.route('/', methods=['GET'])
    def home():
        try:
            return render_template('index.html')
        except Exception as e:
            return jsonify({
                'error': 'Template error',
                'message': str(e),
                'note': 'Try /api/health or /test'
            }), 500
    
    # Simple test endpoint
    @app.route('/test', methods=['GET'])
    def test():
        return '''
        <html>
        <head><title>Test Page</title></head>
        <body style="font-family: Arial; padding: 50px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white;">
            <h1>✅ Server is Working!</h1>
            <p>If you see this page, your Flask server is running correctly.</p>
            <h2>Test These Links:</h2>
            <ul>
                <li><a href="/api/health" style="color: white;">Health Check (JSON)</a></li>
                <li><a href="/api/modules" style="color: white;">Modules Info (JSON)</a></li>
                <li><a href="/register.html" style="color: white;">Registration Page</a></li>
                <li><a href="/login.html" style="color: white;">Login Page</a></li>
            </ul>
            <h2>Use Postman for API Testing:</h2>
            <p>Import: <code>backend/Postman_Collection.json</code></p>
        </body>
        </html>
        '''
    
    # Registration page
    @app.route('/register.html', methods=['GET'])
    def register_page():
        return render_template('register.html')
    
    # Login page
    @app.route('/login.html', methods=['GET'])
    def login_page():
        return render_template('login.html')
    
    # Dashboard page
    @app.route('/dashboard.html', methods=['GET'])
    def dashboard_page():
        return render_template('dashboard.html')
    
    # Health check endpoint
    @app.route('/api/health', methods=['GET'])
    def health_check():
        return jsonify({
            'status': 'healthy',
            'message': 'API is running',
            'modules': [
                'auth_module',
                'user_module',
                'prediction_module',
                'history_module',
                'analytics_module',
                'report_module',
                'admin_module'
            ]
        }), 200
    
    # Module info endpoint
    @app.route('/api/modules', methods=['GET'])
    def module_info():
        return jsonify({
            'total_modules': 5,
            'modules': [
                {
                    'name': 'auth_module',
                    'description': 'Authentication and session management',
                    'endpoints': ['/api/auth/register', '/api/auth/login', '/api/auth/logout']
                },
                {
                    'name': 'user_module',
                    'description': 'User profile and account management',
                    'endpoints': ['/api/user/profile', '/api/user/list']
                },
                {
                    'name': 'prediction_module',
                    'description': 'AI predictions for age and smile detection',
                    'endpoints': ['/api/prediction/analyze']
                },
                {
                    'name': 'history_module',
                    'description': 'Prediction history and statistics',
                    'endpoints': ['/api/history/predictions', '/api/history/statistics', '/api/history/recent']
                },
                {
                    'name': 'analytics_module',
                    'description': 'Advanced analytics and reporting',
                    'endpoints': ['/api/analytics/trends', '/api/analytics/report', '/api/analytics/compare']
                }
            ]
        }), 200
    
    # Error handlers
    @app.errorhandler(404)
    def not_found(error):
        return jsonify({'error': 'Resource not found'}), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        return jsonify({'error': 'Internal server error'}), 500
    
    return app

if __name__ == '__main__':
    app = create_app(os.getenv('FLASK_ENV', 'development'))
    port = int(os.getenv('PORT', 5000))  # Fixed to port 5000
    print("\n" + "="*60)
    print("Starting Flask Server")
    print("="*60)
    print(f"Server: http://localhost:{port}")
    print(f"Test Page: http://localhost:{port}/test")
    print(f"Health Check: http://localhost:{port}/api/health")
    print(f"Register: http://localhost:{port}/api/auth/register")
    print("="*60 + "\n")
    app.run(host='0.0.0.0', port=port, debug=True)
