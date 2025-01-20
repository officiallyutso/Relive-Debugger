from flask import Flask, request, jsonify, send_from_directory, current_app
from .debugger import WebDebugger
from .monitor import ResourceMonitor
from pygments import highlight
from pygments.lexers import PythonLexer
from pygments.formatters import HtmlFormatter
import threading
import time

app = Flask(__name__, static_folder='../frontend')
debugger_instance = None
resource_monitor = None

def update_resource_monitor():
    global resource_monitor
    while True:
        if resource_monitor:
            resource_monitor.update()
        time.sleep(1)


def run_code(code, debugger, start_line=None, end_line=None):
    try:
        debugger.setup_io()
        debugger.is_running = True
        
        if start_line is not None and end_line is not None:
            debugger.selected_range = (start_line, end_line)
            code_lines = code.split('\n')
            selected_code = '\n'.join(code_lines[start_line-1:end_line])
            debugger.selected_code = selected_code
            compiled_code = compile(selected_code, '<string>', 'exec')
        else:
            debugger.selected_range = None
            debugger.selected_code = None
            compiled_code = compile(code, '<string>', 'exec')
            
        debugger.run(compiled_code)
    except Exception as e:
        debugger.exception = str(e)
        print(f"Exception occurred: {str(e)}")
    finally:
        debugger.restore_io()
        debugger.is_running = False

@app.route("/")
def index():
    return send_from_directory(current_app.static_folder, 'index.html')

@app.route("/visualizations", methods=["GET"])
def get_visualizations():
    global debugger_instance
    if not debugger_instance:
        return jsonify({"error": "Debugger not running"}), 400
        
    try:
        data = debugger_instance.get_visualization_data()
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
@app.route("/profile", methods=["GET"])
def get_profile_data():
    global debugger_instance
    if not debugger_instance:
        return jsonify({"error": "Debugger not running"}), 400
        
    try:
        data = debugger_instance.get_profile_data()
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
@app.route("/resource_usage", methods=["GET"])
def get_resource_usage():
    global resource_monitor
    if not resource_monitor:
        return jsonify({"error": "Resource monitor not running"}), 400
    return jsonify(resource_monitor.get_usage())

@app.route("/evaluate", methods=["POST"])
def evaluate_code():
    global debugger_instance
    if not debugger_instance:
        return jsonify({"error": "Debugger not running"}), 400
        
    code = request.json.get("code")
    line_number = request.json.get("line_number")
    
    if not code:
        return jsonify({"error": "No code provided"}), 400
        
    result = debugger_instance.evaluate_code(code, line_number)
    return jsonify(result)

@app.route("/start", methods=["POST"])
def start_debugger():
    global debugger_instance, resource_monitor
    code = request.json.get("code")
    start_line = request.json.get("start_line")
    end_line = request.json.get("end_line")
    
    if not code:
        return jsonify({"error": "No code provided"}), 400

    highlighted_code = highlight(code, PythonLexer(), HtmlFormatter())
    
    if debugger_instance and debugger_instance.is_running:
        debugger_instance.set_quit()
        time.sleep(0.5)

    debugger_instance = WebDebugger()
    resource_monitor = ResourceMonitor()
    
    threading.Thread(
        target=run_code, 
        args=(code, debugger_instance, start_line, end_line), 
        daemon=True
    ).start()
    
    return jsonify({
        "message": "Debugger started",
        "highlighted_code": highlighted_code
    })

@app.route("/status", methods=["GET"])
def get_status():
    global debugger_instance
    if not debugger_instance:
        return jsonify({"error": "Debugger not running"}), 400
    
    status = {
        "is_running": debugger_instance.is_running,
        "stack_frames": debugger_instance.stack_frames,
        "variables": debugger_instance.variables,
        "breakpoints": debugger_instance.breakpoints.get('<string>', {}),
        "exception": debugger_instance.exception,
        "output": debugger_instance.output_buffer.getvalue(),
        "current_line": debugger_instance.current_line,
        "states": len(debugger_instance.program_states),
        "current_state": debugger_instance.current_state_index
    }
    return jsonify(status)

@app.route("/breakpoints", methods=["POST"])
def set_breakpoints():
    global debugger_instance
    if not debugger_instance:
        return jsonify({"error": "Debugger not running"}), 400
    
    breakpoints = request.json.get("breakpoints", [])
    debugger_instance.clear_all_breaks()
    
    for bp in breakpoints:
        line = bp.get('line') if isinstance(bp, dict) else bp
        condition = bp.get('condition') if isinstance(bp, dict) else None
        
        if condition:
            debugger_instance.set_conditional_break('<string>', line, condition)
        else:
            debugger_instance.set_break('<string>', line)
    
    return jsonify({"message": "Breakpoints set"})

# Add a new route to get breakpoint information
@app.route("/breakpoints", methods=["GET"])
def get_breakpoints():
    global debugger_instance
    if not debugger_instance:
        return jsonify({"error": "Debugger not running"}), 400
    
    return jsonify(debugger_instance.get_all_breakpoints())


@app.route("/control", methods=["POST"])
def control_execution():
    global debugger_instance
    if not debugger_instance:
        return jsonify({"error": "Debugger not running"}), 400
    
    action = request.json.get("action")
    valid_actions = ['step', 'step_over', 'continue', 'step_back', 'quit']
    
    if action not in valid_actions:
        return jsonify({"error": "Invalid action"}), 400
    
    debugger_instance.next_command = action
    return jsonify({"message": f"Action '{action}' performed"})





threading.Thread(target=update_resource_monitor, daemon=True).start()

if __name__ == "__main__":
    app.run(debug=True, threaded=True, port=5000)