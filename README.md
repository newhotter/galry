Galry: high performance interactive visualization package in Python
===================================================================

Galry is a **high performance interactive visualization package in 
Python** based on OpenGL.
It allows to interactively visualize very large plots (tens of millions of
points) in real time, by using the graphics card as much as possible.

Galry's high-level interface is directly inspired by Matplotlib and Matlab.
The low-level interface can be used to write complex interactive visualization
GUIs with Qt that deal with large 2D/3D datasets.

Visualization capabilities of Galry are not restricted to plotting, and 
include textures, 3D meshes, graphs, shapes, etc. Custom shaders can also be
written for advanced uses.

[Click here to go to the FAQ](https://github.com/rossant/galry/blob/master/docs/faq.md).

### Note

The library will be entirely rewritten in the coming months
in the context of the [vispy collaborative project](https://github.com/vispy/vispy).
The goal is to share common building blocks with other visualization libraries
(visvis, pyqtgraph, glumpy...). The low-level API will change and we suggest not
to use it in production for now.


User survey
-----------

[**We'd be very grateful if you could fill in this really short form if you're interested in Galry!**](https://docs.google.com/spreadsheet/viewform?formkey=dE5qZldRN3pvY2NEaXRhb2J4UDhoYWc6MQ#gid=0)


Gallery
-------

![Multiple plots](https://raw.github.com/rossant/galry/master/images/thumbnails/img0.jpg)
![Multiple bar plots](https://raw.github.com/rossant/galry/master/images/thumbnails/img1.jpg)
![Dynamic fractal](https://raw.github.com/rossant/galry/master/images/thumbnails/img5.jpg)

[Click here to see all screenshots and videos](https://github.com/rossant/galry/blob/master/docs/gallery.md).


Installation
------------

### Requirements

  * Galry should work on any platform (Window/Linux/MacOS).
  * Mandatory dependencies include:
  
      * Python 2.7
      * Numpy
      * PyQt4 or PySide with the OpenGL bindings
      * PyOpenGL
      * matplotlib

  * Your graphics card drivers must be up-to-date and support **OpenGL 2.1**.

Galry is licensed under the BSD license.

### Installation procedure

  * [Download the package](http://galry.rossant.net/galry-0.1.0.rc1.zip).
  * Extract it.
  * Run in a console:
  
        python setup.py install
        
  * Test it:
      
        from galry import *
        from numpy.random import randn
        plot(randn(3, 10000))
        show()
        
  * You should see three overlayed random signals. You can navigate with the
    mouse and the keyboard. Press `H` to see all available actions.

[More details](https://github.com/rossant/galry/wiki/Installation).

### Development version (expert users)

  * Clone the repository:
  
        git clone https://github.com/rossant/galry.git
  
  * Install Galry with `pip` so that external packages are automatically
    updated (like `qtools` which contains some Qt-related utility functions):
  
        pip install -r requirements.txt


Quick links
-----------

  * [What's new?](https://github.com/rossant/galry/blob/master/CHANGES.md)
  * [Installation page](https://github.com/rossant/galry/wiki/Installation)
  * [User Manual](https://github.com/rossant/galry/blob/master/docs/manual.md)
  * [Tutorials](https://github.com/rossant/galry/tree/master/tutorials)
  * [Examples](https://github.com/rossant/galry/tree/master/examples)
  * [Gallery](https://github.com/rossant/galry/blob/master/docs/gallery.md)
  * [Benchmarks wiki](https://github.com/rossant/galry/wiki/Benchmarks)
  * [FAQ](https://github.com/rossant/galry/blob/master/docs/faq.md)
  * [Source code](https://github.com/rossant/galry)
  * [Galry Users Google Group](https://groups.google.com/forum/?fromgroups#!forum/galry-users)
  * [Contact](http://cyrille.rossant.net)
  
  
