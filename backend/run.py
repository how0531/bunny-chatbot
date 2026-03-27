import sys
import os
from pathlib import Path

# Add the project root to sys.path so 'backend' package is resolvable
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.append(str(project_root))

from backend.app.api.routes import app

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print(f"🐰 Starting Bunny Chatbot from {project_root}...")
    app.run(host='0.0.0.0', port=port, debug=False)
