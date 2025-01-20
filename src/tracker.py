import time

class ExecutionTracker:
    def __init__(self):
        self.execution_path = []
        self.call_graph = {}
        self.current_calls = []
        
    def add_execution_step(self, line_no, code, event_type):
        """Track a single execution step"""
        clean_code = code.strip().replace('"', '\'').replace('\n', ' ')
        if len(clean_code) > 30:
            clean_code = clean_code[:27] + '...'
            
        self.execution_path.append({
            'line': line_no,
            'code': clean_code,
            'event': event_type,
            'timestamp': time.time(),
            'call_depth': len(self.current_calls)
        })

    def add_function_call(self, caller_name, callee_name):
        """Track a function call relationship"""
        if caller_name not in self.call_graph:
            self.call_graph[caller_name] = {
                'calls': set(),
                'called_from': set()
            }
            
        if callee_name not in self.call_graph:
            self.call_graph[callee_name] = {
                'calls': set(),
                'called_from': set()
            }
            
        self.call_graph[caller_name]['calls'].add(callee_name)
        self.call_graph[callee_name]['called_from'].add(caller_name)
        self.current_calls.append(callee_name)

    def remove_function_call(self, callee_name):
        """Remove the most recent call to the function"""
        if self.current_calls and self.current_calls[-1] == callee_name:
            self.current_calls.pop()
    
    def get_execution_flowchart(self):
        """Generate Mermaid flowchart from execution path"""
        if not self.execution_path:
            return "flowchart TB\nstart[No execution steps yet]"
            
        nodes = []
        edges = []
        node_ids = {}
        last_node = None
        
        for i, step in enumerate(self.execution_path):
            node_id = f"node{i}"
            label = f"{step['line']}: {step['code']}"
            nodes.append(f"{node_id}[\"{label}\"]")
            nodes.append(f"click {node_id} callback \"Line {step['line']}<br/>Code: {step['code']}<br/>Event: {step['event']}\"")
            
            if last_node:
                edges.append(f"{last_node} --> {node_id}")
            last_node = node_id
            
        return "flowchart TB\n" + "\n".join(nodes) + "\n" + "\n".join(edges)
        
    def get_call_graph(self):
        """Generate Mermaid diagram for call graph"""
        if not self.call_graph:
            return "flowchart LR\nstart[No function calls yet]"
            
        nodes = []
        edges = []
        
        for func in sorted(self.call_graph.keys()):
            clean_func = func.replace('<', '').replace('>', '').replace(' ', '_')
            
            nodes.append(f"{clean_func}[\"{func}\"]")
            calls = len(self.call_graph[func]['calls'])
            called_by = len(self.call_graph[func]['called_from'])
            nodes.append(f"click {clean_func} callback \"Function: {func}<br/>Calls: {calls}<br/>Called by: {called_by}\"")
            
            for called in sorted(self.call_graph[func]['calls']):
                clean_called = called.replace('<', '').replace('>', '').replace(' ', '_')
                edges.append(f"{clean_func} --> {clean_called}")
                
        return "flowchart LR\n" + "\n".join(nodes) + "\n" + "\n".join(edges)
