import cmd, sys

class hacker(cmd.Cmd):
    """
    CMD providing I/O for the hacker tools.
    """
    intro="bla"
    prompt="sialala"


    def do_setswitch(self, args):
        "Sets switch on given branch to given value."
        params = args.split()
        print(params)


    

if __name__ == "__main__":
    hacker().cmdloop()