import json
from os import environ
from threading import Thread
import time

from jaeger_client import Config
from kafka import KafkaProducer
import speedtest
import serial

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


def get_metrics_from_arduino(tracer, client, arduino):
    while True:
        try:
            with tracer.start_span('get-arduino-metric'):
                raw_data = arduino.readline().decode("utf-8")
            
            data=raw_data.split("|")
            temperature = Metric(name='temperature', value=float(data[0]), unit='degrees')
            humidity = Metric(name='humidity', value=float(data[1]), unit='percent')
            print("Temp: {}°C, Humidity: {}%".format(temperature.value, humidity.value))
            print("Sending {} and {}".format(str(temperature), str(humidity)))

            with tracer.start_span('send-metrics-to-kafka'):
                client.send('metrics', str(temperature).encode('utf-8'))
                client.send('metrics', str(humidity).encode('utf-8'))
                client.flush()
        except Exception as e:
            print(e)
            pass
        
        time.sleep(60)

def get_current_bandwith(tracer, speedtest, client):
    while True:
        with tracer.start_span('get-download-value'):
            try:
                download_value = speedtest.download()
                download = Metric(name='download', value=download_value, unit='bits/s')
            except Exception as e:
                print('Cant get download value for this run: ', str(e))
                download = Metric(name='download', value=0, unit='bits/s')

        with tracer.start_span('get-upload-value'):
            try:
                upload_value = speedtest.upload(pre_allocate=False)
                upload = Metric(name='upload', value=upload_value, unit='bits/s')
            except Exception as e:
                print('Cant get upload value for this run: ', str(e))
                upload = Metric(name='upload', value=0, unit='bits/s')

        print("Sending {} and {}".format(str(upload), str(download)))

        with tracer.start_span('send-metrics-to-kafka'):
            try:
                client.send('metrics', str(download).encode('utf-8'))
                client.send('metrics', str(upload).encode('utf-8'))
                client.flush()
            except Exception as e:
                print('Cant send metrics to Kafka: ',str(e))
        
        time.sleep(60)

if __name__ == '__main__':

    jaeger_host = environ.get('JAEGER_HOST')
    config = Config(
        config={ 
            'local_agent': {
                'reporting_host': jaeger_host,
            },
            'sampler': {
                'type': 'const',
                'param': 1,
            },
            'logging': True,
        },
        service_name='balena-app',
        validate=True,
    )
    tracer = config.initialize_tracer()

    with tracer.start_span('init-kafka-client'):
        kafka_server = environ.get('KAFKA_BOOTSTRAP_SERVERS')
        try:
            client = KafkaProducer(bootstrap_servers=kafka_server)
        except Exception as e:
            print('Cant initialize Kafka client: {}'.format(str(e)))
            raise


    with tracer.start_span('init-arduino-connection'):
        device = environ.get('DEVICE') if environ.get('DEVICE') is not None else "/dev/ttyACM0"
        try:
            arduino = serial.Serial(device)
            arduino.baudrate=environ.get('BAUDRATE') if environ.get('BAUDRATE') is not None else 9600
        except Exception as e:
            print('Cant get serial device: {}'.format(str(e)))
            raise

    with tracer.start_span('init-speedtest-bandwith'):
        st = speedtest.Speedtest()
        st.get_best_server()


    thread_arduino = Thread(
        target=get_metrics_from_arduino,
        name='t_arduino',
        args=(tracer, client, arduino),
        daemon=True
    )

    thread_bandwith = Thread(
        target=get_current_bandwith,
        name='t_bandwith',
        args=(tracer, st, client),
        daemon=True
    )

    thread_arduino.start()
    thread_bandwith.start()

    thread_arduino.join()
    thread_bandwith.join()

    tracer.close()