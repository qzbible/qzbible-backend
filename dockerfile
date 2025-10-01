FROM python:3.10-slim

WORKDIR /app

COPY . .

RUN pip install --upgrade pip \
    && pip install --no-cache-dir --timeout=120 -i https://pypi.tuna.tsinghua.edu.cn/simple -r requirements.txt

CMD ["flask", "run", "--host=0.0.0.0", "--port=5001"]
