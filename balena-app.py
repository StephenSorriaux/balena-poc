import serial
import time
from os import environ
import json

from kafka import KafkaProducer

class Metric(object):

    def __init__(self, name, value, unit):
        self.name = name
        self.value = value
        self.unit = unit

    def __repr__(self):
        metric = {
            'version': 1,
            'name': self.name,
            'value': self.value,
            'unit': self.unit,
            'time': str(time.time()),
            'meta': {
                'location': 'home'
            }
        }

        return json.dumps(metric)

kafka_server = environ.get('KAFKA_BOOTSTRAP_SERVERS')
try:
    client = KafkaProducer(bootstrap_servers=kafka_server)
except Exception as e:
    print('Cant initialize Kafka client: {}'.format(str(e)))
    raise

device = environ.get('DEVICE') if environ.get('DEVICE') is not None else "/dev/ttyACM0"
try:
    arduino = serial.Serial(device)
    arduino.baudrate=environ.get('BAUDRATE') if environ.get('BAUDRATE') is not None else 9600
except Exception as e:
    print('Cant get serial device: {}'.format(str(e)))
    raise

while True:
    try:
        raw_data = arduino.readline().decode("utf-8")
        data=raw_data.split("|")
        temperature = Metric(name='temperature', value=float(data[0]), unit='degrees')
        humidity = Metric(name='humidity', value=float(data[1]), unit='percent')
        print("Temp: {}°C, Humidity: {}%".format(temperature.value, humidity.value))
        print("Sending {} and {}".format(str(temperature), str(humidity)))

        client.send('metrics', str(temperature).encode('utf-8'))
        client.send('metrics', str(humidity).encode('utf-8'))
        client.flush()
    except Exception as e:
        print(e)
        pass
    
    time.sleep(60)