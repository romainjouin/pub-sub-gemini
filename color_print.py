
HEADER = '\033[95m'
OKBLUE = '\033[94m'
OKGREEN = '\033[92m'
WARNING = '\033[93m'
FAIL = '\033[91m'
ENDC = '\033[0m'
BOLD = "\033[1m"

def info(msg):
    print(OKBLUE + msg + ENDC)

def warn(msg):
    print(WARNING + msg + ENDC)

def error(msg):
    print(FAIL + msg + ENDC)
