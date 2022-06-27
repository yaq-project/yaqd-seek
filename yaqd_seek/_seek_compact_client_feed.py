import numpy as np
import yaqc
import matplotlib.pyplot as plt
import matplotlib.animation as animation
import matplotlib
import time

cam = yaqc.Client(39005)
cam.measure()
time.sleep(0.5)

fig = plt.figure()

ax = plt.subplot(111)
ax_im = plt.imshow(cam.get_measured()["img"], origin="lower", norm = matplotlib.colors.Normalize())

def update_img(y):
    ax_im.set_data(y)
    ax_im.set_norm(matplotlib.colors.Normalize())
    plt.draw()

def data_gen():
    index = 0
    while True:
        cam.measure()
        while True:
            measured = cam.get_measured()
            if index < measured["measurement_id"]:
                index = measured["measurement_id"]
                yield cam.get_measured()["img"]
                break
            else:
                time.sleep(0.1)

ani = animation.FuncAnimation(fig, update_img, data_gen, interval=100)
plt.show()