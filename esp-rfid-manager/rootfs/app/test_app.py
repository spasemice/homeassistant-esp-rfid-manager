#!/usr/bin/env python3
"""
Minimal test Flask app to debug startup issues
"""

import os
import sys
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

print("Starting minimal test app...")
sys.stdout.flush()

try:
    from flask import Flask, jsonify
    print("Flask imported successfully")
    sys.stdout.flush()
    
    # Create minimal Flask app
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'test-key'
    
    print("Flask app created")
    sys.stdout.flush()
    
    @app.route('/')
    def test_home():
        return jsonify({
            'status': 'ok',
            'message': 'Test Flask app is working!',
            'version': 'test-1.0'
        })
    
    @app.route('/health')
    def test_health():
        return jsonify({'status': 'healthy'})
    
    print("Routes defined")
    sys.stdout.flush()
    
    if __name__ == '__main__':
        print("Starting Flask server on port 8080...")
        sys.stdout.flush()
        
        # Get environment info
        supervisor_token = os.getenv('SUPERVISOR_TOKEN', '')
        print(f"SUPERVISOR_TOKEN present: {len(supervisor_token) > 0}")
        print(f"Python version: {sys.version}")
        print(f"Working directory: {os.getcwd()}")
        sys.stdout.flush()
        
        # Start Flask
        app.run(host='0.0.0.0', port=8080, debug=False)
        
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1) 