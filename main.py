import csv

import cv2
import easyocr
import pyautogui as pg
import numpy as np
import matplotlib.pyplot as plt
import json

reader = easyocr.Reader(["en"])


class TextBox:
    def __init__(self, x1, y1, x2, y2):
        self.x1 = x1
        self.x2 = x2
        self.y1 = y1
        self.y2 = y2
        self.frame = np.ndarray
        self.text = ""

    def detect(self, original_frame):
        self.frame = original_frame[self.y1:self.y2, self.x1:self.x2]
        result = reader.readtext(self.frame, detail=0, allowlist='.0123456789')
        if len(result) == 0:
            pass
        else:
            self.text = result[0]
        print(self.text)


class TimeTextBox(TextBox):
    def __init__(self, x1, y1, x2, y2):
        super().__init__(x1, y1, x2, y2)

    def detect(self, original_frame):
        self.frame = original_frame[self.y1:self.y2, self.x1:self.x2]
        result = reader.readtext(self.frame, detail=0, allowlist='T+-:0123456789')
        if len(result) == 0:
            pass
        else:
            self.text = result[0]
        print(self.text)


class Stage:
    def __init__(self, stage_num, stage_dict):
        self.stage_num = stage_num
        self.speed = 0
        self.altitude = 0
        self.speed_textbox = TextBox(*stage_dict["speed"])
        self.altitude_textbox = TextBox(*stage_dict["altitude"])
        self.speed_textbox.text = "0"
        self.altitude_textbox.text = "0"
        self.temp_speed = 0
        self.temp_altitude = 0

    def update(self, original_frame):
        self.speed_textbox.detect(original_frame)
        self.altitude_textbox.detect(original_frame)
        temp_speed_text = self.speed_textbox.text.replace("-", "")
        if not temp_speed_text == "":
            self.temp_speed = float(temp_speed_text)
        temp_altitude_text = self.altitude_textbox.text.replace("-", "")
        if not temp_altitude_text == "":
            self.temp_altitude = float(temp_altitude_text)
        # if self.temp_speed < self.speed + 1000:
        self.speed = self.temp_speed
        if self.temp_altitude < (self.altitude + 5) * 20 and self.temp_altitude < 6000:
            self.altitude = self.temp_altitude


class Rocket:
    def __init__(self, name, json_dict, is_stage2=False):
        self.name = name
        self.int_time = 0
        self.rocket_dict = json_dict[name]
        self.time = TimeTextBox(*self.rocket_dict["time"])
        self.is_stage2 = is_stage2
        self.csv = csv.writer(open(f"{self.name}.csv", "w", newline=""))
        self.csv.writerow(["Time", "Altitude1", "Speed1", "Altitude2", "Speed2"])
        if self.is_stage2:
            self.stages = [Stage(1, self.rocket_dict["Stage1"]), Stage(2, self.rocket_dict["Stage2"])]
        else:
            self.stages = [Stage(1, self.rocket_dict["Stage1"])]
        self.fig = plt.figure(figsize=(4, 4))
        plt.rcParams["font.size"] = 20
        self.time_list = []
        self.altitude = [[], []]
        self.speed = [[], []]
        self.fig_altitude = self.fig.add_subplot(2, 1, 1)
        self.fig_speed = self.fig.add_subplot(2, 1, 2)
        self.last_time = 0
        self.frame = 0

    def update(self, frame):
        self.time.detect(frame)
        self.stages[0].update(frame)
        if self.is_stage2:
            self.stages[1].altitude_textbox.text = self.stages[0].altitude_textbox.text
            self.stages[1].update(frame)
        self.time.text = self.time.text.replace(".", ":")
        self.int_time = time_change(self.int_time, self.time.text)
        if self.int_time == self.last_time:
            self.frame += 1
        else:
            self.frame = 0
        self.fig_altitude.cla()
        self.fig_speed.cla()
        self.time_list.append(self.int_time + self.frame / 60)
        self.altitude[0].append(self.stages[0].altitude)
        if self.is_stage2:
            self.altitude[1].append(self.stages[1].altitude)
        self.speed[0].append(self.stages[0].speed)
        if self.is_stage2:
            self.speed[1].append(self.stages[1].speed)
        self.last_time = self.int_time
        self.csv.writerow([self.int_time + self.frame / 60, self.stages[0].altitude, self.stages[0].speed])
        if (len(self.time_list) == 0) or (len(self.altitude[0]) == 0):
            return
        if (len(self.time_list) == 0) or (len(self.speed[0]) == 0):
            return

        # altitude
        self.fig_altitude.plot(self.time_list, self.altitude[0], color="cyan", label="1st Stage")
        if self.is_stage2:
            self.fig_altitude.plot(self.time_list, self.altitude[1], color="red", label="2nd Stage")
            self.fig_altitude.set_ylim(0, max(max(self.altitude[0]), max(self.altitude[1]))*1.1)
        else:
            self.fig_altitude.set_ylim(0, max(self.altitude[0])*1.1)
        self.fig_altitude.set_xlim(-10, self.time_list[-1]*1.1)
        self.fig_altitude.set_xlabel("Time [s]")
        self.fig_altitude.set_ylabel("Altitude [km]")
        self.fig_altitude.legend(loc="upper left")

        # speed
        self.fig_speed.plot(self.time_list, self.speed[0], color="cyan", label="1st Stage")
        if self.is_stage2:
            self.fig_speed.plot(self.time_list, self.speed[1], color="red", label="2nd Stage")
            self.fig_speed.set_ylim(0, max(max(self.speed[0]), max(self.speed[1])) * 1.1)
        else:
            self.fig_speed.set_ylim(0, max(self.speed[0]) * 1.1)
        self.fig_speed.set_xlim(-10, self.time_list[-1] * 1.1)
        self.fig_speed.set_xlabel("Time [s]")
        self.fig_speed.set_ylabel("Speed [km/h]")
        self.fig_speed.legend(loc="upper left")
        plt.pause(0.01)


def time_change(last_time, str_time):
    if len(str_time) == 10:
        hour = int(str_time[2:4])
        minute = int(str_time[5:7])
        second = int(str_time[8:10])
        if str_time[1] == "-":
            return -(3600 * hour + 60 * minute + second)
        else:
            return 3600 * hour + 60 * minute + second
    else:
        return last_time


def main():
    with open("setting.json") as f:
        json_dict = json.load(f)
    # f9 = Rocket("Falcon9", json_dict, True)
    # starship = Rocket("Starship", json_dict, True)
    h3 = Rocket("H3", json_dict)

    # cap = cv2.VideoCapture("test.mp4")

    while True:
        # ret, img = cap.read()
        img = pg.screenshot(region=(0, 0, 1920, 1080))
        frame = np.asarray(img)
        # f9.update(frame)
        # starship.update(frame)
        h3.update(frame)
        #frame = cv2.resize(frame, (960, 540))
        #cv2.imshow("a", frame)
        #key = cv2.waitKey(1)
        #if key == 27:
        #    break
    #cv2.destroyAllWindows()


if __name__ == '__main__':
    main()
