import serial
import time
from os import environ
import boto3
import datetime

client = boto3.client('cloudwatch')
device = environ.get('DEVICE') if environ.get('DEVICE') is not None else "/dev/ttyACM0"
arduino = serial.Serial(device)
arduino.baudrate=environ.get('BAUDRATE') if environ.get('BAUDRATE') is not None else 9600
while True:
    raw_data = arduino.readline().decode("utf-8")
    data=raw_data.split("|")
    temperature = data[0]
    humidity = data[1]
    print("Temp: {}°C, Humidity: {}%".format(temperature, humidity))
    client.put_metric_data(
        Namespace='HOME',
        MetricData=[
            {
                'MetricName': 'temperature',
                'Timestamp': datetime.datetime.now(),
                'Value': float(temperature),
                'Unit': 'None',
                'StorageResolution': 60
            },
        ]
    )
    client.put_metric_data(
        Namespace='HOME',
        MetricData=[
            {
                'MetricName': 'humidity',
                'Timestamp': datetime.datetime.now(),
                'Value': float(humidity),
                'Unit': 'None',
                'StorageResolution': 60
            },
        ]
    )