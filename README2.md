# Educational Platform for Building Design

## Description
This project utilizes advanced simulation techniques with Python, integrating MQTT for transferring simulation data, InfluxDB for managing time-series data, and an FMU-based environment for dynamic system simulation. The primary goal is to perform simulations efficiently, collect, publish, and store simulation data, and provide real-time visualization capabilities.

## Installation

### Prerequisites
Before you begin, ensure the following tools and packages are installed:
- **Python 3.9 or higher**: Needed to run the scripts.
- **Conda**: Recommended for managing Python libraries and environments.
- **EnergyPlus**: Essential for building simulations.


### Dependencies
Use Conda and pip to install the required libraries. For complex dependencies like `pyfmi`, Conda Forge is recommended. Here are the commands to install all necessary dependencies:

```bash
conda create --name myenv python=3.9
conda activate myenv
conda install -c conda-forge pyfmi lxml assimulo cython wxpython
pip install numpy pandas matplotlib paho-mqtt influxdb_client

## Additional Documentation
as additional refrence for implementing the environment you could go to this video on youtube (https://www.youtube.com/watch?v=2CE7FGBxSeM)
