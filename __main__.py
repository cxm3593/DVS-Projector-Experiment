# Main DVS Control Program
# Author: Chengyi Ma
# 

from metavision_core.event_io import EventsIterator
from metavision_sdk_core import PeriodicFrameGenerationAlgorithm
from metavision_sdk_ui import EventLoop, BaseWindow, Window, UIAction, UIKeyEvent
from metavision_core.event_io.raw_reader import initiate_device
from metavision_hal import I_LL_Biases, I_TriggerIn
import json
import os.path
import numpy as np
import h5py

def parse_args():
    import argparse
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='DVS-Projector program',
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument(
        '-i', '--input-event-file', dest='event_file_path', default="",
        help="Path to input event file (RAW or HDF5). If not specified, the camera live stream is used. "
        "If it's a camera serial number, it will try to open that camera instead.")
    args = parser.parse_args()
    return args

def test_function():
    print("This is a dummy test function")


def main():
    """ Main """
    # Initialization
    script_directory = os.path.dirname(os.path.abspath(__file__))

    # Load config
    config_path:str = os.path.join(script_directory, "config.json")
    config = {}
    with open(config_path, "r") as config_file:
        config = json.loads(config_file.read())

    # Output file
    output_recording_path = os.path.join(script_directory, "output_recording.h5")
    output_file = h5py.File(output_recording_path, "a")


    serial_number = config["camera_serial_number"]

    # Process arguments
    args = parse_args()

    # Initialize device
    device = initiate_device('', use_external_triggers=[I_TriggerIn.Channel.MAIN])
    triggers = device.get_i_event_ext_trigger_decoder()
    mv_iterator = EventsIterator.from_device(device, delta_t=1000)

    # for evs in mv_iterator:
    print("Events are available!")

    # Set up window
    height, width = mv_iterator.get_size()  # Camera Geometry

    # Window - Graphical User Interface
    with Window(title="Metavision SDK Get Started", width=width, height=height, mode=BaseWindow.RenderMode.BGR) as window:
        def keyboard_cb(key, scancode, action, mods):
            if action != UIAction.RELEASE:
                return
            if key == UIKeyEvent.KEY_ESCAPE or key == UIKeyEvent.KEY_Q:
                window.set_close_flag()

        window.set_keyboard_callback(keyboard_cb)
        # Event Frame Generator
        event_frame_gen = PeriodicFrameGenerationAlgorithm(sensor_width=width, sensor_height=height,
                                                        accumulation_time_us=10000)
        
        def on_cd_frame_cb(ts, cd_frame):
            window.show(cd_frame)

        event_frame_gen.set_output_callback(on_cd_frame_cb)

        # Process event
        global_counter = 0  # This will track how many events we processed
        global_max_t = 0  # This will track the highest timestamp we processed
        for evs in mv_iterator:
            print("----- New event buffer! -----")
            if evs.size == 0:
                print("The current event buffer is empty.")
            else:
                min_t = evs['t'][0]   # Get the timestamp of the first event of this callback
                max_t = evs['t'][-1]  # Get the timestamp of the last event of this callback
                global_max_t = max_t  # Events are ordered by timestamp, so the current last event has the highest timestamp

                counter = evs.size  # Local counter
                global_counter += counter  # Increase global counter

                

                print(f"There were {counter} events in this event buffer.")
                print(f"There were {global_counter} total events up to now.")
                print(f"The current event buffer included events from {min_t} to {max_t} microseconds.")
                print("----- End of the event buffer! -----")

                # Display
                # Dispatch system events to the window
                EventLoop.poll_and_dispatch()
                event_frame_gen.process_events(evs)

                # Write to output file
                try:
                    output_file.create_dataset(f"event_time{global_max_t}", data=evs)
                except:
                    print("Error in writing event to H5 file")

    # Print the global statistics
    duration_seconds = global_max_t / 1.0e6
    print(f"There were {global_counter} events in total.")
    print(f"The total duration was {duration_seconds:.2f} seconds.")

    if duration_seconds >= 1:  # No need to print this statistics if the total duration was too short
        print(f"There were {global_counter / duration_seconds :.2f} events per second on average.")

    # Clean up
    output_file.close()


if __name__ == "__main__":
    main()

# Divisive Normalization