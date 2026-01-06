# Documentation Index

This document provides an overview of all available documentation for the Buy the Dip Strategy project.

## 📚 Main Documentation

### [README.md](README.md)
**Primary project documentation**
- Project overview and features
- Installation instructions
- Basic usage examples
- Architecture overview
- Development setup

### [QUICKSTART.md](QUICKSTART.md) ⭐ **Start Here**
**5-minute setup guide for new users**
- Fast installation steps
- First run instructions
- Understanding output
- Common use cases
- Troubleshooting basics

## 🛠️ Setup and Installation

### [INSTALLATION.md](INSTALLATION.md)
**Comprehensive installation guide**
- System requirements
- Multiple installation methods
- Verification steps
- Troubleshooting common issues
- Development setup

## ⚙️ Configuration

### [CONFIGURATION_GUIDE.md](CONFIGURATION_GUIDE.md)
**Complete configuration reference**
- Parameter explanations
- Pre-built strategy examples
- Custom configuration creation
- Advanced tips and best practices
- Risk management guidelines

### Configuration Examples Directory: `config_examples/`
**Ready-to-use strategy configurations**
- `conservative.yaml` - Low risk, stable approach
- `balanced.yaml` - Moderate risk/reward balance
- `aggressive.yaml` - High risk, frequent trading
- `individual_stock.yaml` - Single stock strategy
- `dividend_focused.yaml` - Income-oriented approach
- `small_cap.yaml` - Growth-focused small caps
- `crypto_etf.yaml` - Cryptocurrency exposure
- `template.yaml` - Customizable template

## 📋 Usage and Examples

### [EXAMPLES.md](EXAMPLES.md)
**Detailed usage scenarios and examples**
- Basic usage patterns
- Advanced configuration examples
- Real-world scenarios
- Performance analysis
- Error handling examples
- Monitoring and backtesting

## 📁 File Structure Overview

```
buy-the-dip-strategy/
├── README.md                    # Main project documentation
├── QUICKSTART.md               # 5-minute setup guide
├── INSTALLATION.md             # Detailed installation guide
├── CONFIGURATION_GUIDE.md      # Complete configuration reference
├── EXAMPLES.md                 # Usage examples and scenarios
├── DOCUMENTATION_INDEX.md      # This file
├── config.yaml                 # Default configuration
├── config_examples/            # Example configurations
│   ├── conservative.yaml
│   ├── balanced.yaml
│   ├── aggressive.yaml
│   ├── individual_stock.yaml
│   ├── dividend_focused.yaml
│   ├── small_cap.yaml
│   ├── crypto_etf.yaml
│   └── template.yaml
├── buy_the_dip/               # Source code
├── tests/                     # Test suite
└── ...
```

## 🎯 Documentation by Use Case

### New Users
1. **[QUICKSTART.md](QUICKSTART.md)** - Get running in 5 minutes
2. **[README.md](README.md)** - Understand the project
3. **[EXAMPLES.md](EXAMPLES.md)** - See usage examples

### Configuration Help
1. **[CONFIGURATION_GUIDE.md](CONFIGURATION_GUIDE.md)** - Complete reference
2. **`config_examples/`** - Ready-made examples
3. **[EXAMPLES.md](EXAMPLES.md)** - Real-world scenarios

### Installation Issues
1. **[INSTALLATION.md](INSTALLATION.md)** - Detailed setup guide
2. **[QUICKSTART.md](QUICKSTART.md)** - Quick troubleshooting
3. **[README.md](README.md)** - Development setup

### Advanced Usage
1. **[EXAMPLES.md](EXAMPLES.md)** - Advanced scenarios
2. **[CONFIGURATION_GUIDE.md](CONFIGURATION_GUIDE.md)** - Custom strategies
3. **[README.md](README.md)** - Architecture and development

## 🔍 Quick Reference

### Essential Commands
```bash
# Quick start
poetry run buy-the-dip

# Custom configuration
poetry run buy-the-dip --config my_config.yaml

# Validate configuration
poetry run buy-the-dip --config my_config.yaml --validate-config

# Generate performance report
poetry run buy-the-dip --report

# Get help
poetry run buy-the-dip --help
```

### Key Configuration Parameters
```yaml
ticker: "SPY"                    # What to monitor
rolling_window_days: 90          # Sensitivity period
percentage_trigger: 0.90         # When to buy (90% = 10% drop)
monthly_dca_amount: 2000.0       # How much to invest
data_cache_days: 30              # Cache duration
```

### Pre-built Strategies
- **Conservative**: 15% drops, $1K/month, stable
- **Balanced**: 8% drops, $2K/month, moderate
- **Aggressive**: 5% drops, $3K/month, frequent
- **Individual Stock**: 12% drops, single company
- **Dividend Focused**: 11% drops, income-oriented
- **Small Cap**: 13% drops, growth-focused
- **Crypto ETF**: 18% drops, high volatility

## 📞 Getting Help

### Documentation Issues
If you find errors or gaps in the documentation:
1. Check if there's a more recent version
2. Look for related information in other docs
3. Create an issue on the project repository

### Usage Questions
1. Start with **[QUICKSTART.md](QUICKSTART.md)**
2. Check **[EXAMPLES.md](EXAMPLES.md)** for similar scenarios
3. Review **[CONFIGURATION_GUIDE.md](CONFIGURATION_GUIDE.md)** for parameters
4. Use `--help` flag for command-line options

### Technical Issues
1. Check **[INSTALLATION.md](INSTALLATION.md)** troubleshooting section
2. Validate your configuration with `--validate-config`
3. Review error messages carefully
4. Check internet connection for data fetching issues

## 🚨 Important Reminders

- **Educational Tool**: This is a simulation for learning purposes
- **No Real Trading**: No actual money or trades are involved
- **Risk Awareness**: All investments carry risk of loss
- **Professional Advice**: Consult financial advisors for real investments
- **Backtesting Limitations**: Past performance doesn't guarantee future results

---

**Need to get started quickly?** → [QUICKSTART.md](QUICKSTART.md)  
**Want comprehensive setup?** → [INSTALLATION.md](INSTALLATION.md)  
**Need configuration help?** → [CONFIGURATION_GUIDE.md](CONFIGURATION_GUIDE.md)  
**Looking for examples?** → [EXAMPLES.md](EXAMPLES.md)