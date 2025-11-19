# MTL Translation Tools

A comprehensive translation pipeline for Japanese visual novel/game JSON files using local LLM endpoints (OpenAI-compatible).

## Features

- **Automated Translation**: Translate entire folder structures of JSON files
- **Dictionary Preprocessing**: Replace specific Japanese terms before LLM translation
- **OpenAI-Compatible API**: Works with LM Studio, Ollama, or any OpenAI-compatible endpoint
- **Excel Export/Import**: Review and QC translations in Excel
- **Batch Processing**: Handle multiple files and subfolders automatically
- **Preserve Structure**: Maintains original folder hierarchy

## Installation

1. Install Python dependencies:
```bash
pip install -r requirements.txt
```

2. Configure your settings in `config.json`

## Quick Start

### Interactive Mode
```bash
python main.py
```

### Command Line Mode

Translate files:
```bash
python main.py --translate
```

Export to Excel:
```bash
python main.py --export
```

Import QC updates:
```bash
python main.py --import-qc
```

Full workflow:
```bash
python main.py --workflow
```

## Configuration

Edit `config.json` to customize your settings:

### LLM Settings
- `api_url`: Your local LLM endpoint (e.g., LM Studio at `http://localhost:1234/v1/chat/completions`)
- `api_key`: API key (use "lm-studio" for LM Studio)
- `model`: Model name
- `temperature`: Controls randomness (0.0-1.0)
- `system_prompt`: Instructions for the LLM

### Translation Settings
- `input_folder`: Source folder with Japanese JSON files (default: `raw_umatl`)
- `output_folder`: Destination for translated files (default: `slop`)
- `dictionary_file`: Path to dictionary JSON (default: `dictionary.json`)

## Workflow

### 1. Translation Phase

The tool will:
1. Scan `raw_umatl` for all JSON files
2. For each file:
   - Read `jpName` and `jpText` fields
   - Preprocess using `dictionary.json` (replaces known terms)
   - Send to LLM for translation
   - Write to `enName` and `enText` fields
3. Save translated files to `slop` folder

### 2. QC Phase

```bash
python main.py --export
```

This creates `translations.xlsx` with columns:
- **blockIdx**: Block identifier
- **jpName**: Original Japanese name
- **enName**: Translated name
- **jpText**: Original Japanese text
- **enText**: Machine translated text
- **QC**: Your corrected translation (edit this!)

### 3. Import QC Updates

After editing the Excel file:

```bash
python main.py --import-qc
```

The tool will:
- Read the QC column from Excel
- Update `enText` with QC values (if provided)
- Save updated JSON files back to `slop` folder

## Dictionary Format

`dictionary.json` should be a simple key-value mapping:

```json
{
  "マチカネタンホイザ": "Matikanetannhauser",
  "トレーナー": "Trainer",
  "ウマ娘": "Umamusume"
}
```

Terms in this dictionary will be replaced BEFORE sending to the LLM, ensuring consistent terminology.

## JSON Structure

The tool expects JSON files with this structure:

```json
{
  "text": [
    {
      "blockIdx": 1,
      "jpName": "Speaker name",
      "enName": "",
      "jpText": "Dialogue text",
      "enText": "",
      "choices": [
        {
          "jpText": "Choice text",
          "enText": ""
        }
      ]
    }
  ]
}
```

## Tips

1. **Test with one file first**: Move a single JSON to `raw_umatl` and test the workflow
2. **Review LM Studio output**: Make sure your model is loaded and responding
3. **Use dictionary liberally**: Add character names and technical terms to avoid inconsistencies
4. **Batch size**: Adjust in config if you hit rate limits
5. **QC in batches**: The Excel file can be split if it's too large

## Troubleshooting

### Connection Refused
- Make sure LM Studio (or your LLM server) is running
- Check the `api_url` in `config.json` matches your server

### Empty Translations
- Check LLM temperature and system prompt
- Verify dictionary replacements aren't causing issues
- Look at LM Studio console for errors

### Excel Import Not Working
- Make sure you're editing the QC column (column F)
- Don't rename sheets in the Excel file
- Keep the same file structure in `slop` folder

## File Structure

```
MTL-Tools/
├── main.py                 # Main entry point
├── translate.py            # Translation logic
├── export_to_excel.py      # Excel export
├── import_from_excel.py    # Excel import
├── config.json             # Configuration
├── dictionary.json         # Term replacements
├── requirements.txt        # Python dependencies
├── raw_umatl/             # Input folder
├── slop/                  # Output folder
└── translations.xlsx      # QC spreadsheet
```

## License

MIT License - Feel free to use and modify!
