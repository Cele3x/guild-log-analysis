# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.1.0] - 2025-06-22

### Added
- **Totals Row Feature**: Added configurable totals/averages row at bottom of all plots
- **Smart Totals Calculation**: NumberPlot shows sum totals, PercentagePlot shows averages
- **Dynamic Labels**: "Total" for number plots, "Average" for percentage plots
- **Change Indicators**: Totals row displays change from previous data with color coding
- **Comprehensive Tests**: Added 14 new tests covering all totals functionality
- **Visual Separator**: Red line above totals row for clear visual distinction
- **Role-based Filtering**: Added role filtering system for analyses and plots
- **Role Constants**: Added PlayerRoles class with TANK, HEALER, DPS constants
- **Enhanced GraphQL Queries**: Improved query structure and empty data validation
- **HitCountPlot**: New specialized plot type for displaying hit count data with damage values
- **Damage Taken Analysis**: Added `damage_taken_from_ability` analysis type using GraphQL DamageTaken queries
- **Hit Count Metrics**: Support for both hit count and total damage data from API responses
- **Dual Column Display**: HitCountPlot shows hit count as primary metric with damage in separate column

### Changed
- **Plot Layout**: Adjusted spacing and positioning for optimal totals row integration
- **Figure Height**: Automatically accounts for totals row in plot dimensions
- **Type Support**: Enhanced change calculation to handle numpy numeric types
- **Method Signatures**: Cleaned up unused parameters in totals-related methods
- **Duration-based Calculations**: Replaced fight count dependencies with total fight duration metrics
- **Change Calculations**: Enhanced precision for duration-based change calculations with scaled formatting
- **Analysis Architecture**: Updated base analysis to support role filtering in configurations
- **Plot System**: Streamlined to use exclusively duration-based metrics for more accurate comparisons
- **GraphQL Parameters**: Fixed ability ID parameter type from Int! to Float! for damage taken queries
- **One-Armed Bandit Config**: Updated to use HitCountPlot for damage taken analyses

### Fixed
- **Change Calculation**: Fixed "N/A" issue for NumberPlot totals (numpy type handling)
- **Plot Spacing**: Eliminated gaps between header/data rows and data rows/totals
- **Title Positioning**: Optimized spacing between title/subtitle and header row
- **Duration Tracking**: Eliminated fight count parameters throughout plotting system
- **Test Suite**: Updated all tests to use duration parameters instead of fight counts
- **Duplicate Player Handling**: Fixed value doubling for players who switch roles between attempts
- **HitCountPlot Layout**: Fixed damage column positioning to appear right of value bar instead of overlapping

### Technical Details
- Totals row enabled by default with `show_totals=True` parameter
- No value bar displayed in totals row for cleaner appearance
- Proper handling of missing previous data (returns 0 for NumberPlot, None for PercentagePlot)
- Added regression tests for numpy type compatibility
- Role filtering applies to both analysis data collection and plot generation
- Duration-based change calculations provide per-minute rate comparisons
- Enhanced change formatting with 3 decimal places for small values
- Comprehensive test coverage for role filtering functionality
- HitCountPlot uses maximum values instead of sum for duplicate player handling
- Damage taken queries use dataType: DamageTaken with abilityID parameter
- HitCountPlot inherits from BaseTablePlot with minimal method overrides
- Custom 5-column layout for HitCountPlot: Name, Hit Count Value, Hit Count Bar, Damage, Change

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
