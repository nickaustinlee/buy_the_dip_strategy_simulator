# Installation Guide

This guide provides detailed installation instructions for the Buy the Dip Strategy simulator.

## System Requirements

- **Python**: 3.13 or higher
- **Operating System**: Windows, macOS, or Linux
- **Memory**: At least 512MB RAM
- **Disk Space**: 100MB for installation + data cache
- **Internet**: Required for fetching stock price data

## Installation Methods

### Method 1: Poetry (Recommended)

Poetry provides the most reliable dependency management and virtual environment handling.

#### Step 1: Install Poetry

**On macOS/Linux:**
```bash
curl -sSL https://install.python-poetry.org | python3 -
```

**On Windows (PowerShell):**
```powershell
(Invoke-WebRequest -Uri https://install.python-poetry.org -UseBasicParsing).Content | py -
```

**Alternative (using pip):**
```bash
pip install poetry
```

#### Step 2: Clone and Install

```bash
# Clone the repository
git clone <repository-url>
cd buy-the-dip-strategy

# Install dependencies and the package
poetry install

# Verify installation
poetry run buy-the-dip --help
```

> **Note:** All documentation examples use `poetry run buy-the-dip`. If you're using pip/venv, replace `poetry run buy-the-dip` with `python buy_the_dip.py` in all commands.

### Method 2: pip with Virtual Environment

#### Step 1: Create Virtual Environment

**On macOS/Linux:**
```bash
# Clone the repository
git clone <repository-url>
cd buy-the-dip-strategy

# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate
```

**On Windows:**
```cmd
# Clone the repository
git clone <repository-url>
cd buy-the-dip-strategy

# Create virtual environment
python -m venv venv

# Activate virtual environment
venv\Scripts\activate
```

#### Step 2: Install Dependencies

```bash
# Upgrade pip
pip install --upgrade pip

# Install dependencies
pip install -r requirements.txt

# Install the package in development mode
pip install -e .

# Verify installation
python buy_the_dip.py --help
```

### Method 3: Direct pip Installation (Not Recommended)

```bash
# Clone the repository
git clone <repository-url>
cd buy-the-dip-strategy

# Install directly (may conflict with system packages)
pip install -r requirements.txt
pip install -e .
```

## Verification

After installation, verify everything works correctly:

### 1. Check Command Line Interface
```bash
# Using Poetry
poetry run buy-the-dip --help

# Using pip/venv
python buy_the_dip.py --help
```

You should see the help message with available options.

### 2. Validate Default Configuration
```bash
# Using Poetry
poetry run buy-the-dip --validate-config

# Using pip/venv
python buy_the_dip.py --validate-config
```

This should show "Configuration is valid" message.

### 3. Run Basic Test
```bash
# Using Poetry
poetry run pytest tests/test_basic.py -v

# Using pip/venv (if pytest installed)
pytest tests/test_basic.py -v
```

## Troubleshooting

### Common Issues

#### 1. Python Version Error
```
ERROR: Python 3.13 or higher is required
```

**Solution:** Install Python 3.13+ from [python.org](https://python.org) or use a version manager like pyenv.

#### 2. Poetry Not Found
```
poetry: command not found
```

**Solution:** 
- Restart your terminal after installing Poetry
- Add Poetry to your PATH: `export PATH="$HOME/.local/bin:$PATH"`
- Or install via pip: `pip install poetry`

#### 3. Network/SSL Errors
```
SSL: CERTIFICATE_VERIFY_FAILED
```

**Solution:**
- Update certificates: `pip install --upgrade certifi`
- Or use: `pip install --trusted-host pypi.org --trusted-host pypi.python.org --trusted-host files.pythonhosted.org -r requirements.txt`

#### 4. Permission Errors (Windows)
```
PermissionError: [WinError 5] Access is denied
```

**Solution:**
- Run terminal as Administrator
- Or use `--user` flag: `pip install --user -r requirements.txt`

#### 5. yfinance Data Errors
```
No data found for ticker SPY
```

**Solution:**
- Check internet connection
- Verify ticker symbol is correct
- Try running again (temporary API issues)

### Getting Help

If you encounter issues not covered here:

1. **Check the logs**: Look for error messages in the console output
2. **Verify configuration**: Run with `--validate-config` flag
3. **Test network**: Try accessing [finance.yahoo.com](https://finance.yahoo.com) in your browser
4. **Update dependencies**: Run `poetry update` or `pip install --upgrade -r requirements.txt`
5. **Create an issue**: Report bugs on the project's issue tracker

## Development Setup

For contributors and developers:

### Additional Development Dependencies

```bash
# Using Poetry (installs dev dependencies automatically)
poetry install

# Using pip
pip install -r requirements-dev.txt
```

### Pre-commit Hooks (Optional)

```bash
# Install pre-commit
pip install pre-commit

# Set up git hooks
pre-commit install

# Run manually
pre-commit run --all-files
```

### IDE Setup

**VS Code:**
- Install Python extension
- Set interpreter to your virtual environment
- Configure linting (flake8) and formatting (black)

**PyCharm:**
- Set Project Interpreter to your virtual environment
- Enable code inspections for Python
- Configure external tools for black and flake8

## Next Steps

After successful installation:

1. **Read the README**: Understand the basic usage and features
2. **Try examples**: Run with different configuration files in `config_examples/`
3. **Customize configuration**: Create your own `config.yaml` file
4. **Run tests**: Execute the test suite to ensure everything works
5. **Explore the code**: Check out the modular architecture in `buy_the_dip/`

## Uninstallation

### Poetry
```bash
# Remove the virtual environment
poetry env remove python

# Delete the project directory
cd ..
rm -rf buy-the-dip-strategy
```

### pip/venv
```bash
# Deactivate virtual environment
deactivate

# Delete the project directory
cd ..
rm -rf buy-the-dip-strategy
```