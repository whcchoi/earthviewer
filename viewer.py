from Tkinter import *
import tkFileDialog
from PIL import Image, ImageTk
import sys
import os

class LoadImageApp:

    button_1 = "up"        # to indicate if button 1 is up or down
    draw = "move"           # value can be "dot","line", or "move"
    xold, yold = None, None
    viewport = (0,0)
    zoomcycle = 0

    # A list of saved dots
    dots = []

    def __init__(self,root,image_file):

        self.parent = root
        self.frame = Frame(root)

        self.mux = {-9:0.1,-8:0.2,-7:0.3,-6:0.4,-5:0.5,-4:0.6,-3:0.7,-2:0.8,-1:0.9,0:1.0}

        for n in range(1,11,1):
            self.mux[n] = round(self.mux[n-1] + 0.3,2)


        if not image_file:
            self.canvas = Canvas(self.frame, width=800, height=600)
        else:

            self.raw_image = Image.open(image_file)
            self.zoomed_image = self.raw_image

            # need to save a reference to the PhotoImage object, otherwise, image won't be shown
            self.p_img = ImageTk.PhotoImage(self.raw_image)
            self.canvas = Canvas(self.frame, width=self.p_img.width(),height=self.p_img.height())
            #self.canvas.config(background="red")

            self.canvas.create_image(0,0,image=self.p_img, anchor="nw")
            #self.drawGrid()


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

    def to_raw(self,(x,y)):

        # This function will translate the x,y coordinate from window to raw_image coordinate
        (vx, vy) = self.viewport
        return (int((x + vx)/ self.mux[self.zoomcycle]),int((y + vy)/ self.mux[self.zoomcycle]))

    def to_window(self, (x,y)):
        # This function will translate the x,y coordinate from raw_image coordinate to window coordinate
        (vx, vy) = self.viewport
        return (int(x * self.mux[self.zoomcycle]) - vx,int(y * self.mux[self.zoomcycle]) - vy)

    def drawDots(self):

        #print self.dots
        for a,b in self.dots:
            #(x,y) = self.to_window((a,b))
            #self.canvas.create_oval(x,y,x+5,y+5,fill="red")
            x = int(a * self.mux[self.zoomcycle]) - self.viewport[0]
            y = int(b * self.mux[self.zoomcycle]) - self.viewport[1]
            self.canvas.create_oval(x,y,x+5,y+5,fill="red")


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

    def display_region(self):

        # only display the region of the zoomed_image starting at viewport and window size
        (x,y) = self.viewport
        w,h = self.frame.winfo_width(), self.frame.winfo_height()

        #print "Displaying Region: ", x,y,x+w,y+h
        tmp = self.zoomed_image.crop((x,y,x+w,y+h))

        self.p_img = ImageTk.PhotoImage(tmp)
        self.canvas.create_image(0,0,image=self.p_img, anchor="nw")

        # draw the saved dots
        self.drawDots()
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

        # open the image
        self.raw_image = Image.open(self.imageFile)
        self.zoomed_image = self.raw_image

        # need to save a reference to the PhotoImage object, otherwise, image won't be shown
        self.p_img = ImageTk.PhotoImage(self.raw_image)
        self.canvas.create_image(0,0,image=self.p_img, anchor="nw")

    def save_dots(self):
        print "Save the Dots"

    def exit_app(self):
        sys.exit(0)

    def move(self):
        self.draw = "move"

    def dot(self):
        self.draw = "dot"

    def line(self):
        self.draw = "line"

    def zoomin(self):
        print "Zoom In"
        if self.zoomcycle < 10:
            self.zoomcycle += 1
            self.scale_image()
            self.display_region()

    def zoomout(self):
        print "Zoom Out"

    #######################################################
    # The following are mouse event handlers
    #######################################################

    def zoomer(self,event):

        #print "---------------- zoomer --------------------"

        # Zoom image and update viewport based on mouse position, if no mouse position, defaults to middle of screen
        #print "---------------------------"
        #print "Mouse Position in zoomer: ", event.x, event.y
        #print "Viewport in zoomer:", self.viewport
        #print "Old Viewport: ", self.viewport
        (x,y) = self.to_raw((event.x,event.y))
        #print "Mouse position in raw: ", x,y

        if (event.delta > 0 and self.zoomcycle < 10):
            self.zoomcycle += 1
        elif (event.delta < 0 and self.zoomcycle > -9):
            self.zoomcycle -= 1
        else:
            print "Max/Min zoom reached!"
            return

        #print "Zoomcycle", self.zoomcycle
        self.scale_image()

        self.viewport = (int(x * self.mux[self.zoomcycle]) - x, int(y * self.mux[self.zoomcycle]) - y)
        #new_x = int(self.mux[self.zoomcycle]*(self.viewport[0]-event.x)) + event.x
        #new_y = int(self.mux[self.zoomcycle]*(self.viewport[1]-event.y)) + event.y

        #print "Viewport after zoom:", self.viewport
        #print "New Calculation: ", new_x, new_y

        # update the viewport as well
        #self.viewport = (int(event.x * self.mux[self.zoomcycle]) - event.x, int(event.y * self.mux[self.zoomcycle]) - event.y)
        #print "New Viewport = ", self.viewport
        self.display_region()


    def b1down(self,event):
        if self.draw is "move" or self.draw is "line":
            self.button_1 = "down"       # you only want to draw when the button is down
                                            # because "Motion" events happen -all the time-
        elif self.draw is "dot":
            #print "-------------------"
            #print "Mouse position in Dots=", event.x, event.y
            #print "Viewport in dots:", self.viewport
            event.widget.create_oval(event.x,event.y,event.x+5,event.y+5,fill="blue")

            # save the dot in the raw_image aspect ratio
            self.dots.append(self.to_raw((event.x,event.y)))
            #print "Dots = ", self.dots

    def b1up(self,event):
        self.button_1 = "up"
        self.xold = None           # reset the line when you let go of the button
        self.yold = None

    def motion(self,event):
        if self.button_1 == "down":
            if self.xold is not None and self.yold is not None:
                if self.draw is "line":
                    # here's where you draw it. smooth. neat.
                    #print "Draw Line: ", self.xold, self.yold, event.x, event.y
                    event.widget.create_line(self.xold,self.yold,event.x,event.y,smooth=TRUE,fill="blue",width=5)

                elif self.draw is "move":
                    #print "Panning: old = ", self.xold, self.yold, "new = " , event.x, event.y
                    # update the viewport
                    self.viewport = (self.viewport[0] - (event.x - self.xold), self.viewport[1] - (event.y - self.yold))
                    #print "Viewport = ", self.viewport
                    self.display_region()

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