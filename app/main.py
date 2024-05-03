from fastapi import FastAPI, Form, HTTPException
from fastapi.responses import HTMLResponse
from starlette.status import HTTP_400_BAD_REQUEST
import sys
import io
import contextlib
from datetime import datetime
import requests
import matplotlib.pyplot as plt
import base64
import os
from io import BytesIO

app = FastAPI()

def plot(start, end):
    # Get the value of the POD_NAME environment variable
    pod = os.environ.get("POD_NAME")
    namespace = os.environ.get("POD_NAMESPACE")
    # pod = "ubuntu"
    # namespace = "default"
    # Constructing the URL and parameters for the first query
    url_query1 = "http://stable-kube-prometheus-sta-prometheus.prometheus:9090/api/v1/query_range"
    params_query1 = {
        'query': f'sum(container_memory_working_set_bytes{{job="kubelet", metrics_path="/metrics/cadvisor", namespace="{namespace}", pod="{pod}", container!="", image!=""}}) by (container)',
        'start': start,
        'end': end,
        'step': '15s'
    }

    # Execute the first query
    response_query1 = requests.get(url_query1, params=params_query1).json()

    # Constructing the URL and parameters for the second query
    url_query2 = "http://stable-kube-prometheus-sta-prometheus.prometheus:9090/api/v1/query_range"
    params_query2 = {
        'query': f'ceil(sum by(container) (rate(container_fs_reads_total{{job="kubelet", metrics_path="/metrics/cadvisor", container!="", namespace="{namespace}", pod="{pod}"}}[1m]) + rate(container_fs_writes_total{{job="kubelet", metrics_path="/metrics/cadvisor", container!="", namespace="{namespace}", pod="{pod}"}}[1m])))',
        'start': start,
        'end': end,
        'step': '15s'
    }

    # Execute the second query
    response_query2 = requests.get(url_query2, params=params_query2).json()

    # Constructing the URL and parameters for the third query
    url_query3 = "http://stable-kube-prometheus-sta-prometheus.prometheus:9090/api/v1/query_range"
    params_query3 = {
        'query': f'sum(node_namespace_pod_container:container_cpu_usage_seconds_total:sum_irate{{namespace="{namespace}", pod="{pod}"}}) by (container)',
        'start': start,
        'end': end,
        'step': '15s'
    }

    # Execute the third query
    response_query3 = requests.get(url_query3, params=params_query3).json()
    # Print the responses

    # Extracting timestamps and values for Query 1
    timestamps_query1 = [entry[0] for entry in response_query1['data']['result'][0]['values']]
    values_query1 = [int(entry[1]) for entry in response_query1['data']['result'][0]['values']]

    # Extracting timestamps and values for Query 2
    timestamps_query2 = [entry[0] for entry in response_query2['data']['result'][0]['values']]
    values_query2 = [int(entry[1]) for entry in response_query2['data']['result'][0]['values']]

    # Extracting timestamps and values for Query 3
    timestamps_query3 = [entry[0] for entry in response_query3['data']['result'][1]['values']]
    values_query3 = [float(entry[1]) for entry in response_query3['data']['result'][1]['values']]

    fig, axs = plt.subplots(3, 1, figsize=(18, 10))
    
    # Plot for Query 1
    axs[0].plot(timestamps_query1, values_query1)
    axs[0].set_xlabel('Timestamp')
    axs[0].set_ylabel('Memory Usage (Bytes)')
    axs[0].set_title('Container Memory Working Set Bytes over Time')
    axs[0].grid(True)

    # Plot for Query 2
    axs[1].plot(timestamps_query2, values_query2)
    axs[1].set_xlabel('Timestamp')
    axs[1].set_ylabel('Count')
    axs[1].set_title('Container Filesystem Reads/Writes over Time')
    axs[1].grid(True)

    # Plot for Query 3
    axs[2].plot(timestamps_query3, values_query3)
    axs[2].set_xlabel('Timestamp')
    axs[2].set_ylabel('CPU Usage (Seconds)')
    axs[2].set_title('Container CPU Usage over Time')
    axs[2].grid(True)
    
    plt.tight_layout()  # Adjust layout to prevent overlap

    buffer = BytesIO()
    plt.savefig(buffer, format='png')
    buffer.seek(0)
    
    # Encode the plot as a base64 string
    plot_base64 = base64.b64encode(buffer.getvalue()).decode()

    plt.show()
    # Close the plot to free memory
    plt.close()
    
    return plot_base64
    
@app.get("/", response_class=HTMLResponse)
async def get_form():
    return """
    <html>
        <head>
            <style>
                .container {
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                }
                .output {
                    margin-bottom: 20px;
                    padding: 10px;
                    border: 1px solid #ccc;
                    border-radius: 5px;
                }
                .plot {
                    margin-top: 20px;
                }
            </style>
        </head>
        <body>
            <div class="container">
                <form action="/execute" method="post">
                    <textarea name="code" rows="10" cols="50">print("Hello, World!")</textarea>
                    <input type="submit" value="Execute">
                </form>
                <div class="output">
                    <h2>Output:</h2>
                    <pre id="output"></pre>
                </div>
                <div class="plot">
                    <h2>Plot:</h2>
                    <img id="plot_img" />
                </div>
            </div>
            <script>
                // Function to update output
                function updateOutput(output) {
                    document.getElementById("output").innerText = output;
                }
                // Function to update plot
                function updatePlot(plotBase64) {
                    document.getElementById("plot_img").src = "data:image/png;base64," + plotBase64;
                }
            </script>
        </body>
    </html>
    """

@app.post("/execute")
async def execute_code(code: str = Form(...)):
    # Redirect stdout to capture output
    old_stdout = sys.stdout
    redirected_output = sys.stdout = io.StringIO()

    try:
        # Execute the code safely
        start = int(datetime.now().timestamp())
        with contextlib.redirect_stdout(redirected_output):
            exec(code)
        end = int(datetime.now().timestamp())
        plot_base64 = plot(start, end)
    except Exception as e:
        # If there's an error, return it as a HTTPException
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        # Restore stdout
        sys.stdout = old_stdout

    # Get the output
    output = redirected_output.getvalue()
    
    # Update the UI with output and plot
    html_response = f"""
    <html>
        <body>
            <div class="container">
                <div class="output">
                    <h2>Output:</h2>
                    <pre>{output}</pre>
                </div>
                <div class="plot">
                    <h2>Plot:</h2>
                    <img src="data:image/png;base64,{plot_base64}" />
                </div>
            </div>
        </body>
    </html>
    """
    return HTMLResponse(content=html_response)
