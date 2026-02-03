# Menéame forum rehydration (esCorpiusDialog)

This repository provides a **rehydration** utility for the **dehydrated (IDs-only)** Menéame subset distributed with esCorpiusDialog.

- **Input**: dehydrated JSON files containing dialogue chains as ordered lists of **turn IDs**.
- **Fetch**: Menéame public API endpoint:
  https://www.meneame.net/api/list.php?id=<article_id>
- **Output**: a **local rehydrated JSON** that contains user-generated text (**NOT FOR REDISTRIBUTION**).

## Important note about IDs (critical)
The turn IDs in our dehydrated dialogue chains correspond to `objects[*].order` returned by the Menéame API (**NOT** `objects[*].id`).

## Requirements
- Python 3
- `requests` (`pip install requests`)

## Usage

### Minimal command
```bash
python3 rehydrate_meneame.py \
  --input data/meneame_dehydrated/123456.json \
  --output data/meneame_rehydrated/123456.rehydrated.json \
  --user-agent "esCorpiusDialog-rehydrator/1.0 (contact: <email>)" \
  --replace-mentions \
  --timeout 30 \
  --retries 3 \
  --sleep 1 \
  --debug
```
