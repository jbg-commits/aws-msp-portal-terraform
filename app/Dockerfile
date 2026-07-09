FROM python:3.11-slim

# libpq for psycopg2-binary's runtime, matching the python3.11 venv used in
# production (modules/compute/main.tf's user_data) so behavior stays consistent.
RUN apt-get update && apt-get install -y --no-install-recommends libpq5 && rm -rf /var/lib/apt/lists/*

WORKDIR /opt/msp-portal

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN chmod +x docker-entrypoint.sh

EXPOSE 8080

ENTRYPOINT ["./docker-entrypoint.sh"]
