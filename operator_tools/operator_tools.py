import threading
import os
from server import server

class operator_tools(threading.Thread):

    """
    Operator tools handle the data exchange between the GUI and the server.
    Also starts the simulation.
    """
    
    def __init__(self, gui):
        threading.Thread.__init__(self)
        self.gui = gui
        self.serv = None

    def run(self):
        """
        Runs the server thread and starts the simulation.
        """
        self.serv = server(self)
        self.serv.start()
        os.system("./startSimOp.sh")
    
    def hard_reset(self):
        """
        Executes the hard reset command in the server.
        """
        self.serv.hard_reset()

    def append_lbl_line(self, line):
        """
        Appends a line in the GUI label.
        :param line: line to append
        """
        self.gui.append_lbl_line(line)

if __name__ == "__main__":
    op = operator_tools()
    op.start()