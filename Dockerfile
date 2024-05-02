FROM python:3.9

WORKDIR /code

COPY ./requirements.txt /code/requirements.txt

RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt

COPY /stress_test/stress_test.py /code/stress_test.py

CMD ["python", "stress_test.py"]
