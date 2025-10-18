FROM python:3.10-slim

WORKDIR /app

COPY . .

RUN pip install --upgrade pip \
    && pip install --no-cache-dir --timeout=120 -i https://pypi.tuna.tsinghua.edu.cn/simple -r requirements.txt

 
 

COPY  ./docker/develop/flask/entrypoint /entrypoint
RUN sed -i 's/\r$//g' /entrypoint

 
COPY ./docker/develop/flask/start /start
RUN sed -i 's/\r$//g' /start




ENTRYPOINT ["/entrypoint"]