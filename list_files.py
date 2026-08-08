import os
with open('out.txt', 'w') as f:
    f.write('\n'.join(os.listdir('.')))
