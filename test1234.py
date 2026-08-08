import sys, os
out_path = r"C:\Users\Aloosh2020\test_output_123.txt"
with open(out_path, 'w') as f:
    f.write("Exec: " + sys.executable + "\n")
    f.write("CWD: " + os.getcwd() + "\n")
