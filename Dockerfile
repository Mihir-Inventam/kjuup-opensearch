# ----------------------------
# Custom OpenSearch + Python 3.12 + Custom ML Model
# ----------------------------
FROM opensearchproject/opensearch:2.15.0

# Switch to root to install dependencies
USER root

# Install build tools & SSL/development libraries
RUN yum update -y && \
    yum install -y gcc make wget tar bzip2 \
                   libffi-devel bzip2 bzip2-devel zlib-devel xz-devel \
                   openssl-devel && \
    yum clean all

# Build and install Python 3.12
RUN cd /usr/src && \
    wget https://www.python.org/ftp/python/3.12.6/Python-3.12.6.tgz && \
    tar xvf Python-3.12.6.tgz && \
    cd Python-3.12.6 && \
    ./configure --enable-optimizations --with-ssl && \
    make -j$(nproc) && \
    make altinstall

# Verify Python & pip
RUN python3.12 --version && pip3.12 --version

# Create a virtual environment for Python dependencies
RUN python3.12 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Upgrade pip in venv
RUN pip install --upgrade pip

# Create directories for ML models and scripts
RUN mkdir -p /usr/share/opensearch/ml_models && \
    mkdir -p /usr/share/opensearch/scripts && \
    chown -R opensearch:opensearch /usr/share/opensearch/ml_models && \
    chown -R opensearch:opensearch /usr/share/opensearch/scripts

# Copy and install AI/ML dependencies
COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

# Copy model download and registration scripts
COPY download_model.py /usr/share/opensearch/scripts/
COPY register_model.py /usr/share/opensearch/scripts/
COPY startup.sh /usr/share/opensearch/scripts/

# Make scripts executable
RUN chmod +x /usr/share/opensearch/scripts/startup.sh

# Download and prepare the custom model
RUN cd /usr/share/opensearch/scripts && \
    python download_model.py

# IMPORTANT: Run startup as root so we can chown mounted volumes at runtime
USER opensearch

# Verify Python installation
RUN python --version

# Use custom startup script
CMD ["/usr/share/opensearch/scripts/startup.sh"]

