# /home/pi/aurion/aurion_master.py
import multiprocessing
import aurion_left
import aurion_right

def run_left():
    aurion_left.run_idle_until_sd(greeting="Commander")

def run_right():
    aurion_right.run_idle_until_sd(greeting="Commander")

if __name__ == "__main__":
    # Run left + right as separate processes
    p_left = multiprocessing.Process(target=run_left)
    p_right = multiprocessing.Process(target=run_right)

    p_left.start()
    p_right.start()

    # Wait until they finish
    p_left.join()
    p_right.join()
