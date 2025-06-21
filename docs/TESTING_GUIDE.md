# Testing Guide for YouTube Transcriber

## Overview

This guide provides comprehensive instructions for testing the YouTube Transcriber application. The test suite includes unit tests, integration tests, end-to-end tests, and performance tests.

## Test Structure

```
tests/
├── conftest.py              # Shared fixtures and test configuration
├── unit/                    # Unit tests for individual components
├── integration/             # Integration tests
│   ├── test_processing_statistics.py
│   ├── test_e2e_scenarios.py
│   └── test_performance.py
└── fixtures/                # Test data and mock responses
```

## Running Tests

### Prerequisites

1. Install test dependencies:
```bash
poetry install --with test
```

2. Set up test configuration:
```bash
cp config/config.sample.yaml config/config.test.yaml
# Edit config.test.yaml with test settings
```

### Running All Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test categories
pytest -m unit
pytest -m integration
pytest -m e2e
pytest -m performance
```

### Running Specific Tests

```bash
# Run a specific test file
pytest tests/integration/test_processing_statistics.py

# Run a specific test class
pytest tests/integration/test_e2e_scenarios.py::TestE2EScenarios

# Run a specific test method
pytest tests/integration/test_e2e_scenarios.py::TestE2EScenarios::test_successful_channel_processing_flow
```

## Test Categories

### 1. Unit Tests
- Test individual components in isolation
- Mock external dependencies
- Fast execution
- High code coverage

### 2. Integration Tests
- Test component interactions
- Verify ProcessingStatistics integration
- Test data flow between models
- Database integration (if applicable)

### 3. End-to-End Tests
- Complete workflow testing
- Real-world scenarios
- Error handling and recovery
- Multi-language support

### 4. Performance Tests
- Scalability testing
- Memory efficiency
- Processing speed benchmarks
- Stress testing

## Key Test Scenarios

### ProcessingStatistics Tests

1. **Automatic Statistics Update**
   - Verify statistics update when videos are added/modified
   - Test field validator functionality
   - Ensure legacy field compatibility

2. **Error Statistics Aggregation**
   - Test error type classification
   - Verify error counting and percentages
   - Test most common error identification

3. **Time Estimation**
   - Test estimated time remaining calculations
   - Verify processing rate calculations
   - Test average processing time updates

### End-to-End Scenarios

1. **Successful Channel Processing**
   - Complete workflow from start to finish
   - Verify all statistics are tracked correctly
   - Test progress reporting

2. **Error Recovery**
   - Test retry mechanisms
   - Verify error handling
   - Test partial success scenarios

3. **Large Channel Processing**
   - Test pagination handling
   - Verify performance with many videos
   - Test memory efficiency

4. **Multi-Language Support**
   - Test channels with multiple languages
   - Verify language-specific processing
   - Test transcript availability by language

## Test Data

### Sample Channel URLs
- `https://www.youtube.com/channel/UCXuqSBlHAE6Xw-yeJA0Tunw` - Valid channel
- `https://www.youtube.com/@mkbhd` - Channel with handle
- `https://www.youtube.com/channel/UC-invalid-channel-id` - Invalid channel

### Edge Cases
- Empty channels (no videos)
- Large channels (1000+ videos)
- Private/unlisted videos
- Videos without transcripts
- Network failures
- Rate limiting scenarios

## Performance Benchmarks

| Scenario | Videos | Expected Time | Success Rate |
|----------|--------|---------------|--------------|
| Small Channel | 10 | < 30s | > 95% |
| Medium Channel | 100 | < 5 min | > 90% |
| Large Channel | 500 | < 30 min | > 85% |
| Stress Test | 1000 | < 60 min | > 80% |

## Debugging Tests

### Verbose Output
```bash
pytest -v  # Verbose mode
pytest -vv # Very verbose mode
pytest -s  # Show print statements
```

### Debug Specific Failures
```bash
pytest --pdb  # Drop into debugger on failure
pytest --pdb-trace  # Drop into debugger at start of test
```

### Test Markers
```python
@pytest.mark.unit  # Unit test
@pytest.mark.integration  # Integration test
@pytest.mark.e2e  # End-to-end test
@pytest.mark.performance  # Performance test
@pytest.mark.slow  # Slow test (skip with -m "not slow")
@pytest.mark.external  # Requires external services
```

## Continuous Integration

### GitHub Actions Workflow
```yaml
name: Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - run: pip install poetry
      - run: poetry install --with test
      - run: poetry run pytest --cov=src
```

## Best Practices

1. **Test Independence**: Each test should be independent and not rely on others
2. **Clear Names**: Use descriptive test names that explain what is being tested
3. **Arrange-Act-Assert**: Follow the AAA pattern in test structure
4. **Mock External Services**: Don't make real API calls in tests
5. **Test Data Factories**: Use fixtures for consistent test data
6. **Performance Baselines**: Establish and monitor performance benchmarks

## Troubleshooting

### Common Issues

1. **Import Errors**
   - Ensure `PYTHONPATH` includes the project root
   - Check that all dependencies are installed

2. **Fixture Not Found**
   - Verify fixture is defined in conftest.py
   - Check fixture scope and dependencies

3. **Async Test Failures**
   - Use `@pytest.mark.asyncio` decorator
   - Ensure event loop is properly configured

4. **Performance Test Timeouts**
   - Increase timeout values for slow tests
   - Use `@pytest.mark.slow` and skip in CI if needed

## Contributing Tests

When adding new features:
1. Write tests first (TDD approach)
2. Ensure all edge cases are covered
3. Add integration tests for new components
4. Update this guide with new test scenarios
5. Maintain > 90% code coverage