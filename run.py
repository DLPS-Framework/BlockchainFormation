import sys, os, argparse


class ArgParser:

    def __init__(self):
        """Initialize an ArgParser object.
        The general structure of calls from the command line is:
        """

        self.parser = argparse.ArgumentParser()



if __name__ == '__main__':
    argparser = ArgParser()
    namespace = argparser.parser.parse_args()


