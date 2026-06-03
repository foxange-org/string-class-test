import os
import json
import hashlib
import datetime
from functools import wraps
from flask import Flask, request, jsonify, session, send_from_directory
from flask_session import Session
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__, static_folder='public', static_url_path='')
app.secret_key = 'string-jiao-secret-key-2026'
app.config['SESSION_TYPE'] = 'filesystem'
app.config['SESSION_PERMANENT'] = False
app.config['SESSION_USE_SIGNER'] = True
Session(app)

DATA_DIR = 'data'
USERS_FILE = os.path.join(DATA_DIR, 'users.json')
TASKS_FILE = os.path.join(DATA_DIR, 'tasks.json')
EXCHANGE_FILE = os.path.join(DATA_DIR, 'exchangeRequests.json')

# ---------- 初始化数据目录和默认数据 ----------
def init_data():
    os.makedirs(DATA_DIR, exist_ok=True)
    if not os.path.exists(USERS_FILE):
        default_admin = {
            "id": 1,
            "username": "admin",
            "password": generate_password_hash("admin123"),
            "role": "admin",
            "tag": "超级管理员",
            "coins": 9999,
            "tasks": [],
            "personalMd": "# 管理员主页\n欢迎参观",
            "totalTasksCompleted": 0,
            "totalTasksAccepted": 0
        }
        with open(USERS_FILE, 'w', encoding='utf-8') as f:
            json.dump([default_admin], f, indent=2, ensure_ascii=False)
    if not os.path.exists(TASKS_FILE):
        default_tasks = [
            {"id": "task1", "title": "完成一篇孙教宣传文章", "reward": 10, "maxParticipants": 5, "currentParticipants": 0, "deadline": "2025-12-31", "active": True},
            {"id": "task2", "title": "招募一名新信徒", "reward": 20, "maxParticipants": 3, "currentParticipants": 0, "deadline": "2025-12-31", "active": True},
            {"id": "task3", "title": "找出反孙教间谍", "reward": 50, "maxParticipants": 2, "currentParticipants": 0, "deadline": "2025-12-31", "active": True}
        ]
        with open(TASKS_FILE, 'w', encoding='utf-8') as f:
            json.dump(default_tasks, f, indent=2, ensure_ascii=False)
    if not os.path.exists(EXCHANGE_FILE):
        with open(EXCHANGE_FILE, 'w', encoding='utf-8') as f:
            json.dump([], f)

init_data()

def read_json(file):
    with open(file, 'r', encoding='utf-8') as f:
        return json.load(f)

def write_json(file, data):
    with open(file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'error': '未登录'}), 401
        return f(*args, **kwargs)
    return decorated

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session or session.get('role') != 'admin':
            return jsonify({'error': '权限不足'}), 403
        return f(*args, **kwargs)
    return decorated

# ---------- 静态文件 ----------
@app.route('/')
def index():
    return send_from_directory('public', 'index.html')

@app.route('/<path:filename>')
def static_files(filename):
    return send_from_directory('public', filename)

# ---------- API ----------
@app.route('/api/register', methods=['POST'])
def register():
    data = request.json
    username = data.get('username', '').strip()
    password = data.get('password', '')
    if not username or not password:
        return jsonify({'error': '用户名/密码不能为空'}), 400
    users = read_json(USERS_FILE)
    if any(u['username'] == username for u in users):
        return jsonify({'error': '用户名已存在'}), 400
    hashed = generate_password_hash(password)
    new_user = {
        'id': int(datetime.datetime.now().timestamp() * 1000),
        'username': username,
        'password': hashed,
        'role': 'user',
        'tag': '',
        'coins': 0,
        'tasks': [],
        'personalMd': '# 我的个人主页\n欢迎来到我的主页！',
        'totalTasksCompleted': 0,
        'totalTasksAccepted': 0
    }
    users.append(new_user)
    write_json(USERS_FILE, users)
    session['user_id'] = new_user['id']
    session['username'] = new_user['username']
    session['role'] = new_user['role']
    return jsonify({'success': True, 'role': new_user['role']})

@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    username = data.get('username', '').strip()
    password = data.get('password', '')
    users = read_json(USERS_FILE)
    user = next((u for u in users if u['username'] == username), None)
    if not user or not check_password_hash(user['password'], password):
        return jsonify({'error': '用户名或密码错误'}), 401
    session['user_id'] = user['id']
    session['username'] = user['username']
    session['role'] = user['role']
    return jsonify({'success': True, 'role': user['role']})

@app.route('/api/me', methods=['GET'])
@login_required
def me():
    users = read_json(USERS_FILE)
    user = next((u for u in users if u['id'] == session['user_id']), None)
    if not user:
        return jsonify({'error': '用户不存在'}), 401
    return jsonify({
        'id': user['id'],
        'username': user['username'],
        'role': user['role'],
        'tag': user.get('tag', ''),
        'coins': user.get('coins', 0),
        'tasks': user.get('tasks', []),
        'personalMd': user.get('personalMd', ''),
        'totalTasksCompleted': user.get('totalTasksCompleted', 0),
        'totalTasksAccepted': user.get('totalTasksAccepted', 0)
    })

@app.route('/api/update-personal-md', methods=['POST'])
@login_required
def update_personal_md():
    content = request.json.get('content', '')
    users = read_json(USERS_FILE)
    user = next((u for u in users if u['id'] == session['user_id']), None)
    if user:
        user['personalMd'] = content
        write_json(USERS_FILE, users)
        return jsonify({'success': True})
    return jsonify({'error': '用户不存在'}), 404

@app.route('/api/change-password', methods=['POST'])
@login_required
def change_password():
    data = request.json
    old = data.get('oldPassword', '')
    new = data.get('newPassword', '')
    users = read_json(USERS_FILE)
    user = next((u for u in users if u['id'] == session['user_id']), None)
    if not user or not check_password_hash(user['password'], old):
        return jsonify({'error': '原密码错误'}), 400
    user['password'] = generate_password_hash(new)
    write_json(USERS_FILE, users)
    return jsonify({'success': True})

@app.route('/api/change-username', methods=['POST'])
@login_required
def change_username():
    new_username = request.json.get('newUsername', '').strip()
    if not new_username:
        return jsonify({'error': '用户名不能为空'}), 400
    users = read_json(USERS_FILE)
    if any(u['username'] == new_username and u['id'] != session['user_id'] for u in users):
        return jsonify({'error': '用户名已存在'}), 400
    user = next((u for u in users if u['id'] == session['user_id']), None)
    if user:
        user['username'] = new_username
        write_json(USERS_FILE, users)
        session['username'] = new_username
        return jsonify({'success': True})
    return jsonify({'error': '用户不存在'}), 404

@app.route('/api/tasks', methods=['GET'])
def get_tasks():
    tasks = read_json(TASKS_FILE)
    return jsonify(tasks)

@app.route('/api/tasks/accept', methods=['POST'])
@login_required
def accept_task():
    task_id = request.json.get('taskId')
    tasks = read_json(TASKS_FILE)
    task = next((t for t in tasks if t['id'] == task_id), None)
    if not task:
        return jsonify({'error': '任务不存在'}), 404
    now = datetime.datetime.now()
    deadline = datetime.datetime.strptime(task['deadline'], '%Y-%m-%d')
    if deadline < now:
        return jsonify({'error': '任务已过期'}), 400
    if task['currentParticipants'] >= task['maxParticipants']:
        return jsonify({'error': '任务已满员'}), 400
    if not task['active']:
        return jsonify({'error': '任务已禁用'}), 400
    users = read_json(USERS_FILE)
    user = next((u for u in users if u['id'] == session['user_id']), None)
    if not user:
        return jsonify({'error': '用户不存在'}), 404
    if any(t['taskTitle'] == task['title'] and t.get('status') != 'completed' for t in user.get('tasks', [])):
        return jsonify({'error': '您已接取过该任务'}), 400
    task['currentParticipants'] += 1
    user.setdefault('tasks', []).append({
        'taskId': task['id'],
        'taskTitle': task['title'],
        'rewardValue': task['reward'],
        'acceptTime': datetime.datetime.now().isoformat(),
        'status': 'ongoing'
    })
    user['totalTasksAccepted'] = user.get('totalTasksAccepted', 0) + 1
    write_json(TASKS_FILE, tasks)
    write_json(USERS_FILE, users)
    return jsonify({'success': True})

@app.route('/api/tasks/complete', methods=['POST'])
@login_required
def complete_task():
    task_id = request.json.get('taskId')
    users = read_json(USERS_FILE)
    user = next((u for u in users if u['id'] == session['user_id']), None)
    if not user:
        return jsonify({'error': '用户不存在'}), 404
    task = next((t for t in user.get('tasks', []) if t['taskId'] == task_id), None)
    if not task or task.get('status') == 'completed':
        return jsonify({'error': '无效任务'}), 400
    task['status'] = 'completed'
    task['finishTime'] = datetime.datetime.now().isoformat()
    user['coins'] = user.get('coins', 0) + task['rewardValue']
    user['totalTasksCompleted'] = user.get('totalTasksCompleted', 0) + 1
    write_json(USERS_FILE, users)
    return jsonify({'success': True, 'reward': task['rewardValue']})

@app.route('/api/gift', methods=['POST'])
@login_required
def gift():
    data = request.json
    to_username = data.get('toUsername', '').strip()
    amount = int(data.get('amount', 0))
    if amount <= 0:
        return jsonify({'error': '无效数量'}), 400
    users = read_json(USERS_FILE)
    from_user = next((u for u in users if u['id'] == session['user_id']), None)
    to_user = next((u for u in users if u['username'] == to_username), None)
    if not to_user:
        return jsonify({'error': '用户不存在'}), 404
    if from_user.get('coins', 0) < amount:
        return jsonify({'error': '金币不足'}), 400
    from_user['coins'] = from_user.get('coins', 0) - amount
    to_user['coins'] = to_user.get('coins', 0) + amount
    write_json(USERS_FILE, users)
    return jsonify({'success': True})

@app.route('/api/exchange/request', methods=['POST'])
@login_required
def exchange_request():
    data = request.json
    account = data.get('account', '').strip()
    web_coins = int(data.get('webCoins', 0))
    if web_coins < 10 or web_coins % 10 != 0:
        return jsonify({'error': '数量必须为10的倍数且≥10'}), 400
    users = read_json(USERS_FILE)
    user = next((u for u in users if u['id'] == session['user_id']), None)
    if user.get('coins', 0) < web_coins:
        return jsonify({'error': '金币不足'}), 400
    user['coins'] -= web_coins
    write_json(USERS_FILE, users)
    requests = read_json(EXCHANGE_FILE)
    requests.append({
        'id': int(datetime.datetime.now().timestamp() * 1000),
        'username': user['username'],
        'account': account,
        'webCoins': web_coins,
        'campusCoins': web_coins // 10,
        'status': 'pending',
        'time': datetime.datetime.now().isoformat()
    })
    write_json(EXCHANGE_FILE, requests)
    return jsonify({'success': True})

# ---------- 管理员 API ----------
@app.route('/api/admin/users', methods=['GET'])
@admin_required
def admin_users():
    users = read_json(USERS_FILE)
    safe = [{'username': u['username'], 'tag': u.get('tag', ''), 'coins': u.get('coins', 0)} for u in users]
    return jsonify(safe)

@app.route('/api/admin/set-tag', methods=['POST'])
@admin_required
def set_tag():
    data = request.json
    target = data.get('targetUsername')
    new_tag = data.get('newTag', '')
    users = read_json(USERS_FILE)
    user = next((u for u in users if u['username'] == target), None)
    if user:
        user['tag'] = new_tag
        write_json(USERS_FILE, users)
        return jsonify({'success': True})
    return jsonify({'error': '用户不存在'}), 404

@app.route('/api/admin/adjust-coins', methods=['POST'])
@admin_required
def adjust_coins():
    data = request.json
    target = data.get('targetUsername')
    delta = int(data.get('delta', 0))
    users = read_json(USERS_FILE)
    user = next((u for u in users if u['username'] == target), None)
    if user:
        user['coins'] = user.get('coins', 0) + delta
        write_json(USERS_FILE, users)
        return jsonify({'success': True})
    return jsonify({'error': '用户不存在'}), 404

@app.route('/api/admin/tasks', methods=['GET'])
@admin_required
def admin_tasks():
    tasks = read_json(TASKS_FILE)
    return jsonify(tasks)

@app.route('/api/admin/update-task', methods=['POST'])
@admin_required
def update_task():
    data = request.json
    task_id = data.get('taskId')
    updates = data.get('updates', {})
    tasks = read_json(TASKS_FILE)
    task = next((t for t in tasks if t['id'] == task_id), None)
    if task:
        task.update(updates)
        write_json(TASKS_FILE, tasks)
        return jsonify({'success': True})
    return jsonify({'error': '任务不存在'}), 404

@app.route('/api/admin/add-task', methods=['POST'])
@admin_required
def add_task():
    tasks = read_json(TASKS_FILE)
    new_id = f"task{int(datetime.datetime.now().timestamp() * 1000)}"
    today = datetime.datetime.now().strftime('%Y-%m-%d')
    new_task = {
        'id': new_id,
        'title': '新任务',
        'reward': 10,
        'maxParticipants': 5,
        'currentParticipants': 0,
        'deadline': today,
        'active': True
    }
    tasks.append(new_task)
    write_json(TASKS_FILE, tasks)
    return jsonify({'success': True, 'task': new_task})

@app.route('/api/admin/delete-task', methods=['POST'])
@admin_required
def delete_task():
    task_id = request.json.get('taskId')
    tasks = read_json(TASKS_FILE)
    tasks = [t for t in tasks if t['id'] != task_id]
    write_json(TASKS_FILE, tasks)
    # 清理用户任务
    users = read_json(USERS_FILE)
    for u in users:
        u['tasks'] = [t for t in u.get('tasks', []) if t['taskId'] != task_id]
        u['totalTasksAccepted'] = len(u['tasks'])
        u['totalTasksCompleted'] = sum(1 for t in u['tasks'] if t.get('status') == 'completed')
    write_json(USERS_FILE, users)
    return jsonify({'success': True})

@app.route('/api/admin/exchange-requests', methods=['GET'])
@admin_required
def exchange_requests():
    reqs = read_json(EXCHANGE_FILE)
    return jsonify(reqs)

@app.route('/api/admin/approve-exchange', methods=['POST'])
@admin_required
def approve_exchange():
    req_id = request.json.get('requestId')
    reqs = read_json(EXCHANGE_FILE)
    req = next((r for r in reqs if r['id'] == req_id and r['status'] == 'pending'), None)
    if req:
        req['status'] = 'approved'
        write_json(EXCHANGE_FILE, reqs)
        return jsonify({'success': True})
    return jsonify({'error': '申请不存在'}), 404

@app.route('/api/admin/reject-exchange', methods=['POST'])
@admin_required
def reject_exchange():
    req_id = request.json.get('requestId')
    reqs = read_json(EXCHANGE_FILE)
    req = next((r for r in reqs if r['id'] == req_id and r['status'] == 'pending'), None)
    if req:
        # 退还金币
        users = read_json(USERS_FILE)
        user = next((u for u in users if u['username'] == req['username']), None)
        if user:
            user['coins'] = user.get('coins', 0) + req['webCoins']
            write_json(USERS_FILE, users)
        reqs = [r for r in reqs if r['id'] != req_id]
        write_json(EXCHANGE_FILE, reqs)
        return jsonify({'success': True})
    return jsonify({'error': '申请不存在'}), 404

@app.route('/api/rank', methods=['GET'])
def rank():
    users = read_json(USERS_FILE)
    rank_data = [{
        'username': u['username'],
        'tag': u.get('tag', '无'),
        'coins': u.get('coins', 0),
        'completed': u.get('totalTasksCompleted', 0),
        'accepted': u.get('totalTasksAccepted', 0)
    } for u in users]
    return jsonify(rank_data)

@app.route('/api/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({'success': True})

# 不需要 if __name__ 块，直接保留 app 对象即可
# 本地开发时可以保留，但部署到 Vercel 时不会执行
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))