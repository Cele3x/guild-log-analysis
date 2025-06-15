# Plots Directory

This directory contains generated plot images from the analysis. The registry-based system automatically generates plots for all registered boss analyses.

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

1. **Automatic Plot Creation**: Each boss analysis defines `PLOT_CONFIG`
2. **Consistent Styling**: All plots use the same base styling and color schemes
3. **Format Configuration**: Plot DPI and format can be configured:
   ```python
   plot.save("filename.png", dpi=300)
   ```
4. **Dynamic Naming**: File names are automatically generated based on plot titles and dates

## Adding New Plot Types

New boss analyses automatically generate plots based on their `PLOT_CONFIG`:

```python
PLOT_CONFIG = [
    {
        "analysis_name": "Boss Interrupts",
        "plot_type": "NumberPlot",  # or "PercentagePlot"
        "title": "Boss Interrupts",
        "value_column": "interrupts",
        "value_column_name": "Count",
    }
]
```
