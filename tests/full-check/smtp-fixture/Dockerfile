FROM python:3.12-alpine@sha256:d09d15e60962ca365d1cd544a48773bac9d33f2fb1b00f2aa0deec78ade7dc31

WORKDIR /app
COPY smtp_fixture.py .

EXPOSE 1025 8025
CMD ["python", "smtp_fixture.py"]
