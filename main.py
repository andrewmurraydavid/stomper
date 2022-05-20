import cv2
from picamera.array import PiRGBArray
from picamera import PiCamera

from camera import CameraProcessor
from brain import Brain
from stepper import StepperAdapter


stepper_adapter = StepperAdapter()
brain = Brain(stepper_adapter)


picam = PiCamera()
picam.resolution = (1280, 720)
picam.framerate = 32
raw_capture = PiRGBArray(picam, size=(1280, 720))
    
camera_processor = CameraProcessor(brain)

for frame in picam.capture_continuous(raw_capture, format="bgr", use_video_port=True):
    camera_processor.process_image(frame.array)
    raw_capture.truncate(0)
