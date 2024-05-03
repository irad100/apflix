FROM python:3.12-slim

WORKDIR /app

COPY . .

RUN pip install .

EXPOSE 8501

ENTRYPOINT ["streamlit", "run", "apflix/app.py"]