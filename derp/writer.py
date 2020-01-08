"""The disk writer class that records all derp agent messages."""
from datetime import datetime
import socket
import time
import yaml
import derp.util


class Writer:
    """The disk writer class that records all derp agent messages."""

    def __init__(self, config):
        """Using a dict config connects to all possible subscriber sources"""
        self.config = config['writer']
        self.car_config = config
        self.__context, self.__subscriber = derp.util.subscriber(
            [
                "/tmp/derp_camera",
                "/tmp/derp_imu",
                "/tmp/derp_brain",
                "/tmp/derp_joystick",
            ]
        )
        self.is_recording = False
        self.files = {}

    def __del__(self):
        """Close the only active object; the subscriber"""
        self.__subscriber.close()
        self.__context.term()

    def initialize_recording(self):
        date = datetime.utcfromtimestamp(time.time()).strftime("%Y%m%d-%H%M%S")
        folder = derp.util.ROOT / 'recordings' / ("recording-%s-%s" % (date, socket.gethostname()))
        folder.mkdir(parents=True)
        self.files = {}
        with open(str(folder / "config.yaml"), "w") as config_fd:
            yaml.dump(self.car_config, config_fd)
        return folder

    def run(self):
        """
        Read the next available topic. If we're not in a recording state and a state message
        arrives with a command to record then create a new folder, and write all messages
        to this folder until another state message tells us to stop.
        """
        topic_bytes, message_bytes = self.__subscriber.recv_multipart()
        recv_timestamp = derp.util.get_timestamp()
        topic = topic_bytes.decode()
        message = derp.util.TOPICS[topic].from_bytes(message_bytes).as_builder()

        # Create folder or delete folder
        if topic == "controller":
            if message.isRecording and not self.is_recording:
                self.recording_folder = self.initialize_recording()
                print("Started recording", self.recording_folder)
                self.is_recording = True
            elif not message.isRecording and self.is_recording:
                print("Stopped recording")
                for name in self.files:
                    self.files[name].close()
                self.files = {}
                self.is_recording = False
                self.recording_folder = None

        if self.is_recording:
            if topic not in self.files:
                self.files[topic] = derp.util.topic_file_writer(self.recording_folder, topic)
            message.writeNS = derp.util.get_timestamp()
            message.write(self.files[topic])
        return True
