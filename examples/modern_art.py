from galry import *
import numpy.random as rdn

class ArtPaintManager(PaintManager):
    def initialize(self):
        # random positions
        positions = .25 * rdn.randn(1000, 2)
        # random colors
        colors = rdn.rand(len(positions),4)
        # add plot with triangles, 3 consecutive points define a single triangle
        self.add_plot(positions[:,0], positions[:,1], colors,
                      primitive_type=PrimitiveType.Triangles)

if __name__ == '__main__':
    # create window
    window = show_basic_window(paint_manager=ArtPaintManager,
                                constrain_ratio=True,
                                antialiasing=True)