import psutil
import time
import threading


class ResourceMonitor:
    def __init__(self):
        self.cpu_percent = 0
        self.io_counters = psutil.disk_io_counters()
        self.net_counters = psutil.net_io_counters()
        self.last_io_time = time.time()
        self.last_net_time = time.time()
        self.io_ops = 0
        self.net_bytes = 0
        self._lock = threading.Lock()
        
    def update(self):
        with self._lock:
            self.cpu_percent = psutil.cpu_percent()
            
            current_io = psutil.disk_io_counters()
            io_time = time.time()
            io_interval = io_time - self.last_io_time
            
            if io_interval > 0:
                read_ops = current_io.read_count - self.io_counters.read_count
                write_ops = current_io.write_count - self.io_counters.write_count
                self.io_ops = (read_ops + write_ops) / io_interval
                
            self.io_counters = current_io
            self.last_io_time = io_time
            
            current_net = psutil.net_io_counters()
            net_time = time.time()
            net_interval = net_time - self.last_net_time
            
            if net_interval > 0:
                bytes_sent = current_net.bytes_sent - self.net_counters.bytes_sent
                bytes_recv = current_net.bytes_recv - self.net_counters.bytes_recv
                self.net_bytes = (bytes_sent + bytes_recv) / net_interval
                
            self.net_counters = current_net
            self.last_net_time = net_time
            
    def get_usage(self):
        with self._lock:
            return {
                'cpu': self.cpu_percent,
                'io': round(self.io_ops, 1),
                'network': round(self.net_bytes, 1)
            }

resource_monitor = None

def update_resource_monitor():
    global resource_monitor
    while True:
        if resource_monitor:
            resource_monitor.update()
        time.sleep(1)
