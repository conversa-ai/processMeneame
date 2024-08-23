import json
import os

output_folder = './test_output'
output_verbose_folder = './test_output_verbose'

files = os.listdir(output_folder)

words = 0
comments = 0
dialogues = 0
posts = len(files)

for file in files:
    with open(os.path.join(output_folder, file), 'r') as f:
        data = json.load(f)
    with open(os.path.join(output_verbose_folder, file), 'r') as f:
        data_verbose = json.load(f)
    comments += len(data['comments'])
    for d in data_verbose:
        for comment in data_verbose[d]:
            words += len(comment.split())
    dialogues += len(data_verbose)

print('Posts:', posts)
print('Dialogues:', dialogues)
print('Comments:', comments)
print('Words:', words)