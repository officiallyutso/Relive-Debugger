import time

class PerformanceProfiler:
    def __init__(self):
        self.function_times = {}
        self.current_functions = {}
        self._start_times = {}
        
    def start_function(self, func_name, line_no):
        """Start timing a function"""
        timestamp = time.time()
        self._start_times[func_name] = timestamp
        
        if func_name not in self.function_times:
            self.function_times[func_name] = {
                'total_time': 0,
                'calls': 0,
                'avg_time': 0,
                'last_call_time': 0,
                'line': line_no
            }
            
        self.function_times[func_name]['calls'] += 1
        
    def end_function(self, func_name):
        """End timing a function"""
        if func_name in self._start_times:
            end_time = time.time()
            elapsed = end_time - self._start_times[func_name]
            
            self.function_times[func_name]['total_time'] += elapsed
            self.function_times[func_name]['last_call_time'] = elapsed
            self.function_times[func_name]['avg_time'] = (
                self.function_times[func_name]['total_time'] / 
                self.function_times[func_name]['calls']
            )
            
            del self._start_times[func_name]
            
    def get_profile_data(self):
        """Get all profiling data"""
        return {
            'function_times': self.function_times,
            'total_execution_time': sum(
                data['total_time'] for data in self.function_times.values()
            )
        }
