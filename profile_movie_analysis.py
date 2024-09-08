import cProfile
import pstats
from main import main

if __name__ == "__main__":
    profiler = cProfile.Profile()
    profiler.enable()

    main()  # Run the main program

    profiler.disable()
    with open('profiling_results.txt', 'w') as f:
        stats = pstats.Stats(profiler, stream=f)
        stats.sort_stats('cumulative')  # Sort by cumulative time
        stats.print_stats()