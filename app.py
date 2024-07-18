from flask import Flask, jsonify, request, redirect, url_for, send_from_directory, render_template, session, flash
from functools import wraps
from bson import ObjectId
from flask.json import JSONEncoder
import requests
from bs4 import BeautifulSoup
from pymongo import MongoClient
import bcrypt
from datetime import datetime, timedelta
import dateutil.parser
import bleach
import re
from celery import Celery
from flask_cors import CORS
import os
from werkzeug.security import generate_password_hash, check_password_hash
import pytz

class CustomJSONEncoder(JSONEncoder):
    def default(self, obj):
        if isinstance(obj, ObjectId):
            return str(obj)
        return super(CustomJSONEncoder, self).default(obj)

app = Flask(__name__, static_url_path='', static_folder='mm3/build')
app.json_encoder = CustomJSONEncoder
CORS(app)
app.config.update(
    CELERY_BROKER_URL='redis://localhost:6379/0',
    CELERY_RESULT_BACKEND='redis://redis:6379/0',
    SECRET_KEY='your_secret_key'
)

def make_celery(app):
    celery = Celery(app.import_name, backend=app.config['CELERY_RESULT_BACKEND'], broker=app.config['CELERY_BROKER_URL'])
    celery.conf.update(app.config)
    return celery

celery = make_celery(app)

client = MongoClient('mongodb://mongodb:27017/')
db = client['media_monitoring']

def create_indexes():
    db['users'].create_index([('username', 1)], unique=True)
    db['alerts'].create_index([('title', 'text'), ('description', 'text')])
    db['configurations'].create_index([('name', 1)], unique=True)

@app.before_first_request
def initialize_app():
    create_indexes()

def load_config_from_db():
    config = db['configurations'].find_one({"name": "default"})
    if not config:
        raise Exception("Failed to load configuration from MongoDB")
    return config

def now_bulgarian():
    return datetime.now(pytz.timezone('Europe/Sofia'))

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            return redirect(url_for('login'))
        user = db['users'].find_one({'username': session['user']})
        if not user:
            session.pop('user', None)
            return redirect(url_for('login'))
        db['users'].update_one({'username': session['user']}, {'$set': {'last_seen': now_bulgarian()}})
        return f(*args, **kwargs)
    return decorated_function

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = db['users'].find_one({'username': username})
        if user and check_password_hash(user['password'], password):
            session['user'] = username
            db['user_activity'].insert_one({'username': username, 'activity_type': 'login', 'timestamp': now_bulgarian()})
            db['users'].update_one({'username': username}, {'$set': {'last_seen': now_bulgarian()}})
            return redirect(url_for('config_management'))
        flash('Invalid username or password')
    return render_template('login.html')

@app.route('/logout')
def logout():
    username = session.get('user')
    if username:
        db['user_activity'].insert_one({'username': username, 'activity_type': 'logout', 'timestamp': now_bulgarian()})
        db['users'].update_one({'username': username}, {'$set': {'last_seen': now_bulgarian() - timedelta(days=365)}})
    session.pop('user', None)
    return redirect(url_for('login'))

@app.route('/online-users')
@login_required
def online_users():
    threshold = now_bulgarian() - timedelta(minutes=5)
    online_users = db['users'].find({'last_seen': {'$gte': threshold}})
    return render_template('online_users.html', online_users=list(online_users))

@app.route('/user/<username>/activity')
@login_required
def user_activity(username):
    activities = db['user_activity'].find({'username': username}).sort('timestamp', -1)
    return render_template('user_activity.html', username=username, activities=list(activities))

@app.route('/all-users-activity')
@login_required
def all_users_activity():
    activities = db['user_activity'].find({}).sort('timestamp', -1)
    return render_template('all_users_activity.html', activities=list(activities))

@app.route('/api/alerts')
def api_show_alerts():
    return show_alerts()

@app.route('/alerts')
def alerts():
    return show_alerts()

def highlight_keywords(text, keywords):
    pattern = re.compile(r'\b(' + '|'.join(re.escape(keyword) for keyword in keywords) + r')\b', re.IGNORECASE)
    highlighted_text = pattern.sub(lambda match: f"<span class='highlight'>{match.group(0)}</span>", text)
    return highlighted_text

def show_alerts():
    page = int(request.args.get('page', 1))
    per_page = 15
    skip = (page - 1) * per_page
    search_query = request.args.get('search', '')
    if search_query:
        query = {"$text": {"$search": search_query}}
    else:
        query = {}
    alerts = db['alerts'].find(query).skip(skip).limit(per_page)
    total_alerts = db['alerts'].count_documents(query)
    total_pages = (total_alerts + per_page - 1) // per_page
    sanitized_alerts = []
    config = load_config_from_db()
    keywords = config.get('keywords', [])
    for alert in alerts:
        alert['description'] = bleach.clean(highlight_keywords(alert.get('description', ''), keywords), tags=['span'], attributes={'span': ['class']}, strip=True)
        alert['title'] = bleach.clean(highlight_keywords(alert.get('title', ''), keywords), tags=['span'], attributes={'span': ['class']}, strip=True)
        sanitized_alerts.append(alert)
    return jsonify({
        'alerts': sanitized_alerts,
        'total_pages': total_pages,
        'current_page': page,
    })

@app.route('/add-site', methods=['POST'])
@login_required
def add_site():
    site_url = request.form.get('siteUrl')
    db['configurations'].update_one({"name": "default"}, {"$addToSet": {"sites": site_url}})
    return redirect(url_for('config_management'))

@app.route('/add-keyword', methods=['POST'])
@login_required
def add_keyword():
    keyword = request.form.get('keyword').lower()
    db['configurations'].update_one({"name": "default"}, {"$addToSet": {"keywords": keyword}})
    return redirect(url_for('config_management'))

@app.route('/delete-site/<int:index>', methods=['GET'])
@login_required
def delete_site(index):
    config = load_config_from_db()
    try:
        if 'sites' in config and 0 <= index < len(config['sites']):
            del config['sites'][index]
            db['configurations'].update_one({"name": "default"}, {"$set": {"sites": config['sites']}})
    except Exception as e:
        print(f"An error occurred: {e}")
    return redirect(url_for('config_management'))

@app.route('/delete-keyword/<int:index>', methods=['GET'])
@login_required
def delete_keyword(index):
    config = load_config_from_db()
    try:
        if 'keywords' in config and 0 <= index < len(config['keywords']):
            del config['keywords'][index]
            db['configurations'].update_one({"name": "default"}, {"$set": {"keywords": config['keywords']}})
    except Exception as e:
        print(f"An error occurred: {e}")
    return redirect(url_for('config_management'))

@app.route('/run-script')
def run_script():
    config = load_config_from_db()
    task = process_feeds_task.apply_async(args=[config['sites'], config['keywords']])
    return jsonify({"task_id": task.id}), 202

@celery.task(bind=True)
def process_feeds_task(self, feeds, keywords):
    for index, site in enumerate(feeds, start=1):
        response = requests.get(site)
        soup = BeautifulSoup(response.content, 'xml')
        items = soup.findAll('item')
        for item in items:
            process_item(item, site, keywords)
        self.update_state(state='PROGRESS', meta={'current': index, 'total': len(feeds)})
    return {'current': len(feeds), 'total': len(feeds), 'status': 'Task completed'}

def process_item(item, site, keywords):
    title = get_clean_text(item.find('title')) or 'No Title'
    description = get_clean_text(item.find('description')) or 'No Description'
    pub_date = find_pub_date(item)
    link = item.find('link').text if item.find('link') else 'No Link'
    media_urls = [enclosure['url'] for enclosure in item.find_all('enclosure') if 'url' in enclosure.attrs]
    content = f"{title} {description}".lower()
    words = content.split()
    if any(word.lower() in keywords for word in words):
        db['alerts'].update_one(
            {"link": link}, 
            {"$setOnInsert": {
                "site": site,
                "title": title,
                "description": description,
                "pub_date": pub_date,
                "link": link,
                "media_urls": media_urls,
                "last_checked": now_bulgarian()
            }},
            upsert=True
        )

def find_pub_date(item):
    for field in ['pubDate', 'dc:date']:
        date_str = item.find(field)
        if date_str:
            return dateutil.parser.parse(date_str.text)
    return None

def get_clean_text(element):
    if element and element.text:
        soup = BeautifulSoup(element.text, 'lxml')
        return ' '.join(soup.get_text().split())
    return ""

@app.route('/test-bcrypt')
def test_bcrypt():
    password = b"super secret password"
    hashed = bcrypt.hashpw(password, bcrypt.gensalt())
    return hashed

@app.route('/task-status/<task_id>')
@login_required
def task_status(task_id):
    task = process_feeds_task.AsyncResult(task_id)
    if task.state == 'PENDING':
        response = {'state': task.state, 'status': 'Pending...'}
    elif task.state != 'FAILURE':
        response = {
            'state': task.state,
            'progress': task.info.get('current', 0),
            'total': task.info.get('total', 1),
            'status': task.info.get('status', '')
        }
    else:
        response = {'state': task.state, 'status': str(task.info), 'error': 'Task failed'}
    return jsonify(response)

@app.route('/config-management')
@login_required
def config_management():
    config = load_config_from_db()
    return render_template('config_management.html', sites=config['sites'], keywords=config['keywords'])

@app.route('/workers')
@login_required
def show_workers():
    i = celery.control.inspect()
    workers = i.registered()
    if not workers:
        workers = "No workers found."
    return render_template('workers.html', workers=workers)

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password'].encode('utf-8')
        admin_user = db['admins'].find_one({'username': username})
        if admin_user and bcrypt.checkpw(password, admin_user['password']):
            session['admin'] = username
            return redirect(url_for('admin_dashboard'))
        else:
            flash('Invalid username or password')
    return render_template('admin_login.html')

@app.route('/admin/dashboard')
def admin_dashboard():
    if 'admin' not in session:
        return redirect(url_for('admin_login'))
    users = list(db['users'].find())
    return render_template('admin_dashboard.html', users=users)

@app.route('/admin/add_user', methods=['POST'])
def admin_add_user():
    if 'admin' not in session:
        return jsonify({'error': 'Unauthorized'}), 403
    username = request.form['username']
    first_name = request.form['first_name']
    last_name = request.form['last_name']
    email = request.form['email']
    password = generate_password_hash(request.form['password'])
    rank = request.form['rank']
    db['users'].insert_one({
        'username': username,
        'first_name': first_name,
        'last_name': last_name,
        'email': email,
        'password': password,
        'rank': rank
    })
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/delete_user', methods=['POST'])
@login_required
def admin_delete_user():
    if 'admin' not in session:
        flash('Unauthorized access.', 'danger')
        return jsonify({'error': 'Unauthorized'}), 403
    username = request.form.get('username')
    if not username:
        flash('Username is required for deletion.', 'warning')
        return redirect(url_for('admin_dashboard'))
    deletion_result = db['users'].delete_one({'username': username})
    if deletion_result.deleted_count == 0:
        flash('User not found or could not be deleted.', 'warning')
    else:
        flash(f'User {username} deleted successfully.', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/delete_all_alerts', methods=['POST'])
@login_required
def delete_all_alerts():
    if 'admin' not in session:
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('admin_dashboard'))
    try:
        db['alerts'].delete_many({})
        flash('All alerts have been successfully deleted.', 'success')
    except Exception as e:
        flash(f'An error occurred while trying to delete all alerts: {e}', 'danger')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/logout')
def admin_logout():
    session.pop('admin', None)
    return redirect(url_for('admin_login'))

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve(path):
    if path != "" and os.path.exists(os.path.join(app.root_path, 'mm3', 'build', path)):
        return send_from_directory(os.path.join(app.root_path, 'mm3', 'build'), path)
    else:
        return send_from_directory(os.path.join(app.root_path, 'mm3', 'build'), 'index.html')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
