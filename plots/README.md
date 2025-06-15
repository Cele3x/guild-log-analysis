# Plots Directory

This directory contains generated plot images from the analysis.

## Plot Types

- **Interrupt Plots** - Player interrupt performance
- **Uptime Plots** - Debuff uptime percentages  
- **Damage Plots** - Damage to specific targets

## File Naming

Plots are typically saved with descriptive names:
- `overload_interrupts_2024-01-01.png`
- `high_roller_uptime_2024-01-01.png`
- `dynamite_damage_2024-01-01.png`

## Configuration

Plot DPI and format can be configured:

```python
plot.save("filename.png", dpi=300)
```

