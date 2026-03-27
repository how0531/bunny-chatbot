from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from backend.app.services.stock_service import StockService
from backend.app.core.config import Config
from backend.app.core.logger import setup_logger

app = Flask(__name__)
CORS(app)

# Setup logger
logger = setup_logger(__name__, log_file=Config.LOG_FILE, level=Config.get_log_level())

try:
    service = StockService()
    logger.info("Flask application initialized successfully")
except Exception as e:
    logger.critical(f"StockService init failed: {e}. App starting in degraded mode.")
    service = None


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/chat', methods=['POST'])
def chat():
    """
    Single chat endpoint.
    All intent routing is now delegated to Sophia Orchestrator.
    """
    try:
        data = request.json
        message = data.get('message', '').strip()
        user_ip = request.remote_addr

        # Rate Limiting
        from backend.app.core.utils import limiter
        allowed, remaining = limiter.is_allowed(user_ip)
        if not allowed:
            return jsonify({
                'response': "⚠️ **Sophia 的安全警告**：您的請求過於頻繁，請稍候 60 秒再進行下一輪分析。"
            })

        if not service:
            return jsonify({'response': '服務初始化失敗，請確認資料庫連線設定。'}), 503

        if not message:
            return jsonify({'response': '請輸入股票代號'})

        # ── Delegate everything to Sophia ──
        from backend.app.agents.sophia_orchestrator import get_orchestrator
        sophia = get_orchestrator(service)
        result = sophia.route_intent(message)

        return jsonify(result)

    except Exception as e:
        logger.error(f"Error processing request: {e}", exc_info=True)
        return jsonify({'response': f"系統發生錯誤: {str(e)}"}), 500


if __name__ == '__main__':
    app.run(debug=True, port=5000, threaded=True)
