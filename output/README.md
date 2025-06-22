# Output Directory

This directory contains generated plot images and analysis output. The registry-based system automatically generates plots for all registered boss analyses.

## Plot Types

**One-Armed Bandit Analysis Plots:**
- **Overload! Interrupts** - Player interrupt performance for Overload! ability
- **High Roller Uptime** - Debuff uptime percentages for High Roller
- **Premium Dynamite Booties Damage** - Damage to Premium Dynamite Booties (Geschenke)
- **Reel Assistants Damage** - Damage to Reel Assistants
- **Boss Damage** - Damage to the One-Armed Bandit boss
- **Absorbed Damage to Reel Assistants** - Absorbed damage analysis

**Additional Boss Analyses:**
- New boss analyses automatically generate their configured plots
- Plot types include NumberPlot and PercentagePlot
- All plots follow consistent styling and formatting

## File Naming

Plots are automatically generated with date prefix and descriptive names:
- `2025-01-15_overload_interrupts.png`
- `2025-01-15_high_roller_uptime.png`
- `2025-01-15_schaden_auf_geschenke.png`
- `2025-01-15_schaden_auf_reel_assistants.png`
- `2025-01-15_schaden_auf_boss.png`
- `2025-01-15_absorbierter_schaden_auf_reel_assistants.png`

## Plot Generation

Plots are automatically generated through the registry-based system:

1. **Unified Configuration**: Each boss analysis defines a single `CONFIG` with both analysis and plot settings
2. **Consistent Styling**: All plots use the same base styling and color schemes
3. **Format Configuration**: Plot DPI and format can be configured:
   ```python
   plot.save("filename.png", dpi=300)
   ```
4. **Dynamic Naming**: File names are automatically generated based on plot titles and dates

## Adding New Plot Types

New boss analyses automatically generate plots based on their unified `CONFIG`:

```python
CONFIG = [
    {
        "name": "Boss Interrupts",
        "analysis": {
            "type": "interrupts",
            "ability_id": 12345,
        },
        "plot": {
            "type": "NumberPlot",  # or "PercentagePlot", "HitCountPlot"
            "title": "Boss Interrupts",
            "column_key_1": "interrupts",
            "column_header_1": "Name",      # Optional: Column 1 header (defaults to "Name")
            "column_header_2": "Count",     # Optional: Column 2 header
            "column_header_3": "Details",   # Optional: Column 3 header (for bar visualization)
        }
    }
]
```

### Column Header System

The plotting system supports up to 3 columns with optional headers:

- **column_header_1**: Name column header (defaults to "Name" if not specified)
- **column_header_2**: Value column header (displayed above the numeric value)
- **column_header_3**: Bar column header (displayed above the visualization bar)

All column headers are optional. If not provided, the column will have no header text.
