import time

32_bit = 2**32

###############################################################################################
# algorithm from Squirrel Eiserloh's 2017 GDC talk: Math for Game Programmers: Noise-Based RNG
# squirrel3 noise constants
NOISE1 = 0xb5297a4d
NOISE2 = 0x68e31da4
NOISE3 = 0x1b56c4e9

def timeseed():
    return time.time() % 32_bit

# might not get same results when not reducing to 32-bit int at each step
# something to check I guess, should make one that does and compare some outputs for big inputs (just generate some)
def squirrel3_seeded_hash(n, seed):
    n *= NOISE1
    n += seed
    n ^= n >> 8
    n += NOISE2
    n ^= n << 8
    n *= NOISE3
    n ^= n >> 8

    # squirrel3 is a 32 bit algorithm
    # this gets the right result but isn't the fastest, should be more than fast enough for me
    return n % 32_bit
###############################################################################################

# these noise funcitons take an integer position
def get_seeded_noise(position, seed):
    return squirrel3_seeded_hash(position, seed)

def get_2d_seeded_noise(x, y, seed):
    # multiply y by large prime with interesting bit pattern, then add to x
    # pretty good and fast result to map 1d noise to 2d
    # y_prime = 198491317
    return get_seeded_noise((y * 198491317) + x, seed)

# TODO:
#   class for sequential random number fetching
#   function for 32-bit int -> int in range a..b
#   funciton for weighted choice from list
#   multiple choices from list
