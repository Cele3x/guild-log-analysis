# Plots Directory

This directory contains generated plot images from the analysis.

## Plot Types

**One-Armed Bandit Analysis Plots:**
- **Overload! Interrupts** - Player interrupt performance for Overload! ability
- **High Roller Uptime** - Debuff uptime percentages for High Roller
- **Premium Dynamite Booties Damage** - Damage to Premium Dynamite Booties (Geschenke)
- **Reel Assistants Damage** - Damage to Reel Assistants
- **Boss Damage** - Damage to the One-Armed Bandit boss
- **Absorbed Damage to Reel Assistants** - Absorbed damage analysis

## File Naming

Plots are automatically generated with date prefix and descriptive names:
- `2025-01-15_overload_interrupts.png`
- `2025-01-15_high_roller_uptime.png`
- `2025-01-15_schaden_auf_geschenke.png`
- `2025-01-15_schaden_auf_reel_assistants.png`
- `2025-01-15_schaden_auf_boss.png`
- `2025-01-15_absorbierter_schaden_auf_reel_assistants.png`

## Configuration

Plot DPI and format can be configured:

```python
plot.save("filename.png", dpi=300)
```
