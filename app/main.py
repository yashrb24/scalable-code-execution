from fastapi import FastAPI, Form, HTTPException
from fastapi.responses import HTMLResponse
from starlette.status import HTTP_400_BAD_REQUEST
import sys
import io
import contextlib

app = FastAPI()


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
        with contextlib.redirect_stdout(redirected_output):
            exec(code)
    except Exception as e:
        # If there's an error, return it as a HTTPException
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail=str(e))
    finally:
        # Restore stdout
        sys.stdout = old_stdout

    # Get the output and send it back
    output = redirected_output.getvalue()
    return {"output": output}
