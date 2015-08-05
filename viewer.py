try:
    from Tkinter import *
except ImportError:
    from tkinter import *

from PIL import Image, ImageTk
import sys
import os
import math
import pickle
import tkFileDialog
import tkMessageBox


####################################################################
# Class: LoadImageApp
# Main App, created in Main()
####################################################################
class LoadImageApp:

    button_1 = "up"        # to indicate if button 1 is up or down
    tool = "move"          # value can be "move", "dot", "line", "select", or "grid"
    xold, yold = None, None
    viewport = (0,0)       # Use for zoom and pan, this is adjusted whenever image is zoom/pan
    zoomcycle = 0          # from -10 to 10, 0 is no zoom
    MIN_ZOOM = -10
    MAX_ZOOM = 10
    raw_image = None       # a reference to the raw image (of class Image)
    zoomed_image = None    # reference to the zoomed image (of class Image)

    # A list of saved dots (in tuples)
    dots = []

    ####################################################################
    # Function: __init__
    # Args:  root           parent
    #        image_file     name of image file
    # Returns:  None
    ####################################################################
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

        # Create a blank canvas of size 800*600
        self.canvas = Canvas(self.frame,width=800,height=600,bg='white')

        # If image file is provided, this will create the image in the canvas
        if image_file:
            self.init_canvas(self.canvas,image_file)

        self.frame.pack(fill='both', expand=1)
        self.canvas.pack(fill='both', expand=1)

        # The following are for file open dialogs window settings
        self.file_opt = options = {}
        options['defaultextension'] = '.gif'
        options['filetypes'] = [('all files', '.*'),
                                ('ppm files', '.ppm'),
                                ('pgm files', '.pgm'),
                                ('gif files', '.gif'),
                                ('jpg files', '.jpg'),
                                ('jpeg files', '.jpeg')]
        options['initialdir'] = '.'

        # Menu items
        menubar = Menu(root)
        filemenu = Menu(menubar,tearoff=0)
        filemenu.add_command(label="Open", command=self.open_file)
        filemenu.add_command(label="Save", command=self.save_dots)
        filemenu.add_command(label="Exit", command=self.exit_app)
        menubar.add_cascade(label="File", menu=filemenu)

        drawmenu = Menu(menubar,tearoff=0)
        drawmenu.add_command(label="Move", command=self.move)
        drawmenu.add_command(label="Select & Delete", command=self.select)
        drawmenu.add_command(label="Draw Circle Grid", command=self.grid)
        drawmenu.add_command(label="Draw Dot", command=self.dot)
        drawmenu.add_command(label="Draw Line", command=self.line)
        menubar.add_cascade(label="Tool", menu=drawmenu)

        zoommenu = Menu(menubar, tearoff=0)
        zoommenu.add_command(label="Zoom In", command=self.zoomin)
        zoommenu.add_command(label="Zoom Out", command=self.zoomout)
        menubar.add_cascade(label="Zoom",menu=zoommenu)

        # Attach created menu to root window
        root.config(menu=menubar)

        # Create the status bar on the bottom to show the X,Y coords (in respect to RAW image coords)
        self.status = Label(root, text="X,Y", bd=1, relief=SUNKEN, anchor=W)
        self.status.pack(side=BOTTOM, fill=X)

        # Event binding
        self.canvas.bind("<MouseWheel>",self.zoomer)
        self.canvas.bind("<Motion>", self.motion)
        self.canvas.bind("<ButtonPress-1>", self.b1down)
        self.canvas.bind("<ButtonRelease-1>", self.b1up)
        self.canvas.bind("<Configure>", self.resize_window)

    ####################################################################
    # Function: init_canvas(), initialize the canvas with the image provided
    # Args:  canvas
    #        image_file     name of image file
    # Returns:  None
    ####################################################################
    def init_canvas(self, canvas, image_file):

        # Reset these variables when a new image is opened
        self.button_1 = "up"
        self.tool = "move"
        self.xold, self.yold = None, None
        self.viewport = (0,0)
        self.zoomcycle = 0
        del self.dots[:]

        self.raw_image = Image.open(image_file)
        (width, height) = self.raw_image.size

        # If image is larger than 1000 pixels, resize it to less than 800 x 600
        if width > 1000 or height > 1000:
            self.raw_image.thumbnail((800,600),Image.ANTIALIAS)
            (width, height) = self.raw_image.size
            print "Downsizing image to ", width, "x", height

        self.zoomed_image = self.raw_image

        # need to save a reference to the PhotoImage object, otherwise, image won't be shown
        self.p_img = ImageTk.PhotoImage(self.raw_image)

        # If image.olv file exist, load the dots
        f_name = (image_file.split(".",1))[0] + ".olv"

        if os.path.isfile(f_name):
            self.dotsFile = f_name

            with open(f_name) as data_file:
                self.dots = pickle.load(data_file)
                #print "DOTS (init) = ", self.dots

        # Change the size of the canvas to new width and height based on image size
        canvas.config(width=width, height=height)

        # Remove all the previous canvas items
        canvas.delete("all")
        canvas.create_image(0,0,image=self.p_img, anchor="nw")

        # Find center of image and radius
        self.center = (int(width/2), int(height/2))
        self.radius = int(math.sqrt(self.center[0] * self.center[0] + self.center[1] * self.center[1]))

        # Draw the dots and grids on the canvas as well
        self.drawDots(canvas)
        #self.drawGrid(canvas)

    # To check if a dot coords is in the list, the coords could be off by 1 due to rounding from to_raw()
    def dot_in_list(self,(x,y)):

        for a,b in self.dots:
            if math.fabs(x-a) <= 2 and math.fabs(y-b) <= 2:
                #print "Dots FOund in list: ", (a,b)
                return (a,b)


    def to_raw(self,(x,y)):

        # This function will translate the x,y coordinate from window to raw_image coordinate
        (vx, vy) = self.viewport
        return (int((x + vx)/ self.mux[self.zoomcycle]),int((y + vy)/ self.mux[self.zoomcycle]))

    def to_window(self, (x,y)):
        # This function will translate the x,y coordinate from raw_image coordinate to window coordinate
        (vx, vy) = self.viewport
        return (int(x * self.mux[self.zoomcycle]) - vx,int(y * self.mux[self.zoomcycle]) - vy)

    def drawDots(self, my_canvas):
        #print "DOTS (drawDots) = ", self.dots

        for (a,b) in self.dots:
            (x,y) = self.to_window((a,b))
            my_canvas.create_oval(x-2,y-2,x+2,y+2,fill="blue")

    def drawGrid(self,my_canvas):

        (wX,wY) = self.to_window(self.center)
        wR = self.radius * self.mux[self.zoomcycle]

        x = wX - wR
        y = wY - wR

        my_canvas.create_oval(x,y,x+(2*wR),y+(2*wR))

        # Draw spokes every 10 degrees
        for n in range(10,370,10):
            rX = self.center[0] + int(self.radius * math.cos(math.radians(n)))
            rY = self.center[1] + int(self.radius * math.sin(math.radians(n)))
            pX,pY = self.to_window((rX,rY))
            my_canvas.create_line(wX,wY,pX,pY)

    def scale_image(self):

        # resize the image based on the scaling factor (mux), update the self.zoomed_image
        raw_x, raw_y = self.raw_image.size
        new_w, new_h = int(raw_x * self.mux[self.zoomcycle]), int(raw_y * self.mux[self.zoomcycle])
        self.zoomed_image = self.raw_image.resize((new_w,new_h), Image.ANTIALIAS)

    def display_region(self, my_canvas):

        my_canvas.delete("all")

        # only display the region of the zoomed_image starting at viewport and window size
        (x,y) = self.viewport
        w,h = self.frame.winfo_width(), self.frame.winfo_height()

        tmp = self.zoomed_image.crop((x,y,x+w,y+h))

        self.p_img = ImageTk.PhotoImage(tmp)
        my_canvas.config(bg="white")
        my_canvas.create_image(0,0,image=self.p_img, anchor="nw")

        # draw the saved dots
        self.drawDots(my_canvas)
        #print my_canvas.find_withtag("all")
        #self.drawGrid(my_canvas)

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

        #print "DOTS(save_dots) = ", self.dots
        # get the first part of the image file name
        f_name = (self.imageFile.split(".",1))[0] + ".olv"
        msg = "Saving dots as file " + f_name + "\n WARNING: Existing file will be overwritten!"
        re = tkMessageBox.askokcancel('Save File', msg)
        if re:
            f = open(f_name, 'wb')
            pickle.dump(self.dots, f)
            f.close()

    def exit_app(self):
        sys.exit(0)

    def move(self):
        self.tool = "move"

    def select(self):
        self.tool = "select"

    def grid(self):
        self.drawGrid(self.canvas)

    def dot(self):
        self.tool = "dot"

    def line(self):
        self.tool = "line"

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
        if self.tool is "dot":

            event.widget.create_oval(event.x-2,event.y-2,event.x+2,event.y+2,fill="blue")

            # save the dot in the raw_image aspect ratio
            self.dots.append(self.to_raw((event.x,event.y)))
        else:
            # Remember the first mouse down coors (for "select" function)
            self.select_X, self.select_Y = event.x, event.y
            self.button_1 = "down"       # you only want to draw when the button is down
                                            # because "Motion" events happen -all the time-

    def b1up(self,event):
        self.button_1 = "up"
        self.xold = None           # reset xold and yold when you let go of the button
        self.yold = None

        # Handles dot deletion here, use canvas.find_enclosed to find items contained within the selection rectangles
        if self.tool is "select":
            items = event.widget.find_enclosed(self.select_X, self.select_Y, event.x, event.y)

            # delete the rectangle since we already found all items enclosed in it
            rect = event.widget.find_withtag("selection_rectangle")
            if rect:
                event.widget.delete(rect)

            # Change the color of the selected dots to "red"
            for i in items:
                event.widget.itemconfig(i,fill="red")

            # If there's canvas items found, (Only works on dots), pop up an dialog to confirm the deletion
            if items:
                result = tkMessageBox.askokcancel("Confirm deletion?","Press OK to delete selected dot(s)!")

                # If user confirms deletion
                if result:
                    # Delete the selected dots on the canvas, and remove it from "dots" list
                    for i in items:
                        xy = event.widget.coords(i)
                        #print xy
                        x = (xy[0]+xy[2])/2
                        y = (xy[1]+xy[3])/2
                        #print "X and Y = ", x, y
                        raw_xy = self.to_raw((x,y))
                        #print "Raw X, Y = ", raw_xy
                        #print "DOTS = ", self.dots

                        # Since the "to_raw" may make dots value a bit off, therefore, the dot_in_list function will
                        # accommodate the coords by +1 to -1 pixel value
                        real_dot = self.dot_in_list(raw_xy)

                        # remove the dots from the list
                        if real_dot:
                            self.dots.remove(real_dot)
                            event.widget.delete(i)

    # Handles mouse movement, depends on what's the current mouse function
    def motion(self,event):

        # Only do anything if mouse button (left button) is clicked first.
        if self.button_1 == "down":
            if self.xold is not None and self.yold is not None:

                # Handles different functions differently
                if self.tool is "line":
                    # here's where you draw line. smooth. neat.
                    event.widget.create_line(self.xold,self.yold,event.x,event.y,smooth=TRUE,fill="blue",width=5)

                elif self.tool is "move":
                    # Panning
                    # update the viewport and redraw the canvas
                    self.viewport = (self.viewport[0] - (event.x - self.xold), self.viewport[1] - (event.y - self.yold))
                    self.display_region(self.canvas)

                elif self.tool is "select":
                    # Draw a dotted rectangle to show the area selected
                    rect = event.widget.find_withtag("selection_rectangle")
                    if rect:
                        event.widget.delete(rect)
                    event.widget.create_rectangle(self.select_X,self.select_Y,event.x,event.y,fill="",dash=(4,2),tag="selection_rectangle")

            self.xold = event.x
            self.yold = event.y

        # update the status bar with x,y values, status bar always shows "RAW" coordinates
        (rX,rY) = self.to_raw((event.x,event.y))
        str = "(", rX , ",", rY, ")"
        self.status.config(text=str)

    def resize_window(self, event):
        if self.zoomed_image:
            self.display_region(self.canvas)

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