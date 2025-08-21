# Portfolio Tracker for Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/custom-components/hacs)
[![GitHub release](https://img.shields.io/github/release/mikkomakipaa/HAPortfolio.svg)](https://github.com/mikkomakipaa/HAPortfolio/releases)

A comprehensive Home Assistant custom integration for tracking investment portfolios with Google Sheets and InfluxDB integration.

## Features

- **📊 Google Sheets Integration**: Sync portfolio data using HA's Google Drive authentication
- **📈 InfluxDB v1 Support**: Compatible with Home Assistant InfluxDB Add-on
- **⚡ Real-time Monitoring**: Track portfolio value, daily changes, and positions
- **🔍 Binary Sensors**: Monitor connectivity status for all data sources
- **📊 Analytics Services**: Run portfolio analytics and system health checks
- **🔄 Auto-sync**: Configurable automatic synchronization from Google Sheets

## Data Flow

```
Google Sheets → Integration → InfluxDB → Home Assistant Sensors
```

1. **Google Sheets** contains your portfolio positions (symbols, quantities, prices)
2. **Integration** fetches data using HA's existing Google Drive authentication
3. **InfluxDB** stores processed portfolio metrics and historical data
4. **Home Assistant Sensors** display real-time portfolio values and changes

## Requirements

- Home Assistant 2023.1.0 or newer
- InfluxDB v1 (Home Assistant Add-on recommended)
- Google Drive integration configured in Home Assistant
- Google Sheets document with portfolio data

## Installation

### Via HACS (Recommended)

1. Add this repository to HACS as a custom repository
2. Install "Portfolio Tracker" through HACS
3. Restart Home Assistant

### Manual Installation

1. Copy `custom_components/portfolio_tracker` to your HA `custom_components` directory
2. Restart Home Assistant

## Configuration

### Prerequisites

1. **Configure Google Drive Integration** in Home Assistant first
2. **Install InfluxDB Add-on** or have InfluxDB v1 running
3. **Prepare Google Sheets** with your portfolio data

### Setup Steps

1. Go to Settings → Integrations
2. Click "Add Integration" and search for "Portfolio Tracker"
3. Provide the following information:
   - **InfluxDB URL**: Your InfluxDB instance URL (default: `http://homeassistant.local:8086`)
   - **Username/Password**: InfluxDB v1 credentials
   - **Database**: InfluxDB database name (default: `portfolio`)
   - **Google Sheets ID**: ID from your Google Sheets URL
   - **Auto-sync**: Enable automatic data synchronization (recommended)

### Google Sheets Format

Your Google Sheets should have headers like:

| symbol | quantity | price | value | change |
|--------|----------|-------|-------|--------|
| AAPL   | 10       | 150   | 1500  | 5.2    |
| GOOGL  | 5        | 2800  | 14000 | -12.5  |

## Entities

### Sensors

- **Portfolio Value**: Total portfolio value in USD
- **Daily Change**: Daily change in USD
- **Daily Change Percent**: Daily change percentage
- **Total Positions**: Number of positions in portfolio
- **Last Update**: Timestamp of last data update

### Binary Sensors

- **Data Source Health**: Overall health of data sources
- **InfluxDB Connected**: InfluxDB connectivity status
- **Google Sheets Connected**: Google Sheets connectivity status

## Services

### `portfolio_tracker.update_data`
Manually sync portfolio data from Google Sheets to InfluxDB

### `portfolio_tracker.run_analytics`
Generate portfolio analytics for specified number of days

**Parameters:**
- `days` (optional): Number of days to analyze (default: 30)

### `portfolio_tracker.get_status`
Get current portfolio system status and health information

## Automation Examples

### Daily Portfolio Report
```yaml
automation:
  - alias: "Daily Portfolio Report"
    trigger:
      platform: time
      at: "09:00:00"
    action:
      - service: portfolio_tracker.update_data
      - delay: "00:00:30"
      - service: notify.mobile_app
        data:
          title: "Portfolio Update"
          message: >
            Portfolio Value: ${{ states('sensor.portfolio_value') }}
            Daily Change: {{ states('sensor.daily_change_percent') }}%
```

### Portfolio Alert
```yaml
automation:
  - alias: "Portfolio Loss Alert"
    trigger:
      platform: numeric_state
      entity_id: sensor.daily_change_percent
      below: -5
    action:
      - service: notify.mobile_app
        data:
          title: "Portfolio Alert"
          message: "Portfolio down {{ states('sensor.daily_change_percent') }}% today"
```

## Troubleshooting

### Common Issues

1. **Google Sheets not connecting**:
   - Ensure Google Drive integration is configured in HA
   - Check that the Google Sheets ID is correct
   - Verify the Google Sheets is accessible

2. **InfluxDB connection failed**:
   - Check InfluxDB Add-on is running
   - Verify username/password for InfluxDB v1
   - Ensure database exists

3. **No data in sensors**:
   - Check binary sensors for connectivity status
   - Run manual sync: `portfolio_tracker.update_data`
   - Check Home Assistant logs for errors

### Debug Logging

Add to `configuration.yaml`:
```yaml
logger:
  logs:
    custom_components.portfolio_tracker: debug
```

## Contributing

Issues and pull requests are welcome on [GitHub](https://github.com/mikkomakipaa/HAPortfolio).

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Changelog

### v1.3.0
- Added Google Drive authentication integration
- Implemented complete Google Sheets → InfluxDB → Sensors data flow
- Added auto-sync configuration option
- Enhanced binary sensors for connectivity monitoring
- Improved error handling and logging

### v1.2.0
- InfluxDB v1 compatibility for HA Add-on
- Binary sensor platform
- Enhanced configuration flow

### v1.1.0
- Initial Google Sheets support
- Portfolio analytics services
- HACS compatibility

### v1.0.0
- Initial release
- Basic InfluxDB integration
- Core portfolio sensors
