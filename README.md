# pH Control for Home Assistant

This integration analyzes pH oscillation patterns in pool or aquarium pH control systems to predict alkalinity depletion.

## Features

- Detects pH oscillations around a setpoint (typically 8.2 for pools)
- Tracks oscillation amplitude, frequency, and trends
- Predicts alkalinity depletion based on increasing oscillation patterns
- Provides alkalinity status (normal, decreasing, low)

## Installation

### HACS Installation

1. Open HACS in your Home Assistant instance
2. Click on "Integrations"
3. Click the three dots in the top right corner
4. Select "Custom repositories"
5. Add the URL to this repository
6. Select "Integration" as the category
7. Click "Add"
8. Find "pH Control" in the list of integrations and install it
9. Restart Home Assistant

### Manual Installation

1. Copy the `custom_components/ph_control` directory to your Home Assistant `custom_components` directory
2. Restart Home Assistant

## Configuration

1. Go to Settings -> Devices & Services
2. Click "Add Integration"
3. Search for "pH Control"
4. Follow the configuration steps:
   - Select your pH sensor entity
   - Configure the desired setpoint (default 8.2)
   - Adjust sensitivity parameters if needed

## Usage

The integration creates a new sensor that provides:

- Current oscillation amplitude trend
- Alkalinity status (normal, decreasing, low)
- Number of oscillations in the last 24 hours
- Average and maximum oscillation amplitude
