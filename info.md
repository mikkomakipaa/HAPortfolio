# Portfolio Tracker Integration

Transform your investment tracking with seamless Google Sheets and InfluxDB integration.

## Quick Setup

1. **Prerequisites**: Configure Google Drive integration in HA
2. **Install**: Add through HACS or manually
3. **Configure**: Provide InfluxDB credentials and Google Sheets ID
4. **Track**: Monitor real-time portfolio metrics

## Key Features

- 📊 **Google Sheets Sync**: Uses HA's Google Drive authentication
- 📈 **InfluxDB Integration**: Compatible with HA Add-on (v1)
- ⚡ **Real-time Data**: Auto-sync from sheets to database to sensors
- 🔍 **Health Monitoring**: Binary sensors track all connections
- 📊 **Analytics**: Portfolio performance analysis services

## Entities Created

- Portfolio Value sensor
- Daily Change ($ and %) sensors  
- Position count sensor
- Connectivity binary sensors
- Last update timestamp

## Services Available

- Manual sync from Google Sheets
- Portfolio analytics (configurable days)
- System health status check

Perfect for investors who want to track their portfolio performance directly in Home Assistant!
