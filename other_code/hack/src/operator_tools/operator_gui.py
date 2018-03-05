import tkinter as tk
from operator_tools import operator_tools

class operator_gui(tk.Frame):

    """
    GUI for the operator to hard reset the RTUs.
    """

    def __init__(self, master):
        super().__init__(master)
        master.title("Operator RTU Control Center")
        self.pack()
        self.welcome_string = "Operator RTU Control Center"
        self.create_widgets()
        self.op = operator_tools(self)
        self.op.start()

    def create_widgets(self):
        """
        Creates the GUI.
        """
        self.lbl_welcome = tk.Label(self, font="Helvetica 20 bold")
        self.lbl_welcome["text"] = self.welcome_string
        self.lbl_welcome.pack()

        self.lbl_notification = tk.Label(self, fg="red", font="Helvetica 16 bold")
        self.lbl_notification["text"] = ""
        self.lbl_notification.pack()

        self.btn_reset = tk.Button(self)
        self.btn_reset["text"] = "HARD RESET"
        self.btn_reset["command"] = self.hard_reset
        self.btn_reset.pack(side="bottom")

    def hard_reset(self):
        """
        Sends the hard reset command to the server.
        """
        self.set_lbl_txt("")
        print("HARD RESETTING RTUS!")
        self.op.hard_reset()

    def set_lbl_txt(self, txt):
        """
        Sets the text in the GUI label.
        :param txt: text to display
        """
        self.lbl_notification["text"] = txt

    def append_lbl_line(self, line):
        """
        Appends a line to the GUI label if the line is not already present.
        :param line: line to append
        """
        if line not in self.lbl_notification["text"]:
            if len(self.lbl_notification["text"]) != 0:
                self.lbl_notification["text"] += "\n"
            self.lbl_notification["text"] += line

if __name__ == "__main__":
    app = operator_gui(tk.Tk())
    app.mainloop()
    