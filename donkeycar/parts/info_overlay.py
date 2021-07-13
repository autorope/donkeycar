import cv2


class InfoOverlayer(object):
    """
    Add a info overlay to the camera image
    """

    # Store the infos which will be write to image
    info_list = []

    def __init__(self, w=None, h=None):

        # Camera image's size
        self.img_width = w
        self.img_height = h

        # Overlay text's properties
        self.text_offset = (5, 100)
        self.font = cv2.FONT_HERSHEY_SIMPLEX
        self.font_size_multiplier = 2
        self.text_color = (255, 255, 255)
        self.text_thickness = 1

    def add(self, string):
        self.info_list.append(string)

    # truncate input so it won't cover up the screen
    def slice(self, input, start=0, end=5, step=1):
        if input is not None:
            input = str(input)[start:end:step]
        return input

    def writeToImg(self, input_img):
        # Config overlay texts
        text_x = int(self.text_offset[0])
        text_y = int(self.text_offset[1] * self.img_height / 1000)      # Text's gap relative to the image size
        font = self.font
        font_size = self.font_size_multiplier * self.img_width / 1000   # Font's size relative to the image size
        color = self.text_color
        thickness = self.text_thickness

        # Write each info onto images
        for idx, info in enumerate(self.info_list):
            cv2.putText(input_img, info, (text_x, text_y * (idx + 1)),
                        font, font_size, color, thickness)

    def run(self, img_arr, fps, user_mode, user_throttle, user_angle, pilot_throttle, pilot_angle):
        # Default infos
        if fps is not None:
            self.add(f"current fps = {fps}")
        if user_mode == "user":
            self.add(f"user throttle = {self.slice(user_throttle)}")
            self.add(f"user angle = {self.slice(user_angle)}")
        elif user_mode == "local":
            self.add(f"pilot throttle = {self.slice(pilot_throttle)}")
            self.add(f"pilot angle = {self.slice(pilot_angle)}")
        elif user_mode == "local_angle":
            self.add(f"user throttle = {self.slice(user_throttle)}")
            self.add(f"pilot angle = {self.slice(pilot_angle)}")

        # Write infos
        new_img_arr = None
        if img_arr is not None:
            new_img_arr = img_arr.copy()

        if len(self.info_list) > 0:
            self.writeToImg(new_img_arr)
            self.info_list.clear()

        return new_img_arr
