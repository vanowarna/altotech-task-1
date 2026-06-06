FROM python:3.11-slim
WORKDIR /app
COPY services/csv-replayer/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt
COPY services/csv-replayer/replayer.py /app/replayer.py
CMD ["python", "replayer.py"]
