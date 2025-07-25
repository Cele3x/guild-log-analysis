# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.5.0] - 2025-07-16

### Added
- **Polarization Blast Hits Analysis**: New custom analysis type for counting damage events with 10-second hit grouping to avoid double-counting rapid hits
- **Spell Data Configuration**: Added comprehensive spell data system in `spells.yaml` with defensive cooldowns, healing abilities, and raid-wide defensive abilities organized by class
- **Test Infrastructure**: Complete test directory restructure with centralized output management, fixtures, and comprehensive documentation

### Enhanced
- **GraphQL Query Optimization**: Replaced manual death event counting with native `wipeCutoff` parameter for better performance and server-side filtering
- **Code Reuse**: Eliminated custom player name queries in favor of base class implementation, reducing code duplication
- **Sprocketmonger Lockenstock Analysis**: Enhanced boss configuration with Wire Transfer analysis and improved German descriptions

### Fixed
- **API Efficiency**: Removed redundant death event queries by leveraging GraphQL `wipeCutoff` parameter with default value of 4 deaths
- **Memory Usage**: Simplified player name resolution using existing base class data instead of additional API calls

### Refactoring
- **Tests Organization**: Restructured tests folder with proper output isolation, removed duplicate nested directories, and cleaned up scattered plot files
- **Performance**: Streamlined custom analysis methods by removing ~100 lines of manual timestamp tracking code
- **GraphQL Queries**: Consolidated event filtering logic into server-side parameters for better performance

### Documentation
- **Test Structure**: Added comprehensive README files documenting test organization, output directories, and best practices
- **Spell System**: Documented spell data format and usage patterns for future defensive cooldown analysis

### Technical Details
- Custom analysis methods now use `DEFAULT_WIPE_CUTOFF` (4 deaths) when no cutoff specified
- GraphQL queries handle wipe cutoff filtering server-side instead of client-side timestamp comparison
- Test outputs now properly isolated in `tests/output/` with automatic directory creation
- Removed date-named plot folders and duplicate test structures
- Enhanced pre-commit configuration with comprehensive code quality checks

## [2.4.1] - 2025-07-14

### Fixed
- **Parameter Ordering**: Fixed critical runtime error "string indices must be integers, not 'str'" by correcting parameter order in `_execute_analysis` method calls
- **Universal Normalization**: Removed incorrect universal duration normalization from main data columns, keeping only change-specific normalization
- **Table Data Analysis**: Fixed participant-based filtering to eliminate duplicate characters and ensure consistent data processing
- **Deaths Data Processing**: Corrected Deaths data type handling to properly count individual death events

### Refactoring
- **Analysis Method Consolidation**: Replaced specialized methods (`analyze_player_deaths`, `analyze_debuff_uptime`, `analyze_damage_taken_from_ability`) with unified `analyze_table_data` method
- **Code Reduction**: Removed ~400 lines of duplicate code through method consolidation
- **API Consistency**: Standardized table-based analysis interface across all data types

### Enhanced
- **Documentation**: Updated CLAUDE.md with unified analysis method documentation and legacy configuration migration guide
- **Error Prevention**: Improved participant-based data filtering to prevent duplicates and inconsistent results

### Technical Details
- Legacy analysis types automatically converted to unified `table_data` approach
- Participant-based filtering ensures data consistency across all analysis types
- Deaths data type now correctly processes individual death events
- Normalized parameter ordering prevents runtime errors in analysis execution

## [2.4.0] - 2025-07-13

### Added
- **Player Deaths Analysis**: New `player_deaths` analysis type with table-based queries for efficiency
- **Table Data Analysis**: Generic `table_data` analysis type for flexible data retrieval
- **Wrong Mine Analysis**: Specialized `wrong_mine_analysis` for correlating debuffs with damage events
- **Sprocketmonger Lockenstock Boss**: Complete boss analysis implementation with wrong mine trigger tracking

### Fixed
- **Duplicate Players**: Fixed players appearing twice in analyses when switching roles during encounters
- **Death Cutoff**: Ensured all analysis queries use 4 deaths cutoff by default for consistent behavior
- **Table Query Support**: Added wipeCutoff parameter to table data queries for proper wipe filtering

### Enhanced
- **Code Formatting**: Applied comprehensive code reformatting following PEP 8 standards
- **Documentation**: Updated CLAUDE.md with player_deaths analysis type documentation
- **Error Handling**: Improved null checks and defensive programming throughout base analysis
- **Query Optimization**: Added ability filtering for player deaths with optional ability_id parameter

### Technical Details
- Player deaths analysis uses table queries instead of events for better performance
- Wrong mine analysis correlates Unstable Shrapnel debuffs with Polarized Catastro-Blast damage
- Table data analysis supports multiple data types (Debuffs, DamageTaken, Deaths)
- Enhanced correlation window and minimum victims threshold configuration
- Player deduplication prevents duplicate entries for role-switching players
- Default kill_type changed from "Encounters" to "Wipes" for table data queries

## [2.3.0] - 2025-07-07

### Added
- **Command-Line Interface**: New `guild-analyze` CLI command with comprehensive argument support
- **Progress Plots**: Multi-line plots showing player metrics trends over time with role categorization
- **CLI Script**: Standalone `scripts/analyze` script for direct execution
- **Multi-line Plot Module**: Complete visualization system for tracking progression across multiple reports
- **CLI Documentation**: Comprehensive CLI_USAGE.md with examples and usage patterns

### Enhanced
- **Plot Organization**: Regular plots saved to dated subdirectories (output/YYYY-MM-DD/)
- **Progress Plot Features**: Duration normalization, role-based categorization, class-colored lines
- **Test Suite**: Optimized test coverage from 74% to 78% with comprehensive CLI tests
- **Configuration Management**: Enhanced settings with player categorization support

### Fixed
- **Empty Graph Issue**: Resolved empty progress plots for inappropriate role combinations
- **GitIgnore Update**: Updated patterns to match new output directory structure
- **Test Optimization**: Removed obsolete tests and improved mock patterns for better stability

### CLI Features
- **Boss Selection**: `--list-bosses` to show available encounters
- **Progress Control**: `--progress-plots` flag to enable trend visualization (disabled by default)
- **Output Control**: Configurable output directory with `--output-dir`
- **Logging Control**: Verbose (`--verbose`) and debug (`--debug`) logging options
- **Authentication**: Automatic .env file integration for API credentials

### Technical Details
- Progress plots support role categories: tanks_healers, melee_dps, ranged_dps
- Duration normalization for cross-report comparison (per-hour metrics)
- Comprehensive CLI argument validation and error handling
- Organized output structure with separate directories for regular and progress plots
- Enhanced test isolation and coverage optimization

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
