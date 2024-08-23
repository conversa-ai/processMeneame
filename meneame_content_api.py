import requests
import json
import os
import pandas as pd
import argparse

LINK = 'https://www.meneame.net/api/list.php?id='
output_file = 'output.json'
corpus_folder = 'corpus'
content_folder = 'content'

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
        }

def get_meneame_links_pandas(output_file):
    meneame_links = []
    with open(output_file, 'r') as f:
        for line in f:
            meneame_links.append(json.loads(line))
    return pd.DataFrame(meneame_links, columns=['article_id', 'article_link'])

def get_meneame_comments(meneame_links):

    existing_ids = [file.split('.')[0] for file in os.listdir(corpus_folder)]

    for i, row in meneame_links.iterrows():
        if row['article_id'] in existing_ids:
            print('Article ' + row['article_id'] + ' already exists. Skipping...')
            continue

        article_api_link = 'https://www.meneame.net/api/list.php?id=' + row['article_id']

        print('Getting comments for article ' + row['article_id'] + '...')
        print('Link: ' + row['article_link'])

        try:
            response = requests.get(article_api_link, headers=headers)
            data = response.json()
        except requests.exceptions.RequestException as e:
            print(f'Request failed with error: {e}')
            continue
        except json.JSONDecodeError:
            print('JSONDecodeError')
            continue

        with open(os.path.join(corpus_folder, row['article_id'] + '.json'), 'w') as f:
            json.dump(data, f)

def get_meneame_content(meneame_files):
    processed_files = os.listdir(content_folder)
    for file in meneame_files:
        if file.endswith('json'):
            if file in processed_files:
                print('File ' + file + ' already exists. Skipping...')
                continue
            article_id = file.split('.')[0]
            link = f'https://www.meneame.net/backend/info.php?&what=link&id={article_id}&fields=content,title'
            print('Getting content for article', article_id, '...')
            try:
                response = requests.get(link, headers=headers)
                data = response.json()
            except requests.exceptions.RequestException as e:
                print(f'Request failed with error: {e}')
                continue
            except json.JSONDecodeError:
                print('JSONDecodeError')
                continue

            with open(os.path.join(content_folder, article_id + '.json'), 'w') as f:
                json.dump(data, f)

def write_comments_to_file(comments, comment_file):
    with open(comment_file, 'w') as f:
        for comment in comments:
            json.dump(comment, f, separators=(',', ':'))
            f.write('\n')


if __name__ == '__main__':
    # meneame_links = get_meneame_links_pandas(output_file)
    # get_meneame_comments(meneame_links)
    os.makedirs(content_folder, exist_ok=True)
    meneame_files = os.listdir(corpus_folder)
    get_meneame_content(meneame_files)
