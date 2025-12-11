FROM python:3.12

WORKDIR /code

COPY ./requirements.txt /code/requirements.txt

RUN apt-get update && apt-get install -y build-essential
RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt

COPY . /code

EXPOSE 8123

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8123"]
