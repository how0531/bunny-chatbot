# AI Stock Assistant (AI 股市助理)

A Flask-based web application that provides real-time stock analysis, hotword tracking, and market sentiment using Google Gemini AI and MongoDB.

## ✨ Key Features

- **Real-time AI Analysis**: Generates summaries of stock price movements and rising reasons
- **Visual Sentiment**: 🔴🟢⚪ indicators for quick sentiment assessment
- **Data Integrity**: Automatically falls back to Yahoo Finance (yfinance) for P/E and Yield when MongoDB data is missing
- **Batch Query**: Support for multiple stocks (e.g., `2330,2317`)
- **Concept Search**: Search for stocks by keywords (e.g., `AI`, `5G`)
- **Historical Comparison**: View past rising reasons with `[Stock ID] 歷史`
- **Smart Caching**: Multi-layer cache for optimal performance
- **Production-Ready**: Structured logging, configuration management, error handling

## 📁 Project Structure

```
mongo_project/
├── app.py                  # Main Flask application (Sophia's Controller)
├── agents_orchestrator.py  # AI Team Orchestration logic
├── finrobot_agents.py      # Specialized FinRobot CoT agents
├── stock_service.py        # Core financial business logic (Arthur's Engine)
├── metabase_service.py     # ClickHouse & Metabase data access
├── report_formatter.py     # Research report generation
├── sector_analyzer.py      # Sector & Concept analysis
├── config.py               # Configuration management
├── constants.py            # Global constants
├── finrobot_lib/           # Optimized FinRobot local library
├── static/                 # CSS (Glassmorphism) & JS (Recharts)
├── templates/              # HTML templates
└── scripts/                # Maintenance scripts
```

## 👑 AI Team (Personas)

This project is an **All-Star Ensemble** managed by specialized agents:

- **@Sophia (Strategic PM)**: Controls `app.py`, parses user intent, and arbitrates decisions.
- **@Arthur (Senior Advisor)**: Powers `stock_service.py`, handles Top-Down research and valuation.
- **@Leo (Architect)**: Manages `static/` and `templates/`, implements the Glassmorphism UI.
- **@Oscar (Quant/Compliance)**: handles `metabase_service.py`, sentiment analysis, and risk control.
- **@Kevin (QA/Diagnostic)**: Ensures data integrity and handles stress testing.
- **@Diana (AI Strategy)**: Optimizes prompts and interaction flows.
- **@Max (Infrastructure)**: Manages MongoDB connections and security.

## 🚀 Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Environment

Copy `.env.example` to `.env` and update with your actual values:

```bash
cp .env.example .env
```

Edit `.env`:

```
GEMINI_API_KEY=your_actual_api_key_here
MONGODB_URI=your_mongodb_connection_string
```

### 3. Run the Application

```bash
python app.py
```

The application will be available at [http://localhost:5000](http://localhost:5000)

## ⚙️ Configuration

All configuration is managed through environment variables in `.env`:

- **MongoDB**: `MONGODB_URI`, `MONGODB_TIMEOUT`, `MONGODB_MAX_POOL_SIZE`
- **Gemini API**: `GEMINI_API_KEY`, `GEMINI_MODEL`
- **Flask**: `FLASK_ENV`, `FLASK_DEBUG`, `FLASK_PORT`
- **Cache**: `CACHE_NAME_TTL`, `CACHE_ANALYSIS_TTL`, etc.
- **Logging**: `LOG_LEVEL`, `LOG_FILE`

## 📊 Usage Examples

**Single Stock Query:**

```
2330
```

**Batch Query:**

```
2330,2317,2454
```

**Historical Analysis:**

```
2330 歷史
```

**Detailed Mode:**

```
2330 詳細
```

**Concept Search:**

```
AI
```

**Fuzzy Name Search:**

```
台積電
```

## 🏗️ Architecture

### Backend (Flask + Python)

- **Multi-datasource**: MongoDB (News, Hotwords, Twstock) + Yahoo Finance
- **Caching Layer**: TTLCache with configurable expiration
- **AI Integration**: Google Gemini 2.0 Flash
- **Logging**: Structured logging with file rotation

### Frontend (Vanilla JS)

- **Responsive UI**: Mobile and desktop support
- **Dynamic Interaction**: Quick action buttons, loading animations
- **Error Handling**: Timeout detection, retry mechanism
- **Modern Design**: Glassmorphism styling

## 📝 Logs

Application logs are stored in `logs/app.log` with automatic rotation (10MB per file, 5 backups).

Log format:

```
2026-01-22 14:12:45 - module_name - LEVEL - message
```

## 🛠️ Development

### Running Tests

Development and testing scripts are located in the `scripts/` directory. See `scripts/README.md` for details.

### Code Quality

- **Type Hints**: All functions include type annotations
- **Docstrings**: Google-style documentation
- **Constants**: Centralized in `constants.py`
- **Config**: Environment-based configuration

## 🔒 Security

- API keys and credentials are stored in `.env` (gitignored)
- MongoDB connection uses authentication
- No sensitive data in source code

## 📦 Dependencies

See `requirements.txt` for the full list. Key packages:

- `flask` - Web framework
- `pymongo` - MongoDB driver
- `google-generativeai` - Gemini AI
- `yfinance` - Yahoo Finance data
- `cachetools` - Caching utilities
- `python-dotenv` - Environment management

## 🎯 Recent Optimizations

- ✅ Configuration management with environment variables
- ✅ Structured logging with file rotation
- ✅ Constants management for better maintainability
- ✅ MongoDB connection pooling
- ✅ yfinance result caching
- ✅ Frontend timeout handling
- ✅ Retry mechanism for failed requests
- ✅ Type hints and comprehensive documentation

## 📄 License

This is a private project for stock analysis purposes.

## 🤝 Contributing

This is a private project. For questions or issues, please contact the project maintainer.
