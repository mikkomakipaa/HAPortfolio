# Portfolio Tracker Architecture

## Project Overview
The Portfolio Tracker is a Home Assistant custom integration (v1.3.0) that serves as a **data importer and basic monitoring system** for investment portfolios. It bridges Google Sheets (portfolio data source) with InfluxDB (data storage) to provide real-time portfolio metrics through Home Assistant sensors. **Advanced analytics and visualization are handled separately in Grafana** using the time-series data stored in InfluxDB.

## Core Architecture

### Data Flow Pipeline
```
Google Sheets → Portfolio Manager → InfluxDB → [Home Assistant Sensors + Grafana Analytics]
```

1. **Google Sheets** serves as the authoritative data source containing portfolio positions
2. **Portfolio Manager** orchestrates data synchronization and processing
3. **InfluxDB v1** stores time-series portfolio data for consumption by multiple systems
4. **Home Assistant Sensors** expose basic real-time portfolio values and status
5. **Grafana** (external) consumes InfluxDB data for advanced analytics and visualization
6. **Binary Sensors** monitor connectivity status of all data sources

### Component Architecture

#### Core Integration (`__init__.py`)
- **PortfolioDataUpdateCoordinator**: Manages data updates and coordinates between all components
- **Service Registration**: Handles manual operations (`update_data`, `get_status`) and basic analytics (`run_analytics`)
- **Auto-sync Functionality**: Automated Google Sheets → InfluxDB synchronization
- **Platform Management**: Coordinates sensor and binary sensor platforms

#### Portfolio Manager (`portfolio_manager.py`)
- **Central Orchestrator**: Core business logic for data import and synchronization
- **InfluxDB v1 Client**: Database connection management with connection pooling
- **Google Sheets Integration**: Data retrieval via Home Assistant's Google Drive authentication
- **Basic Analytics**: Simple performance calculations for Home Assistant sensors only
- **Data Transformation**: Converts between Google Sheets format and InfluxDB schema
- **Data Importer**: Primary responsibility is reliable data ingestion, not analysis

#### Sensor Platform (`sensor.py`)
- **Portfolio Value Sensor**: Total portfolio value (monetary with measurement state class)
- **Daily Change Sensors**: Basic absolute dollar and percentage change tracking
- **Position Count Sensor**: Number of active positions
- **Last Update Sensor**: Timestamp of most recent data update
- **Basic Data Exposure**: Makes essential portfolio data available to Home Assistant UI
- **Simple Metrics Only**: Complex analytics are delegated to Grafana

#### Binary Sensor Platform (`binary_sensor.py`)
- **Data Source Health**: Overall system connectivity status
- **InfluxDB Connectivity**: Database connection monitoring
- **Google Sheets Connectivity**: Sheet access status monitoring
- **System Health Indicator**: Aggregated health status

#### Google API Integration (`google_api.py`)
- **Authentication Leverage**: Uses Home Assistant's existing Google Drive integration
- **Sheet Access Management**: Handles Google Sheets API calls
- **Data Retrieval**: Fetches data from specified sheet ranges
- **Connection Status**: Monitors Google API connectivity

## Technical Architecture

### Dependencies & Integration Points
- **InfluxDB v1 Client** (`influxdb>=5.3.0,<6.0.0`): Direct database operations for time-series data
- **Google API Client** (`google-api-python-client>=2.0.0`): Sheet data access
- **Google Auth OAuth** (`google-auth-oauthlib>=0.8.0`): Authentication handling
- **Home Assistant Core**: Configuration flow, coordinator pattern, sensor platforms
- **HACS Compatible**: Installable via Home Assistant Community Store

### Data Models

#### InfluxDB Schema
```
Measurements:
├── portfolio
│   ├── total_value (float)
│   ├── position_count (int)
│   └── timestamp
└── positions
    ├── tags: symbol
    ├── quantity (float)
    ├── price (float)
    ├── value (float)
    ├── change (float)
    └── timestamp
```

#### Google Sheets Format
Expected columns: `symbol`, `quantity`, `price`, `value`, `change`
- First row contains headers
- Data rows contain individual position information
- Flexible column mapping supports variations

#### Sensor Data Structure
```python
{
    'portfolio_value': float,
    'daily_change': float,
    'daily_change_percent': float,
    'total_positions': int,
    'last_update': ISO timestamp,
    'positions': [position_objects],
    'data_sources': {
        'influxdb_connected': bool,
        'google_sheets_connected': bool
    }
}
```

### Configuration Management

#### Required Configuration
- **InfluxDB URL**: Database connection endpoint (default: `http://homeassistant.local:8086`)
- **InfluxDB Credentials**: Username, password, database name
- **Google Sheets ID**: Document identifier from Google Sheets URL
- **Update Interval**: Data refresh frequency (default: 30 minutes)
- **Auto-sync Setting**: Enable/disable automatic Google Sheets synchronization

#### Optional Configuration
- **Custom Database Name**: InfluxDB database (default: "portfolio")
- **Authentication Credentials**: Alternative Google API credentials path

## Operational Features

### Primary Function: Data Import & Basic Monitoring
- **Configurable Synchronization**: Automatic data imports every 30 minutes (configurable)
- **Live Data Ingestion**: Real-time data import with basic value calculations
- **Multi-source Validation**: Cross-validates data between Google Sheets and InfluxDB
- **Error Handling**: Graceful fallback to cached data during connection issues
- **Connection Monitoring**: Continuous health checks for all data sources
- **InfluxDB Data Storage**: Structured time-series data ready for external analytics tools

### Built-in Services

#### Basic Analytics (`run_analytics`)
- **Limited Historical Analysis**: Simple performance metrics over configurable day ranges (1-365 days)
- **Basic Calculations**: Elementary volatility and trend calculations for Home Assistant use
- **Home Assistant Integration**: Designed for automation triggers and simple dashboards
- **Data Validation**: Ensures data integrity for basic metrics
- **Note**: **Advanced analytics, complex visualizations, and detailed portfolio analysis are handled in Grafana** using the time-series data stored in InfluxDB

#### System Status (`get_status`)
- **Component Health**: Individual status for all integration components
- **Database Connectivity**: InfluxDB connection and database access verification
- **Google Sheets Status**: Sheet accessibility and permission validation
- **Version Information**: Integration compatibility reporting

#### Manual Synchronization (`update_data`)
- **On-demand Import**: Manual trigger for Google Sheets → InfluxDB data transfer
- **Data Validation**: Ensures data integrity during manual import operations
- **Error Reporting**: Detailed feedback on import success/failure

### Home Assistant Integration

#### Service Integration
- **Automation Support**: Services callable from Home Assistant automations for import triggers
- **Event Broadcasting**: Integration state changes broadcast as HA events
- **Configuration Flow**: GUI-based setup through Home Assistant interface
- **HACS Compatibility**: Standard installation via Home Assistant Community Store
- **Basic Dashboard Support**: Simple portfolio value display in Home Assistant UI

#### Sensor Platform Features
- **Device Classes**: Proper monetary and percentage device classifications
- **State Classes**: Measurement state class for historical data retention
- **Units of Measurement**: Standard currency and percentage units
- **Icon Assignments**: Intuitive icons for all sensor types

#### Error Handling & Resilience
- **Connection Retries**: Automatic retry logic for transient failures
- **Cached Data Fallback**: Uses last successful data during outages
- **Partial Error Handling**: Continues operation with degraded functionality
- **Comprehensive Logging**: Debug-level logging for troubleshooting

## Analytics & Visualization Separation

### Data Import vs Analytics Roles

#### Portfolio Tracker Integration (This Project)
- **Primary Role**: Data importer and basic monitoring
- **Responsibility**: Reliable data ingestion from Google Sheets to InfluxDB
- **Analytics Scope**: Limited to basic metrics needed for Home Assistant sensors
- **Output**: Time-series data in InfluxDB ready for consumption by analytics tools

#### Grafana (External Analytics Platform)
- **Primary Role**: Advanced analytics and visualization
- **Data Source**: Consumes time-series data from InfluxDB
- **Analytics Scope**: Complex portfolio analysis, historical trends, risk metrics, performance attribution
- **Visualization**: Rich dashboards, charts, alerts, and reporting
- **Capabilities**: Advanced queries, custom calculations, correlation analysis, benchmarking

### Integration Benefits
- **Separation of Concerns**: Import reliability vs analytical complexity
- **Scalability**: InfluxDB can serve multiple analytics consumers
- **Flexibility**: Different teams can work on data import vs analytics independently
- **Tool Optimization**: Each tool optimized for its specific purpose

## Security & Authentication

### Google API Security
- **OAuth 2.0 Integration**: Leverages Home Assistant's existing Google Drive authentication
- **Scope Limitation**: Requests only necessary Google Sheets read permissions
- **Token Management**: Automatic token refresh via Home Assistant's credential system

### InfluxDB Security
- **Credential Storage**: Secure storage of database credentials in HA configuration
- **Connection Encryption**: Supports SSL/TLS connections to InfluxDB
- **Database Isolation**: Uses dedicated database for portfolio data

## Deployment & Installation

### HACS Installation
1. Add repository to HACS as custom repository
2. Install "Portfolio Tracker" through HACS interface
3. Restart Home Assistant
4. Configure through Integrations page

### Prerequisites
- Home Assistant 2023.1.0 or newer
- InfluxDB v1 instance (Home Assistant Add-on recommended)
- Google Drive integration configured in Home Assistant
- Google Sheets document with portfolio data

### Configuration Steps
1. Configure Google Drive integration in Home Assistant
2. Install and configure InfluxDB Add-on
3. Prepare Google Sheets with portfolio data
4. Install Portfolio Tracker via HACS
5. Configure integration through Home Assistant UI

## Monitoring & Maintenance

### Health Monitoring
- **Binary Sensors**: Real-time connectivity status for all components
- **System Status Service**: Comprehensive health reporting
- **Event Broadcasting**: Integration events for automation triggers

### Troubleshooting
- **Debug Logging**: Configurable logging levels for issue diagnosis
- **Connection Testing**: Built-in connectivity verification
- **Data Validation**: Automatic data integrity checks
- **Error Reporting**: Detailed error messages for configuration issues

### Performance Considerations
- **Connection Pooling**: Efficient InfluxDB connection management
- **Data Caching**: Reduces API calls and improves responsiveness
- **Asynchronous Operations**: Non-blocking data operations
- **Configurable Intervals**: Adjustable update frequencies for load management