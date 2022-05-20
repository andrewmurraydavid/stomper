from concurrent.futures import process
import os
import numpy as np
import time
import cv2

class CameraProcessor(object):
    font = cv2.FONT_HERSHEY_SIMPLEX
    _marker = [0,0,0,0]
    _tract = [0,0,0,0]

    @property
    def marker(self):
        return self._marker

    @property
    def tract(self):
        return self._tract

    @marker.setter
    def marker(self, value):
        self._marker = value
        self.brain.set_marker(value)

    @tract.setter
    def tract(self, value):
        self._tract = value
        self.brain.set_tract(value)


    def __init__(self, brain):
        self.brain = brain
        print("Preparing camera")

        # Last please!
        print("Sleeping for 3 seconds")
        time.sleep(3)

    def crop_image(self, image):
        return image[400:1400, 100:900]

    def get_average_color(self, image):
        return np.array(cv2.mean(image)).astype(np.uint8)
    
    def get_average_color_of_contour(self, image, contour):
        return np.array(cv2.mean(image[contour])).astype(np.uint8)

    def get_gray_image(self, image):
        return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    def process_image(self, frame):
        self.brain.process()

        cropped_color = self.crop_image(frame)
        cropped_grey = self.get_gray_image(cropped_color)

        info_height = int(1920 - (cropped_color.shape[0] * 3))
        info_width = cropped_color.shape[1]

        info_image = np.zeros((info_height, info_width,3), np.uint8)

        ret,thresh = cv2.threshold(cropped_grey, 10, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        contours = cv2.findContours(thresh, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

        contours = contours[0] if len(contours) == 2 else contours[1]

        output = self.process_contours(contours, cropped_color)


        cropped = cv2.resize(cropped_grey, (1080, int(1080 * cropped_grey.shape[0] / cropped_grey.shape[1])), interpolation = cv2.INTER_AREA)
        thresh = cv2.resize(thresh, (1080, int(1080 * thresh.shape[0] / thresh.shape[1])), interpolation = cv2.INTER_AREA)
        output = cv2.resize(output, (1080, int(1080 * output.shape[0] / output.shape[1])), interpolation = cv2.INTER_AREA)
        frame = cv2.resize(frame, (1080, int(1080 * frame.shape[0] / frame.shape[1])), interpolation = cv2.INTER_AREA)
        info = cv2.resize(info_image, (1080, int(1920 - (cropped.shape[0] * 3))), interpolation = cv2.INTER_AREA)

        self.put_info_on_info_image(info)

        self.display_window(cropped, thresh, output, frame, info=info)

    def put_info_on_info_image(self, info):
        ts = 0.75
        cv2.putText(info, f"Marker: {self.marker}", (5,25), self.font, ts, (255, 255, 255), 1, cv2.LINE_AA)
        cv2.putText(info, f"Tract: {self.tract}", (5,50), self.font, ts, (255, 255, 255), 1, cv2.LINE_AA)
        cv2.putText(info, f"Position {self.brain.position}", (5,75), self.font, ts, (255, 255, 255), 1, cv2.LINE_AA)
        cv2.putText(info, f"Action {self.brain.action}", (5,100), self.font, ts, (255, 255, 255), 1, cv2.LINE_AA)
        cv2.putText(info, f"Has new tract {self.brain.is_new_tract}", (5,125), self.font, ts, (255, 255, 255), 1, cv2.LINE_AA)
        time_remaining = int(self.brain.last_valid_tract + 10 - time.time())
        cv2.putText(info, f"Time remaining: {time_remaining}", (5,150), self.font, ts, (255, 255, 255), 1, cv2.LINE_AA)

    def find_marker(self, contour, area, output):
        x,y,w,h = cv2.boundingRect(contour)

        if area > 8000 and area < 15000 and w > h * 3:
            img_hsv = cv2.cvtColor(output, cv2.COLOR_BGR2HSV)
            mask = cv2.inRange(img_hsv, (0, 0, 0), (255, 255, 255))

            cropped_from_contour = output[y:y+h, x:x+w]
            cv2.rectangle(output,(x,y),(x+w,y+h),(0,0,0),2)

            cv2.putText(output, f"x:{x}, y:{y}", (x+5,y+27), self.font, 0.35, (255, 255, 255), 1, cv2.LINE_AA)

            cv2.rectangle(output,(x,y),(x+w,y+h),(0,255,0),2)
            
            average_color = self.get_average_color(output[y:y+h,x:x+w])
            
            cv2.putText(output, f"{average_color}", (x+5,y+37), self.font, 0.35, (255, 255, 255), 1, cv2.LINE_AA)

            cv2.putText(output, f"w:{w}, h:{h}", (x+5,y+47), self.font, 0.35, (255, 255, 255), 1, cv2.LINE_AA)
            self.marker = [x, y, w, h]

            return True

        self.marker = [0, 0, 0, 0]
        return False

    def find_tract(self, contour, area, output):
        if area > 190000:
            x,y,w,h = cv2.boundingRect(contour)
            cv2.drawContours(output, [contour], -1, (0, 255, 0), 1)
            rect = cv2.minAreaRect(contour)
            box = cv2.boxPoints(rect)
            box = np.int0(box)
            cv2.drawContours(output,[box],0,(0,0,255),5)
            
            cv2.putText(output, f"{x}, {y}", (x+5,y+25), self.font, 0.35, (255, 255, 255), 1, cv2.LINE_AA)

            self.tract = [x, y, w, h]
            return True

        self.tract = [0, 0, 0, 0]
        return False

    def process_contours(self, contours, image):
        output = image.copy()
        for c in contours:
            area = cv2.contourArea(c)
            if area > 3000:
                x,y,w,h = cv2.boundingRect(c)
                cv2.putText(output, str(area), (x+5,y+15), self.font, 0.35, (255, 255, 255), 1, cv2.LINE_AA)

                if not self.find_marker(c, area, output):
                    self.find_tract(c, area, output)
        return output

    def convert_grey_to_bgr(self, image):
        return cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)            
    
    def display_window(self, cropped, thresh, output, original, info):
        # resize cropped width 1080 keep aspect
        resized_original_to_cropped = cv2.resize(original, (cropped.shape[1], cropped.shape[0]))

        ch_3_cropped = self.convert_grey_to_bgr(cropped)
        ch_3_thresh = self.convert_grey_to_bgr(thresh)

        numpy_horizontal = np.vstack((resized_original_to_cropped, ch_3_thresh))
        # numpy_horizontal = np.vstack((numpy_horizontal, ch_3_thresh))
        numpy_horizontal = np.vstack((numpy_horizontal, output))
        numpy_horizontal = np.vstack((numpy_horizontal, info))
        cv2.startWindowThread()

        cv2.namedWindow("STAMPER", cv2.WND_PROP_FULLSCREEN)
        cv2.setWindowProperty("STAMPER",cv2.WND_PROP_FULLSCREEN,cv2.WINDOW_FULLSCREEN)
        
        cv2.imshow('STAMPER', numpy_horizontal)

    def abort (self):
        key = cv2.waitKey(10) & 0xFF
        if (key == ord('q')):
            cv2.destroyAllWindows()
            os.abort()

    def get_image(self):
        return self.camera.get_image()

    def run(self):
        raise NotImplementedError()
