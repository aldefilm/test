# /home/pi/aurion/aurion_master.py
import multiprocessing as mp
import aurion_left, aurion_right

def run_left(album_q):
    aurion_left.run_left_worker(album_q, greeting="Commander")

def run_right(album_q):
    aurion_right.run_right_worker(album_q, greeting="Commander")

if __name__ == "__main__":
    mp.set_start_method("spawn")  # safer on Pi/SDL

    album_q = mp.Queue()
    p_left  = mp.Process(target=run_left,  args=(album_q,))
    p_right = mp.Process(target=run_right, args=(album_q,))

    p_left.start()
    p_right.start()

    p_left.join()
    p_right.join()
