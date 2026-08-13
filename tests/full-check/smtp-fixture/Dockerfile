FROM python:3.12-alpine

WORKDIR /app
COPY smtp_fixture.py .

EXPOSE 1025 8025
CMD ["python", "smtp_fixture.py"]
