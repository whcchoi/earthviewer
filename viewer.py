try:
    from Tkinter import *
except ImportError:
    from tkinter import *

import tkFileDialog
from PIL import Image, ImageTk
import sys
import os

try:
    import json
except ImportError:
    import simplejson as json

import tkMessageBox


class LoadImageApp:

    button_1 = "up"        # to indicate if button 1 is up or down
    draw = "move"           # value can be "dot","line", or "move"
    xold, yold = None, None
    viewport = (0,0)
    zoomcycle = 0
    MIN_ZOOM = -10
    MAX_ZOOM = 10

    # A list of saved dots
    dots = []

    def __init__(self,root,image_file):

        self.parent = root
        self.frame = Frame(root,bg='white')
        self.imageFile = image_file

        # Initialize the scaling/zoom table
        self.mux = {0 : 1.0}
        for n in range(1,self.MAX_ZOOM+1,1):
            self.mux[n] = round(self.mux[n-1] * 1.1, 5)

        for n in range(-1, self.MIN_ZOOM-1, -1):
            self.mux[n] = round(self.mux[n+1] * 0.9, 5)

        self.canvas = Canvas(self.frame,width=800,height=600,bg='white')

        # Create a blank canvas or an image canvas if a image file is provided
        if image_file:
            self.init_canvas(self.canvas,image_file)

        self.frame.pack(fill='both', expand=1)
        self.canvas.pack(fill='both', expand=1)

        self.file_opt = options = {}
        options['defaultextension'] = '.gif'
        options['filetypes'] = [('all files', '.*'), ('ppm files', '.ppm'), ('pgm files', '.pgm'), ('gif files', '.gif')]
        options['initialdir'] = '.'

        menubar = Menu(root)
        filemenu = Menu(menubar,tearoff=0)
        filemenu.add_command(label="Open", command=self.open_file)
        filemenu.add_command(label="Save", command=self.save_dots)
        filemenu.add_command(label="Exit", command=self.exit_app)
        menubar.add_cascade(label="File", menu=filemenu)

        drawmenu = Menu(menubar,tearoff=0)
        drawmenu.add_command(label="Move", command=self.move)
        drawmenu.add_command(label="Dot", command=self.dot)
        drawmenu.add_command(label="Line", command=self.line)
        menubar.add_cascade(label="Draw", menu=drawmenu)

        zoommenu = Menu(menubar, tearoff=0)
        zoommenu.add_command(label="Zoom In", command=self.zoomin)
        zoommenu.add_command(label="Zoom Out", command=self.zoomout)
        menubar.add_cascade(label="Zoom",menu=zoommenu)

        root.config(menu=menubar)

        self.canvas.bind("<MouseWheel>",self.zoomer)
        self.canvas.bind("<Motion>", self.motion)
        self.canvas.bind("<ButtonPress-1>", self.b1down)
        self.canvas.bind("<ButtonRelease-1>", self.b1up)

    def init_canvas(self, canvas, image_file):

        # Initialize these variables when a new image is opened
        self.button_1 = "up"        # to indicate if button 1 is up or down
        self.draw = "move"           # value can be "dot","line", or "move"
        self.xold, self.yold = None, None
        self.viewport = (0,0)
        self.zoomcycle = 0
        del self.dots[:]

        self.raw_image = Image.open(image_file)
        (width, height) = self.raw_image.size

        if width > 1000 or height > 1000:
            self.raw_image.thumbnail((800,600),Image.ANTIALIAS)
            (width, height) = self.raw_image.size
            print "Downsizing image to ", width, "x", height

        self.zoomed_image = self.raw_image

        # need to save a reference to the PhotoImage object, otherwise, image won't be shown
        self.p_img = ImageTk.PhotoImage(self.raw_image)

        # If image.dots file exist, load the dots
        f_name = (image_file.split(".",1))[0] + ".dots"

        if os.path.isfile(f_name):
            self.dotsFile = f_name

            with open(f_name) as data_file:
                self.dots = json.load(data_file)

        #print "Creating canvas: ", width, height, canvas
        canvas.config(width=width, height=height)
        canvas.delete("all")
        canvas.create_image(0,0,image=self.p_img, anchor="nw")

        #print "Dots=", self.dots
        # Draw the dots
        self.drawDots(canvas)


    def to_raw(self,(x,y)):

        # This function will translate the x,y coordinate from window to raw_image coordinate
        (vx, vy) = self.viewport
        return (int((x + vx)/ self.mux[self.zoomcycle]),int((y + vy)/ self.mux[self.zoomcycle]))

    def to_window(self, (x,y)):
        # This function will translate the x,y coordinate from raw_image coordinate to window coordinate
        (vx, vy) = self.viewport
        return (int(x * self.mux[self.zoomcycle]) - vx,int(y * self.mux[self.zoomcycle]) - vy)

    def drawDots(self, my_canvas):

        for a,b in self.dots:
            (x,y) = self.to_window((a,b))
            my_canvas.create_oval(x-2,y-2,x+2,y+2,fill="blue")


    def drawGrid(self):
        #print "Drawing Grid"
        centerX, centerY = self.raw_image.size[0]/2, self.raw_image.size[1]/2
        if self.raw_image.size[0] > self.raw_image.size[1]:
            d = self.raw_image.size[0]
        else:
            d = self.raw_image.size[1]

        a, b  = centerX - int(d/2), centerY - int(d/2)

        x = int(a * self.mux[self.zoomcycle]) - self.viewport[0]
        y = int(b * self.mux[self.zoomcycle]) - self.viewport[1]

        self.canvas.create_oval(centerX,centerY,centerX+2,centerY+2)
        self.canvas.create_oval(x,y,x+d,y+d)

    def scale_image(self):

        # resize the image based on the scaling factor (mux), update the self.zoomed_image
        raw_x, raw_y = self.raw_image.size
        new_w, new_h = int(raw_x * self.mux[self.zoomcycle]), int(raw_y * self.mux[self.zoomcycle])
        self.zoomed_image = self.raw_image.resize((new_w,new_h), Image.ANTIALIAS)

    def display_region(self, my_canvas):

        # only display the region of the zoomed_image starting at viewport and window size
        (x,y) = self.viewport
        w,h = self.frame.winfo_width(), self.frame.winfo_height()

        tmp = self.zoomed_image.crop((x,y,x+w,y+h))

        self.p_img = ImageTk.PhotoImage(tmp)
        my_canvas.config(bg="white")
        my_canvas.create_image(0,0,image=self.p_img, anchor="nw")

        # draw the saved dots
        self.drawDots(my_canvas)
        #self.drawGrid()

    ########################################################
    # The following are menu handlers
    ########################################################

    def open_file(self):
        fileHandle = tkFileDialog.askopenfile(mode='r', **self.file_opt)

        if fileHandle:
            self.imageFile = fileHandle.name
        else:
            print "Error opening file selected!"

        fileHandle.close()

        # Initialize the canvas with image file
        self.init_canvas(self.canvas,self.imageFile)

    def save_dots(self):

        # get the first part of the image file name
        f_name = (self.imageFile.split(".",1))[0] + ".dots"
        msg = "Saving dots as file " + f_name + "\n WARNING: Existing file will be overwritten!"
        re = tkMessageBox.askokcancel('Save File', msg)
        if re:
            f = open(f_name, 'w')
            json.dump(self.dots, f)
            f.close()

    def exit_app(self):
        sys.exit(0)

    def move(self):
        self.draw = "move"

    def dot(self):
        self.draw = "dot"

    def line(self):
        self.draw = "line"

    def zoomin(self):
        if self.zoomcycle < self.MAX_ZOOM:
            self.zoomcycle += 1
            self.scale_image()
            self.display_region(self.canvas)
        else:
            print "Max zoom reached!"

    def zoomout(self):
        if self.zoomcycle > self.MIN_ZOOM:
            self.zoomcycle -= 1
            self.scale_image()
            self.display_region(self.canvas)
        else:
            print "Min zoom reached!"

    #######################################################
    # The following are mouse event handlers
    #######################################################

    def zoomer(self,event):

        #print "---------------- zoomer --------------------"

        # Zoom image and update viewport based on mouse position, if no mouse position, defaults to middle of screen
        (x,y) = self.to_raw((event.x,event.y))

        if (event.delta > 0 and self.zoomcycle < self.MAX_ZOOM):
            self.zoomcycle += 1
        elif (event.delta < 0 and self.zoomcycle > self.MIN_ZOOM):
            self.zoomcycle -= 1
        else:
            print "Max/Min zoom reached!"
            return

        self.scale_image()

        self.viewport = (int(x * self.mux[self.zoomcycle]) - x, int(y * self.mux[self.zoomcycle]) - y)
        self.display_region(self.canvas)


    def b1down(self,event):
        if self.draw is "move" or self.draw is "line":
            self.button_1 = "down"       # you only want to draw when the button is down
                                            # because "Motion" events happen -all the time-
        elif self.draw is "dot":
            event.widget.create_oval(event.x-2,event.y-2,event.x+2,event.y+2,fill="blue")

            # save the dot in the raw_image aspect ratio
            self.dots.append(self.to_raw((event.x,event.y)))

    def b1up(self,event):
        self.button_1 = "up"
        self.xold = None           # reset the line when you let go of the button
        self.yold = None

    def motion(self,event):
        if self.button_1 == "down":
            if self.xold is not None and self.yold is not None:
                if self.draw is "line":
                    # here's where you draw it. smooth. neat.
                    event.widget.create_line(self.xold,self.yold,event.x,event.y,smooth=TRUE,fill="blue",width=5)

                elif self.draw is "move":
                    # update the viewport
                    self.viewport = (self.viewport[0] - (event.x - self.xold), self.viewport[1] - (event.y - self.yold))
                    self.display_region(self.canvas)

            self.xold = event.x
            self.yold = event.y

# Main Program, checks to see if image file is provided in command line, if not, it will be opened via menu File->Open File

if __name__ == '__main__':
    root = Tk()
    root.title("Image Viewer")
    image_file = None

    if len(sys.argv) > 1:
        if os.path.isfile(sys.argv[1]):
            image_file = sys.argv[1]
        else:
            exit_string = "Image File " + sys.argv[1] + " doesn't exist!"
            sys.exit(exit_string)

    # Create and open app, if image_file is provided, open the image as well
    App = LoadImageApp(root,image_file)

    root.mainloop()