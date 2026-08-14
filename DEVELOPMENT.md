# Development Guide for AeroDrift

## Setup

### Install Python and Git
1. Go to python.org/downloads and install Python 3.10+
2. Go to git-scm.com/downloads and install Git

### Clone and Setup the Project

```bash
git clone https://github.com/YOUR_USERNAME/project1.git
cd project1
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements-dev.txt
```

## Running the Code

### Run the Week 1 Demo

```bash
python -m aerodrift.demo_week1
```

This runs the acceptance test: ingests mock cloud state, simulates drift, and proves detection happens in under 5 seconds.

### Run Tests

```bash
pytest
```

Run tests with coverage:
```bash
pytest --cov=src/aerodrift
```

### Run the Daemon

```bash
python -c "from aerodrift.daemon import AeroDriftDaemon; from aerodrift.config import AeroDriftConfig; import asyncio; d = AeroDriftDaemon(AeroDriftConfig(use_mock_aws=True)); asyncio.run(d.run())"
```

## Project Structure