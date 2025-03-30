FROM python:3.10-slim

WORKDIR /app

COPY setup.py /app/
COPY readthedocs.py /app/

RUN pip install --no-cache-dir -e .

# Expose the default MCP port if needed
EXPOSE 8080

CMD ["python", "readthedocs.py"] 