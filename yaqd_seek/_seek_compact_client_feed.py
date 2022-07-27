import numpy as np
import time
import sys
import yaqc  # type: ignore
import matplotlib.pyplot as plt  # type: ignore
import matplotlib.animation as animation  # type: ignore
import matplotlib  # type: ignore


def plot_feed(port, host=None):
    if host is None:
        cam = yaqc.Client(port)
    else:
        cam = yaqc.Client(port, host=host)
    cam.measure()
    time.sleep(0.5)

    fig = plt.figure()

    ax = plt.subplot(111)
    im0 = cam.get_measured()["img"]
    ax_im = plt.imshow(im0, origin="lower", norm = matplotlib.colors.Normalize())

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
    return ani


def main():
    """Initialize application and main window."""
    port = int(sys.argv[1])    
    host = None if len(sys.argv)==2 else argv[2]
    ani = plot_feed(port, host)
    plt.show()
    # sys.exit(app.exec_())


if __name__ == "__main__":
    main()
