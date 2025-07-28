# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2025-07-28

### Added
- Comprehensive test suite with 15 unit tests covering core functionality
- Modern Python packaging with pyproject.toml
- GitHub Actions CI/CD workflow for automated testing (Python 3.10-3.12)
- Pre-commit hooks configuration for code quality
- Development documentation (CONTRIBUTING.md)
- Example usage script (example.py) demonstrating programmatic usage
- Type hints for better code quality and IDE support
- Comprehensive .gitignore for Python projects

### Fixed
- All PEP 8 linting errors (7 issues resolved)
- Missing newlines at end of files
- Unused variables and imports
- Proper error handling in log loading functions

### Changed
- Enhanced README with clearer installation and development instructions
- Improved project structure and organization
- Better error handling in core functions

### Removed
- Redundant helpers.py file (functionality consolidated into crpm modules)

### Technical Improvements
- All code now passes flake8 linting
- 100% test success rate across all unit tests
- Backward compatibility maintained for existing functionality
- Enhanced developer experience with pre-commit hooks and CI/CD
