# Contributing to CRPM

Thank you for your interest in contributing to CRPM! This document provides guidelines for contributing to the project.

## Development Setup

1. **Fork and clone the repository**:
   ```bash
   git clone https://github.com/YOUR_USERNAME/CRPM.git
   cd CRPM
   ```

2. **Set up the development environment**:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   pip install -e ".[dev]"
   ```

3. **Install pre-commit hooks** (recommended):
   ```bash
   pre-commit install
   ```

## Code Quality Standards

### Linting and Formatting
- Use `flake8` for linting (max line length: 100)
- Use `black` for code formatting (optional but recommended)
- All code must pass the existing flake8 configuration

### Testing
- Write unit tests for new functionality in the `tests/` directory
- Ensure all tests pass: `python -m unittest discover tests -v`
- Aim for good test coverage of core functionality

### Type Hints
- Add type hints to new functions and methods
- Use `from __future__ import annotations` for forward references
- Import types from `typing` module when needed

## Contribution Workflow

1. **Create a feature branch**:
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes**:
   - Write clean, well-documented code
   - Add tests for new functionality
   - Update documentation if needed

3. **Run quality checks**:
   ```bash
   # Lint the code
   flake8 .
   
   # Run tests
   python -m unittest discover tests -v
   
   # Test basic functionality
   python example.py
   ```

4. **Commit your changes**:
   ```bash
   git add .
   git commit -m "feat: describe your changes"
   ```

5. **Push and create a pull request**:
   ```bash
   git push origin feature/your-feature-name
   ```

## Code Style Guidelines

- Follow PEP 8 style guidelines
- Use descriptive variable and function names
- Add docstrings to public functions and classes
- Keep functions focused and single-purpose
- Use pathlib.Path for file operations

## Project Structure

```
CRPM/
├── crpm/                 # Core library modules
│   ├── __init__.py      # Package initialization
│   ├── conformance.py   # Process discovery and conformance checking
│   └── pipeline.py      # High-level pipeline utilities
├── tests/               # Unit tests
├── app.py              # Basic Streamlit app
├── pipeline_app.py     # Full pipeline Streamlit app
├── example.py          # Usage example
└── requirements.txt    # Dependencies
```

## Reporting Issues

When reporting bugs or requesting features:

1. Use the GitHub issue tracker
2. Provide a clear description of the problem or enhancement
3. Include steps to reproduce (for bugs)
4. Specify your Python version and operating system
5. Include relevant error messages or logs

## Types of Contributions

We welcome various types of contributions:

- **Bug fixes**: Help us fix issues in the codebase
- **New features**: Add new process mining capabilities
- **Documentation**: Improve README, docstrings, or examples
- **Tests**: Add or improve test coverage
- **Performance**: Optimize existing functionality
- **Streamlit UI**: Enhance the web interface

## Getting Help

If you need help with development:

- Check existing issues and discussions
- Ask questions in new GitHub issues
- Review the example.py script for usage patterns
- Look at existing tests for code patterns

Thank you for contributing to CRPM!
