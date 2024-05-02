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

    # Plotting the data for Query 1
    plt.figure(figsize=(10, 6))
    plt.plot(timestamps_query1, values_query1, label='Container Memory Working Set Bytes')
    plt.xlabel('Timestamp')
    plt.ylabel('Memory Usage (Bytes)')
    plt.title('Container Memory Working Set Bytes over Time')
    plt.grid(True)
    plt.legend()

    # Plotting the data for Query 2
    plt.plot(timestamps_query2, values_query2, label='Container Filesystem Reads/Writes')
    plt.xlabel('Timestamp')
    plt.ylabel('Count')
    plt.title('Container Filesystem Reads/Writes over Time')
    plt.grid(True)
    plt.legend()

    # Plotting the data for Query 3
    plt.plot(timestamps_query3, values_query3, label='Container CPU Usage (seconds)')
    plt.xlabel('Timestamp')
    plt.ylabel('CPU Usage (Seconds)')
    plt.title('Container CPU Usage over Time')
    plt.grid(True)
    plt.legend()

    buffer = BytesIO()
    plt.savefig(buffer, format='png')
    buffer.seek(0)
    
    # Encode the plot as a base64 string
    plot_base64 = base64.b64encode(buffer.getvalue()).decode()

    # Close the plot to free memory
    plt.close()
    
    return plot_base64
    
@app.get("/", response_class=HTMLResponse)
async def get_form():
    return """
    <html>
        <body>
            <form action="/execute" method="post">
                <textarea name="code" rows="10" cols="50">print("Hello, World!")</textarea>
                <input type="submit" value="Execute">
            </form>
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
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail=str(e))
    finally:
        # Restore stdout
        sys.stdout = old_stdout

    # Get the output and send it back
    output = redirected_output.getvalue()
    html_response = f"""
    <html>
        <body>
            <div>
                <h2>Output:</h2>
                <pre>{output}</pre>
            </div>
            <div>
                <h2>Plot:</h2>
                <img src="data:image/png;base64,{plot_base64}" />
            </div>
        </body>
    </html>
    """
    return html_response
