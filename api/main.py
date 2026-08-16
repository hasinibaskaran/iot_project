import os
import logging
import traceback
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from api.routers.trip import router as trip_router
from api.routers.alert import router as alert_router

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("smart_sanitation_backend")

# Filter out uvicorn access logs for favicon.ico requests
class FaviconFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        return "/favicon.ico" not in record.getMessage()

logging.getLogger("uvicorn.access").addFilter(FaviconFilter())

app = FastAPI(
    title="Smart Train Sanitation System API",
    description="Backend API for managing IoT-driven coach sanitation alerts, scheduling, and staff routing.",
    version="1.0.0",
)

@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    logger.warning(f"HTTP exception: status_code={exc.status_code} detail={exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "detail": exc.detail
        }
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    logger.warning(f"Validation error for path {request.url.path}: {exc.errors()}")
    return JSONResponse(
        status_code=422,
        content={
            "success": False,
            "detail": exc.errors(),
            "message": "Validation error"
        }
    )

@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    tb = traceback.format_exc()
    logger.error(f"Unhandled exception occurred: {str(exc)}\n{tb}")
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "detail": "Internal Server Error"
        }
    )

# Register endpoints routers
app.include_router(trip_router)
app.include_router(alert_router)

@app.get("/", response_class=HTMLResponse)
def read_root():
    # Detect configuration statuses
    supabase_configured = "Configured" if os.environ.get("SUPABASE_URL") and os.environ.get("SUPABASE_KEY") else "Missing"
    api_key_configured = "Configured" if os.environ.get("API_SECRET_KEY") else "Missing"
    twilio_configured = os.environ.get("TWILIO_ACCOUNT_SID") and os.environ.get("TWILIO_AUTH_TOKEN") and os.environ.get("TWILIO_FROM_NUMBER")
    sms_mode = "Production (Twilio)" if twilio_configured else "Mock Sandbox Mode"
    
    return f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Smart Train Sanitation Control Panel</title>
        <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&family=Fira+Code:wght@400;500&display=swap" rel="stylesheet">
        <script src="https://cdn.jsdelivr.net/npm/mermaid/dist/mermaid.min.js"></script>
        <script>
            mermaid.initialize({{ startOnLoad: true, theme: 'dark' }});
        </script>
        <style>
            :root {{
                --bg-color: #080B11;
                --panel-bg: rgba(22, 30, 47, 0.7);
                --border-color: rgba(255, 255, 255, 0.08);
                --text-primary: #F3F4F6;
                --text-secondary: #9CA3AF;
                --accent-blue: #00F2FE;
                --accent-green: #05FFC5;
                --accent-purple: #8B5CF6;
                --status-ok: #10B981;
                --status-warn: #F59E0B;
                --status-err: #EF4444;
            }}

            * {{
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }}

            body {{
                font-family: 'Outfit', -apple-system, sans-serif;
                background-color: var(--bg-color);
                color: var(--text-primary);
                line-height: 1.6;
                background-image: radial-gradient(circle at 10% 20%, rgba(139, 92, 246, 0.05) 0%, transparent 40%),
                                  radial-gradient(circle at 90% 80%, rgba(0, 242, 254, 0.05) 0%, transparent 40%);
                background-attachment: fixed;
                min-height: 100vh;
                padding-bottom: 4rem;
            }}

            header {{
                border-bottom: 1px solid var(--border-color);
                backdrop-filter: blur(12px);
                background-color: rgba(8, 11, 17, 0.8);
                position: sticky;
                top: 0;
                z-index: 100;
            }}

            .nav-container {{
                max-width: 1300px;
                margin: 0 auto;
                display: flex;
                align-items: center;
                justify-content: space-between;
                padding: 1.25rem 2rem;
            }}

            .logo-group {{
                display: flex;
                align-items: center;
                gap: 0.75rem;
            }}

            .logo-dot {{
                width: 12px;
                height: 12px;
                background: linear-gradient(135deg, var(--accent-blue), var(--accent-green));
                border-radius: 50%;
                box-shadow: 0 0 12px var(--accent-blue);
                animation: pulse 2s infinite;
            }}

            .logo-text {{
                font-size: 1.35rem;
                font-weight: 700;
                letter-spacing: -0.5px;
                background: linear-gradient(to right, #FFFFFF, var(--text-secondary));
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
            }}

            .nav-links {{
                display: flex;
                gap: 1.5rem;
            }}

            .nav-links a {{
                color: var(--text-secondary);
                text-decoration: none;
                font-size: 0.9rem;
                font-weight: 500;
                transition: color 0.2s;
                border: 1px solid transparent;
                padding: 0.5rem 1rem;
                border-radius: 8px;
            }}

            .nav-links a:hover {{
                color: var(--text-primary);
                background-color: rgba(255, 255, 255, 0.03);
                border-color: var(--border-color);
            }}

            main {{
                max-width: 1300px;
                margin: 2.5rem auto 0 auto;
                padding: 0 2rem;
            }}

            .hero {{
                text-align: center;
                margin-bottom: 3rem;
            }}

            .hero h1 {{
                font-size: 2.75rem;
                font-weight: 700;
                margin-bottom: 0.75rem;
                background: linear-gradient(135deg, #FFFFFF 30%, var(--accent-blue) 100%);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
            }}

            .hero p {{
                color: var(--text-secondary);
                font-size: 1.1rem;
                max-width: 650px;
                margin: 0 auto;
            }}

            /* System Status Grid */
            .status-grid {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
                gap: 1.5rem;
                margin-bottom: 3rem;
            }}

            .status-card {{
                background: var(--panel-bg);
                border: 1px solid var(--border-color);
                border-radius: 12px;
                padding: 1.5rem;
                display: flex;
                flex-direction: column;
                gap: 0.5rem;
                position: relative;
                overflow: hidden;
            }}

            .status-card::before {{
                content: '';
                position: absolute;
                top: 0;
                left: 0;
                width: 4px;
                height: 100%;
                background: var(--accent-purple);
            }}

            .status-card.ok::before {{
                background: var(--status-ok);
            }}
            .status-card.warn::before {{
                background: var(--status-warn);
            }}

            .status-label {{
                font-size: 0.8rem;
                text-transform: uppercase;
                letter-spacing: 1px;
                color: var(--text-secondary);
            }}

            .status-value {{
                font-size: 1.25rem;
                font-weight: 600;
                color: var(--text-primary);
                display: flex;
                align-items: center;
                gap: 0.5rem;
            }}

            .status-indicator {{
                width: 8px;
                height: 8px;
                border-radius: 50%;
            }}

            .status-indicator.green {{ background-color: var(--status-ok); box-shadow: 0 0 8px var(--status-ok); }}
            .status-indicator.orange {{ background-color: var(--status-warn); box-shadow: 0 0 8px var(--status-warn); }}
            .status-indicator.red {{ background-color: var(--status-err); box-shadow: 0 0 8px var(--status-err); }}

            /* Split Layout for Testing */
            .work-area {{
                display: grid;
                grid-template-columns: 1.2fr 1fr;
                gap: 2rem;
                margin-bottom: 3rem;
            }}

            @media (max-width: 1024px) {{
                .work-area {{
                    grid-template-columns: 1fr;
                }}
            }}

            .interactive-panel {{
                background: var(--panel-bg);
                border: 1px solid var(--border-color);
                border-radius: 16px;
                padding: 2rem;
                backdrop-filter: blur(16px);
            }}

            .panel-title {{
                font-size: 1.35rem;
                font-weight: 600;
                margin-bottom: 1.5rem;
                display: flex;
                align-items: center;
                gap: 0.5rem;
                border-bottom: 1px solid var(--border-color);
                padding-bottom: 0.75rem;
            }}

            .tab-buttons {{
                display: flex;
                gap: 0.5rem;
                margin-bottom: 1.5rem;
                background: rgba(0, 0, 0, 0.2);
                padding: 0.35rem;
                border-radius: 10px;
                border: 1px solid var(--border-color);
            }}

            .tab-btn {{
                flex: 1;
                background: transparent;
                border: none;
                color: var(--text-secondary);
                padding: 0.6rem;
                font-family: inherit;
                font-size: 0.9rem;
                font-weight: 500;
                cursor: pointer;
                border-radius: 8px;
                transition: all 0.2s;
            }}

            .tab-btn.active {{
                background: rgba(255, 255, 255, 0.08);
                color: var(--text-primary);
                box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
            }}

            .input-group {{
                margin-bottom: 1.25rem;
            }}

            .input-group label {{
                display: block;
                font-size: 0.85rem;
                font-weight: 500;
                margin-bottom: 0.5rem;
                color: var(--text-secondary);
            }}

            .input-group input, .input-group select {{
                width: 100%;
                background: rgba(0, 0, 0, 0.2);
                border: 1px solid var(--border-color);
                border-radius: 8px;
                padding: 0.75rem 1rem;
                color: var(--text-primary);
                font-family: inherit;
                font-size: 0.95rem;
                transition: border-color 0.2s, box-shadow 0.2s;
            }}

            .input-group input:focus, .input-group select:focus {{
                outline: none;
                border-color: var(--accent-blue);
                box-shadow: 0 0 0 2px rgba(0, 242, 254, 0.15);
            }}

            .btn-submit {{
                width: 100%;
                background: linear-gradient(135deg, var(--accent-blue), var(--accent-purple));
                color: #000;
                font-weight: 600;
                font-size: 1rem;
                border: none;
                border-radius: 8px;
                padding: 0.85rem;
                cursor: pointer;
                transition: opacity 0.2s, transform 0.1s;
                font-family: inherit;
            }}

            .btn-submit:hover {{
                opacity: 0.95;
                box-shadow: 0 0 16px rgba(0, 242, 254, 0.3);
            }}

            .btn-submit:active {{
                transform: scale(0.98);
            }}

            /* Terminal View */
            .terminal-panel {{
                background: #04060A;
                border: 1px solid var(--border-color);
                border-radius: 16px;
                padding: 1.5rem;
                display: flex;
                flex-direction: column;
                height: 100%;
                min-height: 480px;
            }}

            .terminal-header {{
                display: flex;
                align-items: center;
                justify-content: space-between;
                margin-bottom: 1rem;
                border-bottom: 1px solid rgba(255, 255, 255, 0.05);
                padding-bottom: 0.5rem;
            }}

            .terminal-dots {{
                display: flex;
                gap: 6px;
            }}

            .terminal-dot {{
                width: 10px;
                height: 10px;
                border-radius: 50%;
            }}
            .terminal-dot.red {{ background-color: var(--status-err); }}
            .terminal-dot.yellow {{ background-color: var(--status-warn); }}
            .terminal-dot.green {{ background-color: var(--status-ok); }}

            .terminal-title {{
                font-family: 'Fira Code', monospace;
                font-size: 0.8rem;
                color: var(--text-secondary);
            }}

            .terminal-body {{
                flex: 1;
                font-family: 'Fira Code', monospace;
                font-size: 0.85rem;
                overflow-y: auto;
                color: #10B981;
                white-space: pre-wrap;
                word-break: break-all;
                padding: 0.5rem;
                background: rgba(0, 0, 0, 0.3);
                border-radius: 8px;
                border: 1px solid rgba(255, 255, 255, 0.03);
            }}

            .prompt {{
                color: var(--accent-blue);
            }}

            .response-key {{
                color: #A78BFA;
            }}
            
            .response-str {{
                color: #FCD34D;
            }}

            /* Database Schema section */
            .schema-section {{
                background: var(--panel-bg);
                border: 1px solid var(--border-color);
                border-radius: 16px;
                padding: 2rem;
                margin-bottom: 2rem;
            }}

            @keyframes pulse {{
                0% {{ transform: scale(1); opacity: 1; }}
                50% {{ transform: scale(1.15); opacity: 0.8; }}
                100% {{ transform: scale(1); opacity: 1; }}
            }}
        </style>
    </head>
    <body>
        <header>
            <div class="nav-container">
                <div class="logo-group">
                    <div class="logo-dot"></div>
                    <div class="logo-text">CleanTrack IoT Portal</div>
                </div>
                <div class="nav-links">
                    <a href="/docs" target="_blank">Swagger Docs</a>
                    <a href="https://github.com/vercel/examples/tree/main/python/fastapi" target="_blank">Vercel Template</a>
                </div>
            </div>
        </header>

        <main>
            <div class="hero">
                <h1>Smart Sanitation Control & Routing Gateway</h1>
                <p>Event-driven IoT backend verifying sanitation alert workflows, querying Supabase personnel, and routing messages to active OBHS staff or station fallbacks.</p>
            </div>

            <!-- Status Grid -->
            <div class="status-grid">
                <div class="status-card ok">
                    <div class="status-label">API Server Status</div>
                    <div class="status-value">
                        <div class="status-indicator green"></div>
                        Online / Active
                    </div>
                </div>
                <div class="status-card {"ok" if supabase_configured == "Configured" else "warn"}">
                    <div class="status-label">Supabase DB Link</div>
                    <div class="status-value">
                        <div class="status-indicator {"green" if supabase_configured == "Configured" else "orange"}"></div>
                        {supabase_configured}
                    </div>
                </div>
                <div class="status-card {"ok" if api_key_configured == "Configured" else "warn"}">
                    <div class="status-label">Header Key Verification</div>
                    <div class="status-value">
                        <div class="status-indicator {"green" if api_key_configured == "Configured" else "orange"}"></div>
                        {api_key_configured}
                    </div>
                </div>
                <div class="status-card ok">
                    <div class="status-label">SMS Gateway Mode</div>
                    <div class="status-value">
                        <div class="status-indicator green"></div>
                        {sms_mode}
                    </div>
                </div>
            </div>

            <!-- Interactive Split Panel -->
            <div class="work-area">
                <div class="interactive-panel">
                    <div class="panel-title">REST API Testing Bench</div>
                    
                    <div class="tab-buttons">
                        <button class="tab-btn active" id="btn-tab-init" onclick="switchTab('init')">Initialize Trip (GET)</button>
                        <button class="tab-btn" id="btn-tab-alert" onclick="switchTab('alert')">Dispatch Alert (POST)</button>
                    </div>

                    <!-- Global Configs -->
                    <div class="input-group">
                        <label for="input-api-key">API Auth Key (x-api-key)</label>
                        <input type="password" id="input-api-key" placeholder="Enter API_SECRET_KEY..." value="secret-test-key-2026">
                    </div>

                    <!-- Init Trip Fields -->
                    <div id="panel-init">
                        <div class="input-group">
                            <label for="init-train-num">Train Number</label>
                            <input type="text" id="init-train-num" value="12601">
                        </div>
                        <button class="btn-submit" onclick="runInitTrip()">Send Init Query</button>
                    </div>

                    <!-- Alert Dispatch Fields -->
                    <div id="panel-alert" style="display: none;">
                        <div class="input-group">
                            <label for="alert-train-num">Train Number</label>
                            <input type="text" id="alert-train-num" value="12601">
                        </div>
                        <div class="input-group">
                            <label for="alert-trip-num">Trip Number</label>
                            <input type="text" id="alert-trip-num" value="TRP-2026-8849">
                        </div>
                        <div class="input-group">
                            <label for="alert-coach-num">Coach Number</label>
                            <input type="text" id="alert-coach-num" value="A1">
                        </div>
                        <div class="input-group">
                            <label for="alert-last-station">Last Station Passed ID</label>
                            <input type="text" id="alert-last-station" value="AJJ">
                        </div>
                        <div class="input-group">
                            <label for="alert-next-station">Upcoming Station ID</label>
                            <input type="text" id="alert-next-station" value="KPD">
                        </div>
                        <button class="btn-submit" onclick="runDispatchAlert()">Trigger Alert Flow</button>
                    </div>
                </div>

                <!-- Terminal -->
                <div class="terminal-panel">
                    <div class="terminal-header">
                        <div class="terminal-dots">
                            <div class="terminal-dot red"></div>
                            <div class="terminal-dot yellow"></div>
                            <div class="terminal-dot green"></div>
                        </div>
                        <div class="terminal-title">Response Console</div>
                    </div>
                    <div class="terminal-body" id="console-output">// Run queries on the left to see requests and database triggers in real-time...</div>
                </div>
            </div>

            <!-- Database Design Section -->
            <div class="schema-section">
                <div class="panel-title">Relational Entity Layout</div>
                <pre class="mermaid" style="background:transparent;border:none;margin:0;">
                    erDiagram
                        TRAIN {{
                            string train_number PK
                            string train_name
                        }}
                        TRIP {{
                            uuid id PK
                            string trip_number UNIQUE
                            string train_number FK
                            string direction
                            string status
                            datetime start_time
                        }}
                        TRAIN_ROUTE_STATION {{
                            uuid id PK
                            string train_number FK
                            string direction
                            int sequence_order
                            string station_id
                            string station_name
                            string manager_phone
                        }}
                        OBHS_STAFF {{
                            uuid id PK
                            string trip_number FK
                            string coach_number
                            string name
                            string phone_number
                            boolean is_active
                        }}
                        ALERT_LOG {{
                            uuid id PK
                            string device_id FK
                            string train_number
                            string trip_number
                            string coach_number
                            string last_station_id
                            string next_station_id
                            string dispatched_to_type
                            string recipient_phone
                            string sms_status
                            datetime created_at
                        }}
                        TRAIN ||--o{{ TRIP : schedules
                        TRAIN ||--o{{ TRAIN_ROUTE_STATION : "has route stops"
                        TRIP ||--o{{ OBHS_STAFF : "assigned to"
                        TRIP ||--o{{ ALERT_LOG : tracks
                </pre>
            </div>
        </main>

        <script>
            let currentTab = 'init';

            function switchTab(tab) {{
                currentTab = tab;
                document.getElementById('btn-tab-init').classList.toggle('active', tab === 'init');
                document.getElementById('btn-tab-alert').classList.toggle('active', tab === 'alert');
                
                document.getElementById('panel-init').style.display = tab === 'init' ? 'block' : 'none';
                document.getElementById('panel-alert').style.display = tab === 'alert' ? 'block' : 'none';
            }}

            async def_fetch(url, options = {{}}) {{
                const consoleOutput = document.getElementById('console-output');
                consoleOutput.innerText = `Calling: ${{options.method || 'GET'}} ${{url}}...\\n`;
                
                try {{
                    const response = await fetch(url, options);
                    const isJson = response.headers.get('content-type')?.includes('application/json');
                    const text = await response.text();
                    
                    let formatted = text;
                    if (isJson) {{
                        const json = JSON.parse(text);
                        formatted = JSON.stringify(json, null, 2);
                    }}
                    
                    consoleOutput.innerHTML = `<span class="prompt">Status: ${{response.status}} ${{response.statusText}}</span>\\n\\n` + 
                        formatted
                            .replace(/"([^"]+)":/g, '<span class="response-key">"$1"</span>:')
                            .replace(/: "([^"]+)"/g, ': <span class="response-str">"$1"</span>');
                }} catch (err) {{
                    consoleOutput.innerText = `Error contacting API: ${{err.message}}\\n`;
                }}
            }}

            function runInitTrip() {{
                const apiKey = document.getElementById('input-api-key').value;
                const trainNum = document.getElementById('init-train-num').value;
                
                const url = `/api/init-trip?train_number=${{encodeURIComponent(trainNum)}}`;
                def_fetch(url, {{
                    method: 'GET',
                    headers: {{
                        'x-api-key': apiKey
                    }}
                }});
            }}

            function runDispatchAlert() {{
                const apiKey = document.getElementById('input-api-key').value;
                const body = {{
                    train_number: document.getElementById('alert-train-num').value,
                    trip_number: document.getElementById('alert-trip-num').value,
                    coach_number: document.getElementById('alert-coach-num').value,
                    last_station_id: document.getElementById('alert-last-station').value,
                    next_station_id: document.getElementById('alert-next-station').value,
                    time: new Date().toISOString().replace('T', ' ').substring(0, 19)
                }};
                
                def_fetch('/api/alert', {{
                    method: 'POST',
                    headers: {{
                        'x-api-key': apiKey,
                        'Content-Type': 'application/json'
                    }},
                    body: JSON.stringify(body)
                }});
            }}
        </script>
    </body>
    </html>
    """

def run_server():
    import uvicorn
    logger.info("Starting local development server on http://localhost:8000")
    uvicorn.run("api.main:app", host="0.0.0.0", port=8000, reload=True)
