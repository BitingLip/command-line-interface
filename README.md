# BitingLip CLI

⚙️ **Status: Operational**

Command-line interface for managing the BitingLip AI inference platform. Provides administrative and operational commands for cluster management, model operations, and worker monitoring.

## Core Features

- ✅ Cluster status monitoring and management
- ✅ Model download, assignment, and unloading operations
- ✅ Worker registration and health monitoring
- ✅ Diagnostic and troubleshooting commands
- ✅ Configuration management for API endpoints
- ✅ Multiple output formats (JSON, CSV, table)
- ✅ Comprehensive help system and command completion

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Show help
python cluster-cli.py --help

# Get cluster status
python cluster-cli.py cluster status

# List all models
python cluster-cli.py models list

# List all workers
python cluster-cli.py workers list

# Download a model
python cluster-cli.py models download gpt2

# Assign model to worker
python cluster-cli.py models assign gpt2 worker-1
```

## Documentation

See [docs/](docs/) for detailed documentation:
- [CLI Reference](docs/cli-reference.md) - Complete command documentation
- [Configuration](docs/configuration.md) - Setup and configuration guide
- [Development Guide](docs/development.md) - Development and contribution guide
- [Troubleshooting](docs/troubleshooting.md) - Common issues and solutions

## Integration

The CLI integrates with:
- **Gateway Manager**: API communication for all operations
- **Cluster Manager**: Worker and model management commands
- **Model Manager**: Model download and registry operations
- **Task Manager**: Task monitoring and management

## Configuration

Key configuration options:
```bash
# API endpoint
--api-url http://localhost:8080

# Output format
--format json|csv|table

# Authentication
--api-key your-api-key-here


