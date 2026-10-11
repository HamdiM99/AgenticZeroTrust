FROM python:3.12-slim
WORKDIR /app
COPY pyproject.toml README.md ./
COPY src ./src
COPY policies ./policies
COPY evals ./evals
COPY examples ./examples
RUN pip install --no-cache-dir -e .
ENV AZT_POLICY_DIR=/app/policies
CMD ["python", "examples/demo.py"]
