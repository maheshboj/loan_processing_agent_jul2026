# Use the official optimized uv image with Python 3.12
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

# Set the working directory
WORKDIR /app

# Enable bytecode compilation
ENV UV_COMPILE_BYTECODE=1

# Copy only the dependency configuration files first to optimize layer caching
COPY pyproject.toml uv.lock ./

# Install dependencies (without installing the project itself)
RUN uv sync --frozen --no-cache --no-install-project

# Copy the application source code and data assets
COPY src/ ./src/
COPY synthetic_data/ ./synthetic_data/
COPY raw_documents/ ./raw_documents/
COPY *.pdf ./

# Install the project itself
RUN uv sync --frozen --no-cache

# Ensure the output directory exists for runtime reports and database
RUN mkdir -p output

# Set environment variables for Streamlit and Python
ENV PORT=8501
ENV HOST=0.0.0.0
ENV PYTHONPATH=/app/src

# Expose Streamlit's default port
EXPOSE 8501

# Command to run the Streamlit dashboard
CMD ["uv", "run", "streamlit", "run", "src/loan_processing_crew/dashboard.py", "--server.port=8501", "--server.address=0.0.0.0"]
