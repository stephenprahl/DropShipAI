"""Error handlers for the application."""
from flask import render_template, jsonify, request
from . import db

def not_found_error(error):
    """Handle 404 errors."""
    if request.accept_mimetypes.accept_json and not request.accept_mimetypes.accept_html:
        response = jsonify({'error': 'Not found'})
        response.status_code = 404
        return response
    return render_template('errors/404.html'), 404

def internal_error(error):
    """Handle 500 errors."""
    db.session.rollback()
    if request.accept_mimetypes.accept_json and not request.accept_mimetypes.accept_html:
        response = jsonify({'error': 'Internal server error'})
        response.status_code = 500
        return response
    return render_template('errors/500.html'), 500

def forbidden_error(error):
    """Handle 403 errors."""
    if request.accept_mimetypes.accept_json and not request.accept_mimetypes.accept_html:
        response = jsonify({'error': 'Forbidden'})
        response.status_code = 403
        return response
    return render_template('errors/403.html'), 403

def ratelimit_error(error):
    """Handle 429 errors (rate limiting)."""
    if request.accept_mimetypes.accept_json and not request.accept_mimetypes.accept_html:
        response = jsonify({
            'error': 'Too many requests',
            'message': 'You have exceeded your request limit.'
        })
        response.status_code = 429
        return response
    return render_template('errors/429.html'), 429

def bad_request_error(error):
    """Handle 400 errors."""
    if request.accept_mimetypes.accept_json and not request.accept_mimetypes.accept_html:
        response = jsonify({
            'error': 'Bad request',
            'message': str(error)
        })
        response.status_code = 400
        return response
    return render_template('errors/400.html', error=error), 400

def unauthorized_error(error):
    """Handle 401 errors."""
    if request.accept_mimetypes.accept_json and not request.accept_mimetypes.accept_html:
        response = jsonify({
            'error': 'Unauthorized',
            'message': 'Authentication is required to access this resource.'
        })
        response.status_code = 401
        response.headers['WWW-Authenticate'] = 'Basic realm="Login Required"'
        return response
    return render_template('errors/401.html'), 401
