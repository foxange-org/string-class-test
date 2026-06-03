import sys
from pathlib import Path

# 将项目根目录添加到 sys.path，以便导入 server 模块
sys.path.append(str(Path(__file__).parent.parent))

from server import app

# Vercel 需要暴露一个名为 'app' 的 WSGI 可调用对象
# 如果你的 server.py 中 app 就是 Flask 实例，直接使用