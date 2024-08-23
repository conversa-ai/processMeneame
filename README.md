```
scrapy crawl meneame_spyder -o output.json
python3 meneame_api.py --input_file output.json
python3 meneame_content_api.py
python clean_comments.py --input_comment_folder corpus --output_folder output_final --output_folder_verbose output_final_verbose
```
