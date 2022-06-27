import numpy as np
import yaqc
import matplotlib.pyplot as plt
import matplotlib.animation as animation
import matplotlib
import time

cam = yaqc.Client(39005)
cam.measure()
time.sleep(0.5)
sl = (slice(None, -1, None), slice(None, -2, None))

fig = plt.figure()

ax = plt.subplot(111)
ax_im = plt.imshow(
    cam.get_measured()["img"][sl], origin="lower", norm=matplotlib.colors.Normalize()
)


def update_img(y):
    ax_im.set_data(y)
    plt.draw()


def data_gen():
    index = 0
    while True:
        cam.measure()
        while True:
            measured = cam.get_measured()
            if index < measured["measurement_id"]:
                index = measured["measurement_id"]
                yield cam.get_measured()["img"][sl]
                break
            else:
                time.sleep(0.1)


ani = animation.FuncAnimation(fig, update_img, data_gen, interval=100)
plt.show()
