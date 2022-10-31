FROM python:3.9

WORKDIR /app
ENV PYTHONPATH="/app"

ADD requirements.txt .
RUN pip3 install -r requirements.txt

ADD rounder /app/rounder

CMD ["-m", "rounder"]
ENTRYPOINT ["python3"]
