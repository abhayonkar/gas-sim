FROM python:3.12-slim
WORKDIR /app
COPY . /app
RUN pip install --no-cache-dir pandapipes flask pymodbus plotly
# MATLAB not included; run externally if needed
CMD ["python", "app.py"]