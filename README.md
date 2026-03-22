# Brooklyn Bridge Tourist Loop

Interactive visualization exploring directional pedestrian flow patterns on the Brooklyn Bridge (2017-2019).

**Live Demo:** [View Interactive Visualization](https://alogailia.github.io/brooklyn-bridge-interactive/)

## Key Finding

The Brooklyn Bridge exhibits a daily "tourist loop" where pedestrian flow reverses direction mid-day:
- **Morning:** More people walk toward Manhattan
- **Afternoon:** Flow reverses toward Brooklyn

## Features

- Filter by day type, season, weather, and year
- Toggle between mean values and variation (IQR bands)
- Year-on-year stability comparison
- Interactive tooltips on all data points

## Running Locally

```bash
pip install -r requirements.txt
panel serve brooklyn_bridge_interactive.py --show
```

## Project

This interactive dashboard was created as one of my projects in the course Information Visualization.
