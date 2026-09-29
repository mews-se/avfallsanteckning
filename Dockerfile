FROM python:3.13-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY avfallsanteckning ./avfallsanteckning

ENV AVFALLSANTECKNING_DATA=/data \
    TZ=Europe/Stockholm
VOLUME ["/data"]
EXPOSE 8400

CMD ["waitress-serve", "--host=0.0.0.0", "--port=8400", "--call", "avfallsanteckning:create_app"]
