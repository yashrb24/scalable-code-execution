import requests
import streamlit as st

# Function to send query to FastAPI app
def send_query(code):
    response = requests.post("http://webapp.svc.cluster.local/execute", data={"code": code})
    return response.json()

# Streamlit web interface
st.title("FastAPI Query Sender")

code = 'print("Hello, World!")'

# Continuous loop to send queries and display responses
while True:
    st.write("Query:", code)
    response = send_query(code)
    st.write("Response:", response['output'])
