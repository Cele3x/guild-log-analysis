# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.2.0] - 2025-06-27

### Added
- **Unified Configuration System**: Single CONFIG array replaces separate ANALYSIS_CONFIG and PLOT_CONFIG
- **Enhanced Column System**: Support for up to 5 data columns with configurable headers
- **Test Output Management**: Isolated test environment with plots/cache/logs in tests/ directory
- **Wipe Cutoff Configuration**: Configurable wipe_cutoff parameter for analysis types
- **Example Boss Testing**: Comprehensive test coverage for all analysis and plot variations

### Changed
- **BREAKING**: Migrated from ANALYSIS_CONFIG/PLOT_CONFIG to unified CONFIG structure
- **Environment Variables**: Simplified .env format (CLIENT_ID, REDIRECT_URI instead of WOW_ prefixes)
- **Column Configuration**: New column_key_1/column_header_1 system replaces value_column/value_column_name
- **Plot Generation**: Enhanced plot parameter handling with flexible column system
- **Analysis Architecture**: Improved type handling and GraphQL parameter consistency

### Fixed
- **Documentation Cleanup**: Removed outdated plots/README.md file
- **Type Consistency**: Standardized ability_id parameters as float values in GraphQL queries
- **Configuration Migration**: Updated all boss analyses to use unified CONFIG format

### Technical Details
- CONFIG entries combine analysis and plot configurations in single objects
- Automatic result key generation from analysis names using snake_case conversion
- Test isolation prevents output files from mixing with production data
- Enhanced documentation in CLAUDE.md with comprehensive testing guidelines
- Support for complex filter expressions and role-based analysis configurations

## [2.1.0] - 2025-06-22

### Added
- **Totals Row Feature**: Added configurable totals/averages row at bottom of all plots
- **Smart Totals Calculation**: NumberPlot shows sum totals, PercentagePlot shows averages
- **Role-based Filtering**: Added role filtering system for analyses and plots
- **HitCountPlot**: New specialized plot type for displaying hit count data with damage values
- **Damage Taken Analysis**: Added `damage_taken_from_ability` analysis type using GraphQL DamageTaken queries

### Changed
- **Duration-based Calculations**: Replaced fight count dependencies with total fight duration metrics
- **Analysis Architecture**: Updated base analysis to support role filtering in configurations
- **GraphQL Parameters**: Fixed ability ID parameter type from Int! to Float! for damage taken queries

### Fixed
- **Change Calculation**: Fixed "N/A" issue for NumberPlot totals (numpy type handling)
- **Duplicate Player Handling**: Fixed value doubling for players who switch roles between attempts
- **HitCountPlot Layout**: Fixed damage column positioning to appear right of value bar instead of overlapping

## [2.0.0] - 2025-06-15

### Added
- **Registry-based Analysis System**: Decorator-based boss registration system
- **Configuration-driven Architecture**: Boss analyses now use ANALYSIS_CONFIG and PLOT_CONFIG arrays
- **Auto-registration**: GuildLogAnalyzer automatically generates methods for registered bosses
- **Enhanced Test Suite**: Comprehensive tests for registry and configuration systems
- **Improved Documentation**: Updated README, CONTRIBUTING, and component-specific docs
- **Virtual Environment Setup**: Configured development environment with convenience aliases
- **Version Management Guidelines**: Comprehensive changelog and semantic versioning documentation

### Changed
- **BREAKING**: Converted OneArmedBanditAnalysis to configuration-based implementation
- **Architecture**: Reduced boilerplate code by 90% for new boss implementations
- **Code Generation**: Dynamic method creation at runtime for registered bosses
- **Base Class**: Enhanced BossAnalysisBase with generic analysis execution methods
- **Type Hints**: Migrated from `Dict`, `List`, `Set`, `Tuple` to modern `dict`, `list`, `set`, `tuple`
- **Development Workflow**: Added virtual environment aliases and convenience scripts

### Fixed
- IDE warnings for unresolved setuptools references
- Type checking issues with modern Python 3.13 type hints
- Virtual environment dependency management

### Features
- **Minimal Boilerplate**: New boss analyses require only configuration, not hundreds of lines
- **Automatic Discovery**: Boss analyses automatically registered via @register_boss decorator
- **Configuration-based**: Define analyses through structured configuration arrays
- **Runtime Generation**: analyze_<boss>() and generate_<boss>_plots() methods created automatically
- **Backward Compatible**: Legacy analysis methods continue to work
- **Modern Type System**: Built-in type hints for Python 3.9+ compatibility

### Technical Details
- Registry system with decorator pattern implementation
- Generic analysis execution framework
- Configuration-driven plot generation
- Enhanced type safety with comprehensive test coverage
- Factory pattern for analysis creation
- Virtual environment at `/home/jonathan/.virtualenvs/guild-log-analysis`
- Modern Python type annotations throughout codebase
- Comprehensive CHANGELOG.md update guidelines

## [1.0.0] - 2025-06-13

### Added
- Initial release of WoW Guild Analysis
- One-Armed Bandit boss analysis implementation
- Overload! interrupt tracking
- High Roller debuff uptime analysis
- Premium Dynamite Booties damage tracking
- Warcraft Logs API client with OAuth authentication
- Intelligent caching system with rate limiting
- Beautiful table-style plots with class colors
- Comprehensive test suite with unit and integration tests
- Modern Python packaging with pyproject.toml
- Development tools configuration (black, isort, flake8, mypy)
- Pre-commit hooks for code quality
- Detailed documentation and README

### Features
- **Modular Architecture**: Easy to extend with new boss analyses
- **Performance Optimized**: Caching and rate limiting for API efficiency
- **Professional Visualizations**: Class-colored bars with change indicators
- **Type Safety**: Full type hints throughout the codebase
- **Comprehensive Testing**: Unit and integration tests with high coverage
- **Developer Friendly**: Modern tooling and clear documentation

### Technical Details
- Python 3.13 support
- Pandas for data manipulation
- Matplotlib for plotting
- Requests for HTTP client
- Pytest for testing
- Black for code formatting
- MyPy for type checking

## [Unreleased]

### Planned
- Additional boss analysis implementations
- Web interface for analysis results
- Export functionality for reports
- Performance metrics dashboard
- Guild comparison features
