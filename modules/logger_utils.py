import streamlit as st
import datetime
import traceback
import os
import sys

# Try to import httpx for monkeypatching if available
try:
    import httpx._models as httpx_models
    _original_normalize = httpx_models._normalize_header_value

    def _debug_normalize_header_value(value, encoding=None):
        try:
            if isinstance(value, bytes):
                return value
            return value.encode(encoding or "ascii")
        except UnicodeEncodeError as e:
            # Capture the offending value and log it before re-raising
            error_msg = f"CRITICAL HEADER ENCODING ERROR: Failed to encode header value to ASCII.\nValue (first 100 chars): {str(value)[:100]}...\nLength: {len(str(value))}\nError: {e}"
            # We use print here because we might not have st.session_state yet or it might be in a different thread
            print(error_msg, file=sys.stderr)
            # Try to log to session state if possible
            try:
                import streamlit as st
                if 'app_logs' in st.session_state:
                    st.session_state.app_logs.append({
                        "timestamp": datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3],
                        "level": "ERROR",
                        "message": error_msg
                    })
            except:
                pass
            raise e

    httpx_models._normalize_header_value = _debug_normalize_header_value
except Exception as e:
    # If httpx is not installed yet or path is different, ignore
    pass

# -- UTF-8 ENFORCEMENT for logging --------------------------------------------
# Ensures that even if the system defaults to ASCII, we try to handle logs as UTF-8
os.environ['PYTHONIOENCODING'] = 'utf-8'

def init_logger():
    """Initializes the log storage in streamlit session state."""
    if 'app_logs' not in st.session_state:
        st.session_state.app_logs = []

def _add_log(level, message):
    """Internal helper to add a log entry with timestamp."""
    timestamp = datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]
    # Ensure message is string and handle potential encoding issues
    try:
        if isinstance(message, bytes):
            message = message.decode('utf-8', errors='replace')
        else:
            message = str(message)
    except Exception:
        message = "[Encoding Error in log message]"
        
    log_entry = {
        "timestamp": timestamp,
        "level": level,
        "message": message
    }
    st.session_state.app_logs.append(log_entry)
    # Keep only last 200 logs to prevent memory bloat
    if len(st.session_state.app_logs) > 200:
        st.session_state.app_logs.pop(0)

def info(msg):
    _add_log("INFO", msg)

def warn(msg):
    _add_log("WARN", msg)

def error(msg, exc_info=False):
    if exc_info:
        msg = f"{msg}\n{traceback.format_exc()}"
    _add_log("ERROR", msg)

def debug(msg):
    _add_log("DEBUG", msg)

def display_logs():
    """Renders the logs in a scrollable, themed container."""
    st.divider()
    with st.expander("🛠️ SYSTEM LOGS & DEBUGGER", expanded=False):
        if not st.session_state.get('app_logs'):
            st.info("No logs generated yet. Start an analysis to see activity.")
            return

        # Simple filter
        log_levels = ["INFO", "WARN", "ERROR", "DEBUG"]
        selected_levels = st.multiselect("Filter levels", log_levels, default=["INFO", "WARN", "ERROR"])
        
        # Reverse logs to see newest first
        filtered_logs = [l for l in reversed(st.session_state.app_logs) if l['level'] in selected_levels]
        
        log_html = "<div style='background-color:#1e1e1e; color:#d4d4d4; padding:10px; border-radius:5px; font-family:monospace; font-size:12px; height:400px; overflow-y:auto;'>"
        for log in filtered_logs:
            color = "#569cd6" # Blue for info
            if log['level'] == "WARN": color = "#ce9178" # Orange
            if log['level'] == "ERROR": color = "#f44747" # Red
            if log['level'] == "DEBUG": color = "#b5cea8" # Greenish
            
            # Escape HTML characters manually for the log view
            safe_msg = log['message'].replace("<", "&lt;").replace(">", "&gt;").replace("\n", "<br>")
            
            log_html += f"<div><span style='color:#808080'>[{log['timestamp']}]</span> <span style='color:{color}; font-weight:bold;'>{log['level']}</span>: {safe_msg}</div>"
        
        log_html += "</div>"
        st.markdown(log_html, unsafe_allow_html=True)
        
        if st.button("Clear Logs"):
            st.session_state.app_logs = []
            st.rerun()
