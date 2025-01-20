from src.app import app, resource_monitor
from src.monitor import update_resource_monitor
import threading

if __name__ == "__main__":
    threading.Thread(target=update_resource_monitor, daemon=True).start()
    app.run(debug=True, threaded=True, port=5000)