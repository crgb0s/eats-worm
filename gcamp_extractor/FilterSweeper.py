import copy
from magicgui import magicgui
from magicgui.widgets import FloatSlider, Slider
import napari
from napari.layers import Image
from .segfunctions import *
#import skimage.data
#import skimage.filters


class FilterSweeper:
    """
    Provides a GUI for parameter selection for our filtering and thresholding flow and tracks selected parameter values.
    
    Attributes
    ---------
    gaussian: tuple
        selected gaussian filter parameters
    median: int
        selected median filter parameters
    quantile: float
        selected threshold
    """
    def __init__(self, stacks, params=None):
        """
        Arguments
        ---------
        stacks: list
            a list of image volumes, each being a numpy.ndarray with ZYX
            dimension order.
            (NOTE: array data needs to be cv2 compliant for segtools to work.
            np.uint16 seems to be one valid option)
        params: dict
            dictionary of filter parameters
        """
        self.stacks = stacks
        if params is None:
            params = {}

        # gaussian
        self.width_x_val = params.get('width_x_val', 3)
        self.width_y_val = params.get('width_y_val', 3)
        self.width_z_val = params.get('width_z_val', 3)
        self.sigma_x = params.get('sigma_x', 1)
        self.sigma_y = params.get('sigma_y', 1)
        self.sigma_z = params.get('sigma_z', 1)
        # median filter
        self.median_sizes = params.get('median_sizes', [1, 3, 5])
        self.median_index = params.get('median_index', 1)
        # quantile
        self.quantile = params.get('quantile', 0.9)

    @classmethod
    def from_extractor(cls, e, timepoints=1):
        """instantiate from an Extractor object

        Arguments
        ---------
        e: Extractor
            extractor object containing the video/image stack stack for which you want select parameters
        timepoints: int
            specifies number of timepoints for which each parameter combination will be evaluated. by default, only the first timepoint is used.
            timepoint 0 is always the first timepoint of the recording.
        """
        try:
            if len(e.gaussian) == 4:
                width_x_val = width_y_val = e.gaussian[0]
                width_z_val =e.gaussian[2]
                sigma_x = sigma_y = e.gaussian[1]
                sigma_z = e.gaussian[3]
            elif len(e.gaussian) == 6: 
                width_x_val = e.gaussian[0]
                width_y_val = e.gaussian[1]
                width_z_val = e.gaussian[4]
                sigma_x = e.gaussian[2]
                sigma_y = e.gaussian[3]
                sigma_z = e.gaussian[5]
        except:
            width_x_val = 1
            width_y_val = 1
            width_z_val = 1
            sigma_x = e.gaussian[2]
            sigma_y = e.gaussian[3]
            sigma_z = e.gaussian[5]
        try:
            quantile = e.quantile
        except:
            quantile = 0.99
        median_sizes = [1, 3, 5]
        try:
            median_index = median_sizes.index(e.median)
        except:
            median_index = 1

        # pack up parameters
        params = dict(
            width_x_val=width_x_val,
            width_y_val=width_y_val,
            width_z_val=width_z_val,
            sigma_x=sigma_x,
            sigma_y=sigma_y,
            sigma_z=sigma_z,
            quantile=quantile,
            median_sizes=median_sizes,
            median_index=median_index
        )

        # pull out image volumes
        stacks = []
        for i in range(timepoints):
            im1 = e.im.get_t(t=i)
            im1_unfiltered = copy.deepcopy(im1)
            stacks.append(im1_unfiltered)
        return cls(stacks=stacks, params=params)

    # adapted from example at https://magicgui.readthedocs.io/en/latest/examples/napari_parameter_sweep/
    def sweep_parameters(self):
        """
        use napari and magicgui to do a parameter sweep for our filtering and thresholding flow. upon napari window close, return dict of selected parameters.
        """
        with napari.gui_qt():
            # stacks = []
            # for i in range(timepoints):
            #     im1 = self.e.im.get_t(t=i)
            #     im1_unfiltered = copy.deepcopy(im1)
            #     stacks.append(im1_unfiltered)
            viewer = napari.Viewer()
            viewer.add_image(np.array(self.stacks), name="worm", blending='additive', interpolation='bicubic')

            @magicgui(
                auto_call=True,
                quantile={"widget_type": FloatSlider, "min": 0.5, "max": 1},
                median_index={"widget_type": Slider, "min": 0, "max": 2},
                width_x={"widget_type": Slider, "min": 0, "max": 24},
                width_y={"widget_type": Slider, "min": 0, "max": 24},
                width_z={"widget_type": Slider, "min": 0, "max": 24},
                sigma_x={"widget_type": FloatSlider, "max": 6},
                sigma_y={"widget_type": FloatSlider, "max": 6},
                sigma_z={"widget_type": FloatSlider, "max": 6},
            )
            def filter_and_threshold(layer: Image, quantile: float = self.quantile, median_index: int = self.median_index, width_x: int = (self.width_x_val - 1) // 2, width_y: int = (self.width_y_val - 1) // 2, width_z: int = (self.width_z_val - 1) // 2, sigma_x: float = self.sigma_x, sigma_y: float = self.sigma_y, sigma_z: float = self.sigma_z) -> Image:
                """Apply a gaussian blur to ``layer``."""
                if layer:
                    # todo: the order used here does not match the documentation in sefgunctions. change either order or documentation in segfunctions
                    filtered_and_thresholded = []
                    self.quantile = quantile
                    self.median_index = median_index
                    self.width_x_val = 2 * width_x + 1
                    self.width_y_val = 2 * width_y + 1
                    self.width_z_val = 2 * width_z + 1
                    self.sigma_x = sigma_x
                    self.sigma_y = sigma_y
                    self.sigma_z = sigma_z
                    for stack in self.stacks:
                        blurred = gaussian3d(copy.deepcopy(stack), (self.width_x_val, self.width_y_val, self.sigma_x, self.sigma_y, self.width_z_val, self.sigma_z))
                        filtered = medFilter2d(blurred, self.median_sizes[self.median_index])
                        thresholded = filtered > np.quantile(layer.data, self.quantile)
                        filtered_and_thresholded.append(thresholded)
                    return np.array(filtered_and_thresholded)

            gui = filter_and_threshold.Gui()
            viewer.window.add_dock_widget(gui)
            viewer.layers.events.changed.connect(lambda x: gui.refresh_choices("layer"))
            viewer.layers["filter_and_threshold result"].colormap = "cyan"
            viewer.layers["filter_and_threshold result"].blending = "additive"
            viewer.layers["filter_and_threshold result"].interpolation = "bicubic"

        final_params = {"gaussian": (self.width_x_val, self.width_y_val, self.sigma_x, self.sigma_y, self.width_z_val, self.sigma_z), "median": self.median_sizes[self.median_index], "quantile": self.quantile}
        self.gaussian, self.median = final_params["gaussian"], final_params["median"]
        print("final parameters from sweep: ", final_params)
