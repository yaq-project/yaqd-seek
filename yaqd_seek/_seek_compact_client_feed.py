import numpy as np
import time
import sys
import yaqc  # type: ignore
import matplotlib.pyplot as plt  # type: ignore
import matplotlib.animation as animation  # type: ignore
from mpl_toolkits.axes_grid1 import make_axes_locatable  # type: ignore
import matplotlib  # type: ignore


def gen_rotator(angle: int):
    reverse = slice(None, None, -1)
    none = slice(None, None, None)
    axes = [0, 1] if angle in [0, 180] else [1, 0]
    if angle == 0:
        sls = (none, none)
    elif angle == 90:
        sls = (reverse, none)
    elif angle == 180:
        sls = (reverse, reverse)
    elif angle == 270:
        sls = (none, reverse)
    else:
        raise ValueError
    return lambda x: x[sls].transpose(*axes)


def plot_feed(port, host=None, bg_subtract=False, rotation=0):
    """
    Parameters
    ----------
    port : int-like
        daemon port
    host : str
        daemon host.  Defaults to localhost
    bg_subtract : boolean-like
        if True, stores the first collected image as a background and subtracts future acquistions from this reference
    rotation : int-like
        CCW rotation of image.  Either 0, 90, 180, 275
    """
    if host is None:
        cam = yaqc.Client(int(port))
    else:
        cam = yaqc.Client(int(port), host=host)
    rotator = gen_rotator(int(rotation))
    cam.measure()
    time.sleep(0.5)
    ref = cam.get_measured()["img"] if bg_subtract else 0

    fig = plt.figure()

    ax = plt.subplot()
    im0 = cam.get_measured()["img"] - ref
    ax_im = plt.imshow(rotator(im0), origin="lower", norm=matplotlib.colors.Normalize())
    divider = make_axes_locatable(ax)
    cax = divider.append_axes("right", size="5%", pad=0.05)
    cbar = plt.colorbar(ax_im, cax=cax)
    cbar.set_ticks(np.linspace(np.nanmin(im0), np.nanmax(im0), 6))
    for axes in [ax.axes, cax.axes]:
        axes.tick_params(labelsize=16)

    def update_img(y):
        y -= ref
        ax_im.set_data(rotator(y))
        ax_im.set_norm(matplotlib.colors.Normalize(y.min(), y.max()))
        cbar_ticks = np.linspace(np.nanmin(y), np.nanmax(y), num=6, endpoint=True)
        cbar.set_ticks(cbar_ticks)
        cbar.draw_all()
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
    ani = plot_feed(port, **dict(arg.split("=") for arg in sys.argv[2:]))
    plt.show()
    # sys.exit(app.exec_())


if __name__ == "__main__":
    main()
