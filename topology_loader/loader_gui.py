import tkinter as tk
from PIL import Image, ImageTk
import os
from topology_loader import topology_loader

class loader_gui(tk.Frame):

    """
    GUI for the topology loader to choose a topology for the simulation.
    """

    def __init__(self, master):
        super().__init__(master)
        master.title("Topology loader")
        self.selected_topo = ""
        self.loader = topology_loader()
        self.pack()
        self.welcome_string = "Topology loader"
        self.create_widgets()

    def create_widgets(self):
        """
        Creates the GUI.
        """
        lst = self.loader.get_topos()
        self.selection = tk.Listbox(self, height= 25)
        self.selection.insert(0, *lst)
        self.selection.bind("<Double-Button-1>", self.on_selec_click)
        self.selection.grid(row=0, column=0)

        self.lbl_rt_factor = tk.Label(self)
        self.lbl_rt_factor["text"] = "Real-Time Factor"
        self.lbl_rt_factor.grid(row=1, column=0)

        self.input_rt_factor = tk.Entry(self, justify="center")
        self.input_rt_factor.insert(0, "120")
        self.input_rt_factor.grid(row=2, column=0)

        self.check_stats_selection = tk.IntVar()
        self.check_get_stats = tk.Checkbutton(self, variable=self.check_stats_selection)
        self.check_get_stats["text"] = "Output RTU sensor stats."
        self.check_get_stats.grid(row=3, column=0)

        self.check_times_selection = tk.IntVar()
        self.check_get_times = tk.Checkbutton(self, variable=self.check_times_selection)
        self.check_get_times["text"] = "Record the Mosaik event times."
        self.check_get_times.grid(row=4, column=0)
        
        img = Image.open(os.path.join(os.getcwd(), "..", "data", "img", "welcome.png"))
        photoimage = ImageTk.PhotoImage(img)
        self.image = tk.Label(self, width=500, height=500, image=photoimage)
        self.image.image = photoimage
        self.image.grid(row=0, column=1, columnspan=1, rowspan=1, padx=5, pady=5)

        self.lbl_topo_name = tk.Label(self, font="Helvetica 14")
        self.lbl_topo_name["text"] = ""
        self.lbl_topo_name.grid(row=1, column=1)

        self.btn_start = tk.Button(self)
        self.btn_start["text"] = "START SIMULATION"
        self.btn_start["command"] = self.start_sim
        self.btn_start.grid(row=3, column=1)

    def change_img(self, dir):
        """
        Changes the image based on selected topology.
        :param dir: name of topology directory
        """
        path = os.path.join(os.getcwd(), "..", "data", dir)
        for f in os.listdir(path):
            if ".png" in f:
                img = Image.open(os.path.join(path, f))
                phimg = ImageTk.PhotoImage(img)
                self.image = tk.Label(self, width=500, height=500, image=phimg)
                self.image.image = phimg
                self.image.grid(row=0, column=1, columnspan=1, rowspan=1, padx=5, pady=5)
                break

    def on_selec_click(self, event):
        """
        On-Click event for the selection.
        """
        widget = event.widget
        index = widget.curselection()
        if len(index) > 0:
            self.change_img(widget.get(index))
        self.selected_topo = self.selection.get(self.selection.curselection()[0])
        self.lbl_topo_name["text"] = self.selected_topo

    def start_sim(self):
        """
        Sends the hard reset command to the server.
        """
        self.set_sim_conf()
        self.loader.get_config(self.selected_topo)
        self.loader.start()

    def set_sim_conf(self):
        """
        Sets the simulation configuration of real-time factor and wheter to output the sensor data in the loader.
        """
        rt_factor = 1/int(self.input_rt_factor.get())
        # print(rt_factor)
        get_stats = self.check_stats_selection.get()
        if get_stats == 1:
            get_stats = True
        else:
            get_stats = False
        # print(get_stats)
        self.loader.set_sim_conf(str(rt_factor), str(get_stats))

if __name__ == "__main__":
    app = loader_gui(tk.Tk())
    app.mainloop()
    