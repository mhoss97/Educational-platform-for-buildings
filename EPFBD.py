import os
import sys
import numpy as np
import pandas as pd
import matplotlib.pyplot as mpl
import matplotlib.pyplot as plt
import json
from datetime import datetime
import paho.mqtt.client as mqtt
from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS
from config import *
from fmi_mlc import fmi_gym
from datetime import datetime, timedelta

class DataHandler:
    def __init__(self, influx_url, influx_token, influx_org, bucket, broker_address='localhost', port=1883, topic='simulation/results', client_id='simulator'):
        self.influx_client = InfluxDBClient(url=influx_url, token=influx_token, org=influx_org)
        self.write_api = self.influx_client.write_api(write_options=SYNCHRONOUS)
        self.mqtt_client = mqtt.Client(client_id=client_id)
        self.mqtt_client.on_connect = self.on_connect
        self.mqtt_client.on_message = self.on_message
        self.mqtt_client.connect(broker_address, port)
        self.topic = topic
        self.bucket = bucket

    def on_connect(self, client, userdata, flags, rc):
        print("Connected with result code " + str(rc))
        client.subscribe(self.topic)

    def on_message(self, client, userdata, msg):
        df = pd.read_json(msg.payload.decode('utf-8'), orient='split')
        df = pd.DataFrame(df)
        self.write_point_to_influx(df)

    def write_point_to_influx(self, data, timestamp=None, year=None):
            # Assume timestamp is the number of seconds elapsed since the start of the year
            # Reference year - you can make this dynamic or configurable as needed
            print(year)
            print(Begin_Day_of_Month)
            print(Begin_Month)
            
            # Start date of the year
            start_of_year = datetime(year, Begin_Month, Begin_Day_of_Month)
            
            # Calculate the resulting datetime by adding the elapsed seconds
            resulting_datetime = start_of_year + timedelta(seconds=timestamp)

            
            point = Point("simulation")
            for key, value in data.items():
                point = point.field(key, float(value))
            
            point = point.time(resulting_datetime, WritePrecision.NS)
            try:
                self.write_api.write(self.bucket, self.influx_client.org, point)
                print(f"Successfully wrote point: {point.to_line_protocol()}")
            except Exception as e:
                print(f"Failed to write point: {e}")

    def publish_data(self, df):
        res_json = df.to_json(orient='split')
        self.mqtt_client.publish(self.topic, res_json, qos=1)
        print("Data published.")

    def get_year_from_epw(self, file_path):
        with open(file_path, 'r') as file:
            for line in file:
                values = line.split(',')
                if values[0].isdigit() and len(values[0]) == 4:  # Check if the first value is a year
                    return int(values[0])
    def close(self):
        self.influx_client.close()
        self.mqtt_client.disconnect()





def main():
    # Configurations
    influxdb_URL = 'http://localhost:8086'
    influxdb_token = 'E1lF0LwGOOBHVhom73RxNLEBaxZqi5w6VjU93QnpBIPD0ed0VfiKtgnGlpbXcMlTRMJZl9cLdCbj0SI47aSPOg=='
    influxdb_org = 'interproject'
    influxdb_bucket = 'new3'
    handler = DataHandler(influxdb_URL, influxdb_token, influxdb_org, influxdb_bucket)

    mpl.rcParams['figure.dpi'] = 72  # Plot config

    # Directory of current script
    try:
        root = os.path.dirname(os.path.realpath(__file__))
    except:
        root = os.getcwd()

    sys.path.append(os.path.join(root, '..'))

    # Initialize the FMU-based environment
    env = fmi_gym(parameter)
    done = False
    state = env.reset()
    year = int(handler.get_year_from_epw(r'Output_EPExport_Slave\runweafile.epw'))
    print(year)

    # Retrieve action and observation names and limits from parameters
    action_names = parameter.get('action_names', [])
    observation_names = parameter.get('observation_names', [])
    action_max = parameter.get('action_max', [])
    action_min = parameter.get('action_min', [])
    #reward_names = parameter.get('reward_names', [])
    #threshold = parameter.get('threshold', 0)

    # Define the reward function
    # def reward_function(reward_names, reward_values):
    #     reward = np.zeros(len(reward_names))
    #     for i, name in enumerate(reward_names):
    #         if reward_values[i] > threshold and reward_values[i] < threshold + 5:
    #             reward[i] = 1
    #         else:
    #             reward[i] = -1
    #     return reward.sum()

    handler.mqtt_client.loop_start()
    # Initialize plot_data dictionary
    plot_data = {}
    

    # Simulation loop
    while not done:
        try:
            action = env.action_space.sample()
            action = np.clip(action, action_min, action_max)
            timestamp = env.fmu_time
            year = year

            state, _ , done, info = env.step(action)

            # Prepare data for InfluxDB writing
            data_to_write = {name: value for name, value in zip(action_names + observation_names, np.concatenate((action, state)))}
            #data_to_write['reward'] = reward

            # Write data to InfluxDB
            
            handler.publish_data(pd.DataFrame(data_to_write, index=[0]))
            handler.write_point_to_influx(data_to_write, timestamp=timestamp, year=year)
             # Store the action values and observation values in plot_data
            for i, name in enumerate(action_names):
                plot_data.setdefault(name, []).append(action[i])
            for i, name in enumerate(observation_names):
                plot_data.setdefault(name, []).append(state[i])
            #plot_data.setdefault('reward', []).append(reward)

        except Exception as e:
            print(f"Error during simulation step: {e}")
            break

    # Close the environment
    env.close()

    # Convert plot data to DataFrame
    res = pd.DataFrame(plot_data)
    # Plotting the results
    fig, axs = plt.subplots(len(action_names) + len(observation_names), 1, figsize=(10, 5 * (len(action_names) + len(observation_names))))
    axs = axs.ravel()


    for i, name in enumerate(action_names + observation_names):
        axs[i].plot(res.index, res[name])
        axs[i].set_ylabel(name)
        axs[i].set_xlabel('Time')

    # # Add reward plots if there are any rewards
    # if 'reward' in res.columns:
    #     fig, ax = plt.subplots(figsize=(10, 5))
    #     ax.plot(res.index, res['reward'], label='reward')
    #     ax.set_title('Rewards over Time')
    #     ax.set_xlabel('Time')
    #     ax.set_ylabel('Reward')
    #     ax.legend()

    plt.tight_layout()
    plt.show()
    handler.mqtt_client.loop_stop()
    handler.close()

if  __name__ == '__main__':
    main()