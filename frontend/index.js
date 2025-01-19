window.callback = function(nodeId) {
    const tooltipContent = document.querySelector(`[id="${nodeId}"]`).getAttribute('title');
    if (tooltipContent) {
        const tooltip = document.createElement('div');
        tooltip.className = 'mermaid-tooltip';
        tooltip.innerHTML = tooltipContent;
        document.body.appendChild(tooltip);
        
        document.addEventListener('mousemove', moveTooltip);
        
        function moveTooltip(e) {
            tooltip.style.left = (e.pageX + 10) + 'px';
            tooltip.style.top = (e.pageY + 10) + 'px';
        }
        
        document.querySelector(`[id="${nodeId}"]`).addEventListener('mouseleave', () => {
            document.removeEventListener('mousemove', moveTooltip);
            tooltip.remove();
        });
    }
}

mermaid.initialize({
    startOnLoad: false,
    theme: 'dark',
    flowchart: {
        curve: 'basis',
        padding: 20,
        htmlLabels: true,
        useMaxWidth: true
    },
    securityLevel: 'loose'
});

let codeLines = [];
let activeBreakpoints = new Set();
let isDebugging = false;
let pollInterval = null;
let currentState = 0;
let maxStates = 0;
let selectedText = '';
let selectionStart = 0;
let selectionEnd = 0;
let currentTab = 'flowchart';
let currentZoom = 1;
let panningEnabled = false;
let lastX = 0;
let lastY = 0;
let timeChart = null;
let callsChart = null;

const codeArea = document.getElementById('codeArea');
const output = document.getElementById('output');
const variables = document.getElementById('variables');
const stackTrace = document.getElementById('stackTrace');
const fileInput = document.getElementById('fileInput');
const variableTooltip = document.getElementById('variableTooltip');
const stateCounter = document.getElementById('stateCounter');
const debugButtons = ['stepButton', 'stepOverButton', 'stepBackButton', 'continueButton', 'stopButton', 'prevStateButton', 'nextStateButton'];

fileInput.addEventListener('change', handleFileSelect);
document.addEventListener('mousemove', updateTooltipPosition);

function updateTooltipPosition(e) {
    if (variableTooltip.style.display === 'block') {
        variableTooltip.style.left = (e.pageX + 10) + 'px';
        variableTooltip.style.top = (e.pageY + 10) + 'px';
    }
}

function showVariableTooltip(value) {
    variableTooltip.textContent = value;
    variableTooltip.style.display = 'block';
}

function hideVariableTooltip() {
    variableTooltip.style.display = 'none';
}
function toggleProfilePanel(show) {
    const panel = document.getElementById('profilePanel');
    const body = document.body;
    
    if (show) {
        panel.style.display = 'flex';
        panel.offsetHeight;
        panel.classList.add('visible');
        body.classList.add('profile-open');
        setTimeout(() => body.classList.add('fade-in'), 50);
        updateProfileData();
    } else {
        panel.classList.remove('visible');
        body.classList.remove('fade-in');
        setTimeout(() => {
            panel.style.display = 'none';
            body.classList.remove('profile-open');
        }, 300);
    }
}
async function updateProfileData() {
    try {
        const response = await fetch('/profile');
        const data = await response.json();
        
        if (data.error) {
            showError(data.error);
            return;
        }
        
        updateCharts(data);
    } catch (error) {
        showError('Error fetching profile data: ' + error.message);
    }
}

function updateCharts(data) {
    const functions = Object.keys(data.function_times);
    const times = functions.map(f => data.function_times[f].total_time.toFixed(4));
    const calls = functions.map(f => data.function_times[f].calls);
    
    const chartOptions = {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
            legend: {
                labels: {
                    color: '#d4d4d4'
                }
            },
            title: {
                color: '#d4d4d4',
                font: {
                    size: 14
                }
            }
        }
    };
    
    if (timeChart) timeChart.destroy();
    timeChart = new Chart(document.getElementById('timeChart'), {
        type: 'bar',
        data: {
            labels: functions,
            datasets: [{
                label: 'Total Time (seconds)',
                data: times,
                backgroundColor: 'rgba(74, 144, 226, 0.5)',
                borderColor: 'rgba(74, 144, 226, 1)',
                borderWidth: 1
            }]
        },
        options: {
            ...chartOptions,
            plugins: {
                ...chartOptions.plugins,
                title: {
                    ...chartOptions.plugins.title,
                    display: true,
                    text: 'Function Execution Times'
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    grid: {
                        color: 'rgba(255, 255, 255, 0.1)'
                    },
                    ticks: {
                        color: '#d4d4d4'
                    }
                },
                x: {
                    grid: {
                        color: 'rgba(255, 255, 255, 0.1)'
                    },
                    ticks: {
                        color: '#d4d4d4'
                    }
                }
            }
        }
    });
    
    if (callsChart) callsChart.destroy();
    callsChart = new Chart(document.getElementById('callsChart'), {
        type: 'pie',
        data: {
            labels: functions,
            datasets: [{
                data: calls,
                backgroundColor: [
                    'rgba(74, 144, 226, 0.5)',
                    'rgba(46, 204, 113, 0.5)',
                    'rgba(230, 126, 34, 0.5)',
                    'rgba(155, 89, 182, 0.5)',
                    'rgba(241, 196, 15, 0.5)'
                ],
                borderColor: [
                    'rgba(74, 144, 226, 1)',
                    'rgba(46, 204, 113, 1)',
                    'rgba(230, 126, 34, 1)',
                    'rgba(155, 89, 182, 1)',
                    'rgba(241, 196, 15, 1)'
                ],
                borderWidth: 1
            }]
        },
        options: {
            ...chartOptions,
            plugins: {
                ...chartOptions.plugins,
                title: {
                    ...chartOptions.plugins.title,
                    display: true,
                    text: 'Function Call Distribution'
                }
            }
        }
    });
}

document.querySelector('.control-group').insertAdjacentHTML('beforeend', `
    <button onclick="toggleProfilePanel(true)">Show Profile</button>
`);

const originalPollStatus = pollStatus;
pollStatus = async function() {
    await originalPollStatus();
    if (document.getElementById('profilePanel').style.display === 'block') {
        await updateProfileData();
    }
};

function handleFileSelect(event) {
    const file = event.target.files[0];
    if (!file || !file.name.endsWith('.py')) {
        showError('Please select a valid Python file');
        return;
    }

    const reader = new FileReader();
    reader.onload = (e) => {
        const code = e.target.result;
        codeLines = code.split('\n');
        updateCodeArea(code);
        activeBreakpoints.clear();
    };
    reader.readAsText(file);
}

function updateCodeArea(code) {
    const highlighted = hljs.highlight(code, {language: 'python'}).value;
    codeArea.innerHTML = highlighted.split('\n').map((line, index) => `
        <div class="code-line${activeBreakpoints.has(index + 1) ? ' breakpoint' : ''}" 
             data-line="${index + 1}" 
             onclick="toggleBreakpoint(${index + 1})">
            ${line || ' '}
        </div>
    `).join('');
}

function highlightLine(lineNumber) {
    const lines = document.querySelectorAll('.code-line');
    lines.forEach(line => line.classList.remove('active'));
    const activeLine = document.querySelector(`[data-line="${lineNumber}"]`);
    if (activeLine) {
        activeLine.classList.add('active');
        activeLine.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
}

function initializeCodeSelection() {
    let isSelecting = false;
    let startLine = 0;

    codeArea.addEventListener('mousedown', (e) => {
        const line = e.target.closest('.code-line');
        if (line) {
            isSelecting = true;
            startLine = parseInt(line.dataset.line);
            clearSelection();
        }
    });

    document.addEventListener('mousemove', (e) => {
        if (!isSelecting) return;
        
        const line = e.target.closest('.code-line');
        if (line) {
            const currentLine = parseInt(line.dataset.line);
            updateSelection(startLine, currentLine);
        }
    });

    document.addEventListener('mouseup', () => {
        if (isSelecting) {
            isSelecting = false;
            showSelectionControls();
        }
    });
}

function clearSelection() {
    document.querySelectorAll('.code-line').forEach(line => {
        line.classList.remove('selection-active');
    });
    document.getElementById('selectionInfo').style.display = 'none';
    document.getElementById('selectionControls').style.display = 'none';
}

function updateSelection(start, end) {
    clearSelection();
    const [lineStart, lineEnd] = start < end ? [start, end] : [end, start];
    selectionStart = lineStart;
    selectionEnd = lineEnd;
    
    document.querySelectorAll('.code-line').forEach(line => {
        const lineNum = parseInt(line.dataset.line);
        if (lineNum >= lineStart && lineNum <= lineEnd) {
            line.classList.add('selection-active');
        }
    });

    selectedText = getSelectedCode(lineStart, lineEnd);
    updateSelectionInfo();
}

function getSelectedCode(start, end) {
    const lines = [];
    document.querySelectorAll('.code-line').forEach(line => {
        const lineNum = parseInt(line.dataset.line);
        if (lineNum >= start && lineNum <= end) {
            lines.push(line.textContent);
        }
    });
    return lines.join('\n');
}

function updateSelectionInfo() {
    const info = document.getElementById('selectionInfo');
    const startSpan = document.getElementById('selectionStart');
    const endSpan = document.getElementById('selectionEnd');
    
    startSpan.textContent = selectionStart;
    endSpan.textContent = selectionEnd;
    info.style.display = 'block';
}

function showSelectionControls() {
    const controls = document.getElementById('selectionControls');
    const selection = window.getSelection();
    const range = selection.getRangeAt(0);
    const rect = range.getBoundingClientRect();
    
    controls.style.left = `${rect.left}px`;
    controls.style.top = `${rect.bottom + 5}px`;
    controls.style.display = 'block';
}

function evaluateSelection() {
    const evaluationInput = document.getElementById('evaluationInput');
    evaluationInput.value = selectedText;
    toggleEvaluationPanel(true);
}

function debugSelection() {
    startDebugger(selectionStart, selectionEnd);
}
function toggleEditor(show) {
    const panel = document.getElementById('editorPanel');
    const body = document.body;
    
    if (show) {
        panel.classList.add('open');
        body.classList.add('editor-open');
        setTimeout(() => body.classList.add('fade-in'), 50);
    } else {
        panel.classList.remove('open');
        body.classList.remove('fade-in');
        setTimeout(() => {
            body.classList.remove('editor-open');
        }, 300);
    }
}
function debugEditorCode() {
    const code = document.getElementById('codeEditor').value;
    if (!code.trim()) {
        showError('Please write some code first');
        return;
    }
    
    codeLines = code.split('\n');
    
    toggleEditor(false);
    
    startDebugger();
}

async function evaluateCode() {
    const code = document.getElementById('evaluationInput').value;
    if (!code.trim()) return;

    try {
        const response = await fetch('/evaluate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ 
                code,
                line_number: selectionStart
            })
        });

        const data = await response.json();
        displayEvaluationResult(data);
    } catch (error) {
        showError(`Evaluation error: ${error.message}`);
    }
}

function displayEvaluationResult(data) {
    const resultsDiv = document.getElementById('evaluationResults');
    let html = '<div class="evaluation-result">';
    
    if (data.error) {
        html += `<div style="color: #f44;">Error: ${data.error}</div>`;
    } else {
        if (data.result !== null) {
            html += `<div>Result: ${data.result}</div>`;
        }
        if (data.output) {
            html += `<div>Output: ${data.output}</div>`;
        }
        if (data.side_effects && data.side_effects.length > 0) {
            html += '<div class="side-effect">Side Effects:';
            data.side_effects.forEach(effect => {
                html += `<div>• ${effect}</div>`;
            });
            html += '</div>';
        }
    }
    html += '</div>';
    
    resultsDiv.innerHTML = html + resultsDiv.innerHTML;
}

function toggleEvaluationPanel(show) {
    document.getElementById('evaluationPanel').style.display = show ? 'block' : 'none';
}

async function startDebugger(startLine = null, endLine = null) {
    if (!codeLines.length) {
        showError('Please load a Python file first');
        return;
    }

    try {
        const response = await fetch('/start', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ 
                code: codeLines.join('\n'),
                start_line: startLine,
                end_line: endLine
            })
        });

        if (!response.ok) throw new Error('Failed to start debugger');

        const data = await response.json();
        if (data.highlighted_code) {
            updateCodeArea(codeLines.join('\n'));
        }

        isDebugging = true;
        updateButtons(true);
        startPolling();
        
        if (activeBreakpoints.size > 0) {
            await sendBreakpoints();
        }

    } catch (error) {
        showError(`Error starting debugger: ${error.message}`);
    }
}

async function step() {
    await sendControl('step');
}

async function stepOver() {
    await sendControl('step_over');
}

async function stepBack() {
    await sendControl('step_back');
}

async function continueExecution() {
    await sendControl('continue');
}

async function quitDebugger() {
    await sendControl('quit');
    stopDebugger();
}

function setBreakpoint(type) {
    const lineNumber = parseInt(document.getElementById('breakpointLine').value);
    const condition = document.getElementById('breakpointCondition').value.trim();
    
    if (!lineNumber || lineNumber < 1) {
        showError('Please enter a valid line number');
        return;
    }

    const line = document.querySelector(`[data-line="${lineNumber}"]`);
    if (!line) {
        showError('Line number not found in code');
        return;
    }

    if (type === 'conditional' && !condition) {
        showError('Please enter a condition for conditional breakpoint');
        return;
    }

    if (activeBreakpoints.has(lineNumber)) {
        activeBreakpoints.delete(lineNumber);
        line.classList.remove('breakpoint', 'conditional-breakpoint');
        line.removeAttribute('data-condition');
        
        const existingIndicator = line.querySelector('.conditional-indicator');
        if (existingIndicator) {
            existingIndicator.remove();
        }
    }

    activeBreakpoints.add(lineNumber);
    line.classList.add('breakpoint');

    if (type === 'conditional' && condition) {
        line.classList.add('conditional-breakpoint');
        line.setAttribute('data-condition', condition);
        
        const indicator = document.createElement('span');
        indicator.className = 'conditional-indicator';
        indicator.title = `Condition: ${condition}`;
        indicator.innerHTML = '⚡';
        line.insertBefore(indicator, line.firstChild);
    }

    document.getElementById('breakpointLine').value = '';
    document.getElementById('breakpointCondition').value = '';

    if (isDebugging) {
        sendBreakpoints();
    }
    updateBreakpointList();
}

function toggleBreakpoint(lineNumber) {
    const line = document.querySelector(`[data-line="${lineNumber}"]`);
    if (!line) return;

    const condition = document.getElementById('breakpointCondition')?.value?.trim();

    if (activeBreakpoints.has(lineNumber)) {
        activeBreakpoints.delete(lineNumber);
        line.classList.remove('breakpoint', 'conditional-breakpoint');
        line.removeAttribute('data-condition');
    } else {
        activeBreakpoints.add(lineNumber);
        line.classList.add('breakpoint');
        if (condition) {
            line.classList.add('conditional-breakpoint');
            line.setAttribute('data-condition', condition);
            let indicator = line.querySelector('.conditional-indicator');
            if (!indicator) {
                indicator = document.createElement('span');
                indicator.className = 'conditional-indicator';
                indicator.title = `Condition: ${condition}`;
                indicator.innerHTML = '⚡';
                line.insertBefore(indicator, line.firstChild);
            }
        }
    }

    if (isDebugging) {
        sendBreakpoints();
    }
    updateBreakpointList();
}
function updateBreakpointList() {
    const breakpointList = document.getElementById('breakpointList');
    if (!breakpointList) return;
    
    breakpointList.innerHTML = '';
    
    Array.from(activeBreakpoints).sort((a, b) => a - b).forEach(line => {
        const element = document.querySelector(`[data-line="${line}"]`);
        const condition = element.getAttribute('data-condition');
        
        const breakpointDiv = document.createElement('div');
        breakpointDiv.className = 'breakpoint-item';
        breakpointDiv.innerHTML = `
            <span class="breakpoint-line">Line ${line}</span>
            ${condition ? `
                <span class="breakpoint-condition" title="${condition}">
                    <span class="condition-icon">⚡</span>
                    ${condition.length > 20 ? condition.substring(0, 20) + '...' : condition}
                </span>
            ` : ''}
            <button class="remove-breakpoint" onclick="removeBreakpoint(${line})">×</button>
        `;
        breakpointList.appendChild(breakpointDiv);
    });
}

async function sendBreakpoints() {
    try {
        const breakpoints = Array.from(activeBreakpoints).map(line => {
            const element = document.querySelector(`[data-line="${line}"]`);
            const condition = document.getElementById('breakpointCondition').value.trim();
            return {
                line: line,
                condition: condition || null
            };
        });
        
        await fetch('/breakpoints', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ breakpoints })
        });
    } catch (error) {
        showError(`Error setting breakpoints: ${error.message}`);
    }
}

function removeBreakpoint(line) {
    activeBreakpoints.delete(line);
    const lineElement = document.querySelector(`[data-line="${line}"]`);
    if (lineElement) {
        lineElement.classList.remove('breakpoint', 'conditional-breakpoint');
    }
    if (isDebugging) {
        sendBreakpoints();
    }
    updateBreakpointList();
}



function toggleBreakpoint(lineNumber) {
    if (!lineNumber) {
        lineNumber = parseInt(document.getElementById('breakpointLine').value);
        if (!lineNumber || lineNumber < 1) return;
    }

    const line = document.querySelector(`[data-line="${lineNumber}"]`);
    if (!line) return;

    if (activeBreakpoints.has(lineNumber)) {
        activeBreakpoints.delete(lineNumber);
        line.classList.remove('breakpoint');
    } else {
        activeBreakpoints.add(lineNumber);
        line.classList.add('breakpoint');
    }

    if (isDebugging) {
        sendBreakpoints();
    }
}

function navigateState(direction) {
    const newState = currentState + direction;
    if (newState >= 0 && newState < maxStates) {
        currentState = newState;
        updateStateCounter();
    }
}

function updateStateCounter() {
    stateCounter.textContent = `State ${currentState + 1}/${maxStates}`;
}

function updateButtons(enabled) {
    debugButtons.forEach(buttonId => {
        document.getElementById(buttonId).disabled = !enabled;
    });
    document.getElementById('startButton').disabled = enabled;
}

function updateVariables(variables, variablesDiv) {
    if (!variables || !variablesDiv) return;

    let html = '';
    if (variables.locals && Object.keys(variables.locals).length > 0) {
        html += '<div class="variable-group">';
        html += '<div class="section-title">Local Variables</div>';
        html += Object.entries(variables.locals)
            .map(([name, value]) => createVariableElement(name, value))
            .join('');
        html += '</div>';
    }

    if (variables.globals && Object.keys(variables.globals).length > 0) {
        html += '<div class="variable-group">';
        html += '<div class="section-title">Global Variables</div>';
        html += Object.entries(variables.globals)
            .map(([name, value]) => createVariableElement(name, value))
            .join('');
        html += '</div>';
    }

    variablesDiv.innerHTML = html;
}

function createVariableElement(name, value) {
    return `
        <div class="variable-item" 
             onmouseover="showVariableTooltip('${value.replace(/'/g, "\\'")}')"
             onmouseout="hideVariableTooltip()">
            <span class="variable-name">${name}</span>
            <span class="variable-value">${value}</span>
        </div>
    `;
}

function updateStackTrace(frames) {
    if (!frames || !frames.length) return;

    stackTrace.innerHTML = frames.map((frame, index) => `
        <div class="stack-frame${index === 0 ? ' active' : ''}" 
             onclick="selectStackFrame(${index})">
            <div>${frame.function} at line ${frame.line}</div>
            <div style="font-size: 12px; color: #888;">${frame.file}</div>
        </div>
    `).join('');
}

async function sendControl(action) {
    try {
        await fetch('/control', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ action })
        });
    } catch (error) {
        showError(`Error sending command: ${error.message}`);
    }
}

async function sendBreakpoints() {
    try {
        const breakpoints = Array.from(activeBreakpoints).map(line => {
            const element = document.querySelector(`[data-line="${line}"]`);
            const condition = element.getAttribute('data-condition');
            return {
                line: line,
                condition: condition || null
            };
        });
        
        const response = await fetch('/breakpoints', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ breakpoints })
        });
        
        if (!response.ok) {
            throw new Error('Failed to set breakpoints');
        }
        
        updateBreakpointList();
    } catch (error) {
        showError(`Error setting breakpoints: ${error.message}`);
    }
}

function startPolling() {
    if (pollInterval) clearInterval(pollInterval);
    pollInterval = setInterval(pollStatus, 300);
}

async function pollStatus() {
    if (!isDebugging) return;

    try {
        const [statusResponse, visualResponse] = await Promise.all([
            fetch('/status'),
            fetch('/visualizations')
        ]);

        if (!statusResponse.ok || !visualResponse.ok) 
            throw new Error('Failed to get data');
        
        const statusData = await statusResponse.json();
        const visualData = await visualResponse.json();
        
        updateDebuggerState(statusData);
        updateVisualizations(visualData);
        
        if (!statusData.is_running || statusData.exception) {
            stopDebugger();
        }
    } catch (error) {
        console.error('Error polling:', error);
        stopDebugger();
    }
}

function updateVisualizations(data) {
    const container = document.getElementById('diagramContainer');
    if (!container) return;

    const diagram = currentTab === 'flowchart' ? 
        data.execution_flowchart : 
        data.call_graph;
        
    container.innerHTML = '';
    
    if (diagram) {
        mermaid.render('diagram', diagram)
            .then(({svg}) => {
                container.innerHTML = svg;
                applyZoom();
                setupPanning();
                
                const nodes = container.querySelectorAll('.node');
                nodes.forEach(node => {
                    node.addEventListener('mouseenter', () => {
                        node.style.filter = 'brightness(1.2)';
                    });
                    node.addEventListener('mouseleave', () => {
                        node.style.filter = '';
                    });
                });
            })
            .catch(error => {
                console.error('Mermaid rendering error:', error);
                container.innerHTML = '<div class="error">Error rendering diagram</div>';
            });
    }
}

function toggleVisualizationPanel(show) {
    const panel = document.getElementById('visualizationPanel');
    
    if (show) {
        panel.style.display = 'flex';
        panel.offsetHeight;
        panel.classList.add('visible');
    } else {
        panel.classList.remove('visible');
        setTimeout(() => {
            panel.style.display = 'none';
        }, 300);
    }
}

function switchTab(tab) {
    currentTab = tab;
    document.querySelectorAll('.visualization-tab').forEach(el => {
        el.classList.toggle('active', el.textContent.toLowerCase().includes(tab));
    });
    pollStatus();
}

function zoomDiagram(delta) {
    currentZoom = Math.max(0.1, Math.min(2, currentZoom + delta));
    applyZoom();
}

function resetZoom() {
    currentZoom = 1;
    applyZoom();
}

function applyZoom() {
    const svg = document.querySelector('#diagramContainer svg');
    if (svg) {
        svg.style.transform = `scale(${currentZoom})`;
        svg.style.transformOrigin = 'center';
    }
}

function setupPanning() {
    const container = document.getElementById('diagramContainer');
    
    container.addEventListener('mousedown', (e) => {
        panningEnabled = true;
        lastX = e.clientX;
        lastY = e.clientY;
        container.style.cursor = 'grabbing';
    });

    container.addEventListener('mousemove', (e) => {
        if (!panningEnabled) return;
        
        const dx = e.clientX - lastX;
        const dy = e.clientY - lastY;
        
        container.scrollLeft -= dx;
        container.scrollTop -= dy;
        
        lastX = e.clientX;
        lastY = e.clientY;
    });

    container.addEventListener('mouseup', () => {
        panningEnabled = false;
        container.style.cursor = 'default';
    });

    container.addEventListener('mouseleave', () => {
        panningEnabled = false;
        container.style.cursor = 'default';
    });
}


function updateDebuggerState(data) {
    const variablesDiv = document.getElementById('variables');
    updateVariables(data.variables, variablesDiv);
    updateStackTrace(data.stack_frames);
    
    if (data.current_line) {
        highlightLine(data.current_line);
    }
    
    if (data.output) {
        output.textContent = data.output;
    }
    
    if (data.exception) {
        showError(data.exception);
    }

    currentState = data.current_state;
    maxStates = data.states;
    updateStateCounter();
}

function stopDebugger() {
    isDebugging = false;
    updateButtons(false);
    if (pollInterval) {
        clearInterval(pollInterval);
        pollInterval = null;
    }
}

function showError(message) {
    const errorDiv = document.createElement('div');
    errorDiv.className = 'error-message';
    errorDiv.textContent = message;
    output.appendChild(errorDiv);
    setTimeout(() => errorDiv.remove(), 5000);
}

function selectStackFrame(index) {
    document.querySelectorAll('.stack-frame').forEach((frame, i) => {
        frame.classList.toggle('active', i === index);
    });
}
document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
        toggleEditor(false);
    }
});
document.addEventListener('DOMContentLoaded', () => {
    initializeCodeSelection();
});
document.querySelector('.control-group').insertAdjacentHTML('beforeend', `
    <button onclick="toggleVisualizationPanel(true)">Show Visualizations</button>
`);

function toggleResourceDetail(show) {
    document.querySelector('.resource-detail').classList.toggle('show', show);
    document.querySelector('.resource-overlay').classList.toggle('show', show);
}

let cpuChart, ioChart, networkChart;
const chartOptions = {
    responsive: true,
    animation: false,
    scales: {
        y: {
            beginAtZero: true
        }
    }
};

function initCharts() {
    cpuChart = new Chart(document.getElementById('cpuChart'), {
        type: 'line',
        data: {
            labels: [],
            datasets: [{
                label: 'CPU Usage (%)',
                data: [],
                borderColor: 'rgb(75, 192, 192)',
                tension: 0.1
            }]
        },
        options: chartOptions
    });

    ioChart = new Chart(document.getElementById('ioChart'), {
        type: 'line',
        data: {
            labels: [],
            datasets: [{
                label: 'I/O Operations/s',
                data: [],
                borderColor: 'rgb(153, 102, 255)',
                tension: 0.1
            }]
        },
        options: chartOptions
    });

    networkChart = new Chart(document.getElementById('networkChart'), {
        type: 'line',
        data: {
            labels: [],
            datasets: [{
                label: 'Network Usage (B/s)',
                data: [],
                borderColor: 'rgb(255, 99, 132)',
                tension: 0.1
            }]
        },
        options: chartOptions
    });
}
function updateResourceData() {
    fetch('/resource_usage')
        .then(response => response.json())
        .then(data => {
            document.getElementById('cpuValue').textContent = `${data.cpu.toFixed(1)}%`;
            document.getElementById('ioValue').textContent = `${data.io} ops/s`;
            document.getElementById('networkValue').textContent = `${formatBytes(data.network)}/s`;

            updateChart(cpuChart, data.cpu);
            updateChart(ioChart, data.io);
            updateChart(networkChart, data.network);
        });
}

function updateChart(chart, value) {
    const now = new Date().toLocaleTimeString();
    chart.data.labels.push(now);
    chart.data.datasets[0].data.push(value);

    if (chart.data.labels.length > 20) {
        chart.data.labels.shift();
        chart.data.datasets[0].data.shift();
    }

    chart.update();
}

function formatBytes(bytes) {
    if (bytes < 1024) return bytes + ' B';
    else if (bytes < 1048576) return (bytes / 1024).toFixed(1) + ' KB';
    else return (bytes / 1048576).toFixed(1) + ' MB';
}

document.addEventListener('DOMContentLoaded', () => {
    initCharts();
    setInterval(updateResourceData, 1000);
});



const chartConfig = {
    cpu: {
        type: 'line',
        data: {
            labels: [],
            datasets: [{
                label: 'User CPU',
                borderColor: '#4a90e2',
                backgroundColor: 'rgba(74, 144, 226, 0.1)',
                data: [],
                fill: true
            }, {
                label: 'System CPU',
                borderColor: '#ff6b6b',
                backgroundColor: 'rgba(255, 107, 107, 0.1)',
                data: [],
                fill: true
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: {
                intersect: false,
                mode: 'index'
            },
            plugins: {
                legend: {
                    position: 'top',
                    labels: {
                        color: '#d4d4d4',
                        padding: 10,
                        font: {
                            family: 'Inter'
                        }
                    }
                },
                tooltip: {
                    backgroundColor: 'rgba(28, 28, 28, 0.95)',
                    borderColor: 'rgba(255, 255, 255, 0.1)',
                    titleColor: '#fff',
                    bodyColor: '#d4d4d4',
                    padding: 12,
                    boxPadding: 6
                }
            },
            scales: {
                x: {
                    grid: {
                        color: 'rgba(255, 255, 255, 0.05)'
                    },
                    ticks: {
                        color: '#888'
                    }
                },
                y: {
                    beginAtZero: true,
                    max: 100,
                    grid: {
                        color: 'rgba(255, 255, 255, 0.05)'
                    },
                    ticks: {
                        color: '#888',
                        callback: value => `${value}%`
                    }
                }
            }
        }
    },
    memory: {
        type: 'line',
        data: {
            labels: [],
            datasets: [{
                label: 'Used Memory',
                borderColor: '#4caf50',
                backgroundColor: 'rgba(76, 175, 80, 0.1)',
                data: [],
                fill: true
            }, {
                label: 'Cache',
                borderColor: '#ff9800',
                backgroundColor: 'rgba(255, 152, 0, 0.1)',
                data: [],
                fill: true
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: {
                intersect: false,
                mode: 'index'
            },
            plugins: {
                legend: {
                    position: 'top',
                    labels: {
                        color: '#d4d4d4',
                        padding: 10,
                        font: {
                            family: 'Inter'
                        }
                    }
                },
                tooltip: {
                    backgroundColor: 'rgba(28, 28, 28, 0.95)',
                    borderColor: 'rgba(255, 255, 255, 0.1)',
                    titleColor: '#fff',
                    bodyColor: '#d4d4d4',
                    padding: 12,
                    boxPadding: 6
                }
            },
            scales: {
                x: {
                    grid: {
                        color: 'rgba(255, 255, 255, 0.05)'
                    },
                    ticks: {
                        color: '#888'
                    }
                },
                y: {
                    beginAtZero: true,
                    grid: {
                        color: 'rgba(255, 255, 255, 0.05)'
                    },
                    ticks: {
                        color: '#888',
                        callback: value => `${formatBytes(value)}`
                    }
                }
            }
        }
    },
    io: {
        type: 'bar',
        data: {
            labels: [],
            datasets: [{
                label: 'Read Operations',
                backgroundColor: 'rgba(74, 144, 226, 0.5)',
                borderColor: '#4a90e2',
                data: [],
                borderWidth: 1
            }, {
                label: 'Write Operations',
                backgroundColor: 'rgba(255, 107, 107, 0.5)',
                borderColor: '#ff6b6b',
                data: [],
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: {
                intersect: false,
                mode: 'index'
            },
            plugins: {
                legend: {
                    position: 'top',
                    labels: {
                        color: '#d4d4d4',
                        padding: 10,
                        font: {
                            family: 'Inter'
                        }
                    }
                },
                tooltip: {
                    backgroundColor: 'rgba(28, 28, 28, 0.95)',
                    borderColor: 'rgba(255, 255, 255, 0.1)',
                    titleColor: '#fff',
                    bodyColor: '#d4d4d4',
                    padding: 12,
                    boxPadding: 6
                }
            },
            scales: {
                x: {
                    stacked: true,
                    grid: {
                        color: 'rgba(255, 255, 255, 0.05)'
                    },
                    ticks: {
                        color: '#888'
                    }
                },
                y: {
                    stacked: true,
                    beginAtZero: true,
                    grid: {
                        color: 'rgba(255, 255, 255, 0.05)'
                    },
                    ticks: {
                        color: '#888',
                        callback: value => `${value} ops/s`
                    }
                }
            }
        }
    },
    network: {
        type: 'line',
        data: {
            labels: [],
            datasets: [{
                label: 'Inbound Traffic',
                borderColor: '#4caf50',
                backgroundColor: 'rgba(76, 175, 80, 0.1)',
                data: [],
                fill: true
            }, {
                label: 'Outbound Traffic',
                borderColor: '#ff9800',
                backgroundColor: 'rgba(255, 152, 0, 0.1)',
                data: [],
                fill: true
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: {
                intersect: false,
                mode: 'index'
            },
            plugins: {
                legend: {
                    position: 'top',
                    labels: {
                        color: '#d4d4d4',
                        padding: 10,
                        font: {
                            family: 'Inter'
                        }
                    }
                },
                tooltip: {
                    backgroundColor: 'rgba(28, 28, 28, 0.95)',
                    borderColor: 'rgba(255, 255, 255, 0.1)',
                    titleColor: '#fff',
                    bodyColor: '#d4d4d4',
                    padding: 12,
                    boxPadding: 6
                }
            },
            scales: {
                x: {
                    grid: {
                        color: 'rgba(255, 255, 255, 0.05)'
                    },
                    ticks: {
                        color: '#888'
                    }
                },
                y: {
                    beginAtZero: true,
                    grid: {
                        color: 'rgba(255, 255, 255, 0.05)'
                    },
                    ticks: {
                        color: '#888',
                        callback: value => formatBytes(value) + '/s'
                    }
                }
            }
        }
    }
};


function formatBytes(bytes) {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

function formatNumber(num) {
    return num.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ",");
}
let charts = {};
const chartContexts = {
    cpu: document.getElementById('cpuChart'),
    memory: document.getElementById('memoryChart'),
    io: document.getElementById('ioChart'),
    network: document.getElementById('networkChart')
};

Object.keys(chartContexts).forEach(type => {
    if (chartContexts[type]) {
        charts[type] = new Chart(chartContexts[type], chartConfig[type]);
    }
});

function updateResourceMonitor(data) {
    document.getElementById('cpuValue').textContent = `${data.cpu.total}%`;
    document.getElementById('memoryValue').textContent = formatBytes(data.memory.used);
    document.getElementById('ioValue').textContent = `${formatNumber(data.io.total)} ops/s`;
    document.getElementById('networkValue').textContent = `${formatBytes(data.network.total)}/s`;

    document.getElementById('cpuLoadAvg').textContent = `${data.cpu.loadAvg}%`;
    document.getElementById('memoryUsage').textContent = formatBytes(data.memory.total);
    document.getElementById('diskIoRate').textContent = `${formatNumber(data.io.rate)} MB/s`;
    document.getElementById('networkRate').textContent = `${formatBytes(data.network.throughput)}/s`;

    updateTrendIndicator('cpuTrend', data.cpu.trend);
    updateTrendIndicator('memoryTrend', data.memory.trend);
    updateTrendIndicator('ioTrend', data.io.trend);
    updateTrendIndicator('networkTrend', data.network.trend);

    updateChart(data);
}

function updateTrendIndicator(elementId, trend) {
    const element = document.getElementById(elementId);
    const value = parseFloat(trend);
    element.textContent = `${value >= 0 ? '+' : ''}${value}% from baseline`;
    element.className = `stat-change ${value >= 0 ? 'positive' : 'negative'}`;
}

function updateChart(data) {
    const timestamp = new Date().toLocaleTimeString();

    // Update CPU chart and metrics
    charts.cpu.data.labels.push(timestamp);
    charts.cpu.data.datasets[0].data.push(data.cpu.user);
    charts.cpu.data.datasets[1].data.push(data.cpu.system);
    if (charts.cpu.data.labels.length > 20) {
        charts.cpu.data.labels.shift();
        charts.cpu.data.datasets.forEach(dataset => dataset.data.shift());
    }
    charts.cpu.update('none');
    
    // Update CPU metrics
    document.getElementById('cpuUserValue').textContent = `${data.cpu.user}%`;
    document.getElementById('cpuSystemValue').textContent = `${data.cpu.system}%`;

    // Update Memory chart and metrics
    charts.memory.data.labels.push(timestamp);
    charts.memory.data.datasets[0].data.push(data.memory.used);
    charts.memory.data.datasets[1].data.push(data.memory.cached);
    if (charts.memory.data.labels.length > 20) {
        charts.memory.data.labels.shift();
        charts.memory.data.datasets.forEach(dataset => dataset.data.shift());
    }
    charts.memory.update('none');
    
    // Update Memory metrics
    document.getElementById('memUsedValue').textContent = formatBytes(data.memory.used);
    document.getElementById('memAvailValue').textContent = formatBytes(data.memory.total - data.memory.used);

    // Update IO chart and metrics
    charts.io.data.labels.push(timestamp);
    charts.io.data.datasets[0].data.push(data.io.read);
    charts.io.data.datasets[1].data.push(data.io.write);
    if (charts.io.data.labels.length > 20) {
        charts.io.data.labels.shift();
        charts.io.data.datasets.forEach(dataset => dataset.data.shift());
    }
    charts.io.update('none');
    
    // Update IO metrics
    document.getElementById('ioReadValue').textContent = `${formatNumber(data.io.read)} ops/s`;
    document.getElementById('ioWriteValue').textContent = `${formatNumber(data.io.write)} ops/s`;

    // Update Network chart and metrics
    charts.network.data.labels.push(timestamp);
    charts.network.data.datasets[0].data.push(data.network.in);
    charts.network.data.datasets[1].data.push(data.network.out);
    if (charts.network.data.labels.length > 20) {
        charts.network.data.labels.shift();
        charts.network.data.datasets.forEach(dataset => dataset.data.shift());
    }
    charts.network.update('none');
    
    // Update Network metrics
    document.getElementById('netInValue').textContent = `${formatBytes(data.network.in)}/s`;
    document.getElementById('netOutValue').textContent = `${formatBytes(data.network.out)}/s`;
}

function toggleResourceDetail(show) {
    const detail = document.querySelector('.resource-detail');
    const overlay = document.querySelector('.resource-overlay');
    
    if (show) {
        detail.classList.add('show');
        overlay.classList.add('show');
        document.body.style.overflow = 'hidden';
    } else {
        detail.classList.remove('show');
        overlay.classList.remove('show');
        document.body.style.overflow = '';
    }
}

document.addEventListener('DOMContentLoaded', () => {
    setInterval(() => {
        const mockData = generateMockData();
        updateResourceMonitor(mockData);
    }, 1000);
});

function generateMockData() {
    return {
        cpu: {
            total: Math.floor(Math.random() * 100),
            user: Math.floor(Math.random() * 60),
            system: Math.floor(Math.random() * 40),
            loadAvg: Math.floor(Math.random() * 100),
            trend: (Math.random() * 10 - 5).toFixed(1)
        },
        memory: {
            total: 16 * 1024 * 1024 * 1024, // Fixed total memory: 16GB
            used: Math.random() * 8 * 1024 * 1024 * 1024,
            cached: Math.random() * 4 * 1024 * 1024 * 1024,
            trend: (Math.random() * 10 - 5).toFixed(1)
        },
        io: {
            total: Math.floor(Math.random() * 1000),
            read: Math.floor(Math.random() * 500),
            write: Math.floor(Math.random() * 500),
            rate: Math.floor(Math.random() * 100),
            trend: (Math.random() * 10 - 5).toFixed(1)
        },
        network: {
            total: Math.random() * 100 * 1024 * 1024,
            in: Math.random() * 50 * 1024 * 1024,
            out: Math.random() * 50 * 1024 * 1024,
            throughput: Math.random() * 100 * 1024 * 1024,
            trend: (Math.random() * 10 - 5).toFixed(1)
        }
    };
}