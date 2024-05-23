import os
import sys
import numpy as np
import pandas as pd
import matplotlib as mpl
import matplotlib.pyplot as plt
import json
from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS
import paho.mqtt.client as mqtt
from config import parameter
from fmi_mlc import fmi_gym

# MQTT settings
broker_address = 'localhost'
port = 1883
topic = 'simulation/results'
id = 'simulator'

# InfluxDB settings
influxdb_URL = 'http://localhost:8086'
influxdb_token = 'oKH04PZcfFpY8T1hT1f5yFB8t84KDjDiGQkOWlp0kwI8TX66iDp_8d0cfVPobKMLed15tzKTT7g-KyGtfNHcWA=='  # Replace with your actual InfluxDB token
influxdb_org = 'smart building'
influxdb_bucket = 'building'

# Configuring MQTT client
client = mqtt.Client(client_id=id, clean_session=True, userdata=None)
client.connect(broker_address, port)

# MQTT message callback
def on_message(client, userdata, message):
    data = json.loads(message.payload.decode('utf-8'))
    df = pd.DataFrame(data)
    write_dataframe_to_influx(df)

client.on_message = on_message

# Start the MQTT client
client.loop_start()
client.subscribe(topic)




# Configuring InfluxDB client
influxdb = InfluxDBClient(url=influxdb_URL, token=influxdb_token, org=influxdb_org)
write_api = influxdb.write_api(write_options=SYNCHRONOUS)

mpl.rcParams['figure.dpi'] = 72  # Plot config

# Directory of current script
try:
    root = os.path.dirname(os.path.realpath(_file_))
except:
    root = os.getcwd()

sys.path.append(os.path.join(root, '..'))

# Initialize the FMU-based environment
env = fmi_gym(parameter)
done = False
state = env.reset()

# Retrieve action and observation names and limits from parameters
action_names = parameter.get('action_names', [])
observation_names = parameter.get('observation_names', [])
action_max = parameter.get('action_max', [])
action_min = parameter.get('action_min', [])
reward_names = parameter.get('reward_names', [])
threshold = parameter.get('threshold', 0)

# Define the reward function
def reward_function(reward_names, observation_values):
    reward = np.zeros(len(reward_names))
    for i, name in enumerate(reward_names):
        threshold = parameter.get(f'threshold_{name}', 0)
        if observation_values[i] > threshold and observation_values[i] < threshold + 5:
            reward[i] = 1
        else:
            reward[i] = -1
    return reward.sum()

# Initialize plot_data dictionary
plot_data = {}

# Simulation loop
while not done:
    try:
        # Sample a random action
        action = env.action_space.sample()

        # Apply the action limits
        action = np.clip(action, action_min, action_max)

        # Execute the updated action in the environment
        state, reward, done, info = env.step(action)

        observation_values = state  # Assuming the state contains the observation values

        # Calculate the reward based on the state and action
        reward = reward_function(reward_names, observation_values)

        # Store the action values and observation values in plot_data
        for i, name in enumerate(action_names):
            plot_data.setdefault(name, []).append(action[i])
        for i, name in enumerate(observation_names):
            plot_data.setdefault(name, []).append(state[i])
        plot_data.setdefault('reward', []).append(reward)

    except Exception as e:
        print(f"Error during simulation step: {e}")
        break

# Close the environment
env.close()

# Convert plot data to DataFrame
res = pd.DataFrame(plot_data)



from datetime import datetime,timedelta

start_time = datetime.now()
time_interval = timedelta(seconds=1)  # 1 second interval between rows
timestamps = [start_time + i * time_interval for i in range(len(res))]
res['timestamp'] = timestamps
print(res)
# Publish the DataFrame as a JSON string
client.publish(topic, res.to_json(orient='split'), qos=1, retain=False)




# Function to write DataFrame to InfluxDB
def write_dataframe_to_influx(df):
    try:
        points = []
        for _, row in df.iterrows():
            point = Point("simulation")
            for column, value in row.items():
                if column != 'timestamp':
                    point = point.field(column, float(value)) # Assuming all values are float
            point = point.time(row['timestamp'], WritePrecision.NS)
            # Optional: Add a tag for better organization
            #point = point.tag("simulation", "simulation")
            points.append(point)
        write_api.write(bucket=influxdb_bucket, org=influxdb_org, record=points)
        print(f"Written {len(points)} points to InfluxDB.")  # Debug print
    except Exception as e:
        print(f"Error writing to InfluxDB: {e}")

#write_dataframe_to_influx(res)









# Stop the MQTT client
client.loop_stop()
client.disconnect()

# Close the InfluxDB client
influxdb.close()

# Plotting the results
fig, axs = plt.subplots(len(action_names) + len(observation_names), 1, figsize=(10, 5 * (len(action_names) + len(observation_names))))
axs = axs.ravel()

for i, name in enumerate(action_names + observation_names):
    axs[i].plot(res.index, res[name])
    axs[i].set_ylabel(name)
    axs[i].set_xlabel('Time')

# Add reward plots if there are any rewards
if 'reward' in res.columns:
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(res.index, res['reward'], label='reward')
    ax.set_title('Rewards over Time')
    ax.set_xlabel('Time')
    ax.set_ylabel('Reward')
    ax.legend()

plt.tight_layout()
plt.show()