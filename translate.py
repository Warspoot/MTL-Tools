import json
import os
import sys
import time
import requests
from pathlib import Path
from typing import Dict, List, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib


class TranslationPipeline:
    def __init__(self, config_path: str = "config.toml"):
        with open(config_path, 'rb') as f:
            self.config = tomllib.load(f)

        self.llm_config = self.config['llm_settings']
        self.trans_config = self.config['translation_settings']

        self.dictionary = {}
        if self.trans_config['use_dictionary']:
            dict_file = self.trans_config['dictionary_file']
            if os.path.exists(dict_file):
                with open(dict_file, 'r', encoding='utf-8') as f:
                    self.dictionary = json.load(f)
                print(f"Loaded {len(self.dictionary)} dictionary entries")

        self.context_lines = self.trans_config.get('context_lines', 0)
        self.current_context: List[Dict[str, str]] = []

    def preprocess_text(self, text: str) -> str:
        preprocessed = text
        for jp_term, en_term in self.dictionary.items():
            preprocessed = preprocessed.replace(jp_term, en_term)
        return preprocessed

    def contains_japanese(self, text: str) -> bool:
        if not text:
            return False

        for char in text:
            code = ord(char)
            if (0x3040 <= code <= 0x309F or
                0x30A0 <= code <= 0x30FF or
                0x4E00 <= code <= 0x9FFF):
                return True

        return False

    def add_to_context(self, jp_name: str, jp_text: str, en_name: str = "", en_text: str = ""):
        if self.context_lines > 0:
            self.current_context.append({
                'jpName': jp_name,
                'jpText': jp_text,
                'enName': en_name,
                'enText': en_text
            })
            if len(self.current_context) > self.context_lines:
                self.current_context.pop(0)

    def build_context_string(self) -> str:
        if not self.current_context:
            return ""

        context_parts = []
        for ctx in self.current_context:
            if ctx['enText']:
                context_parts.append(f"{ctx['jpName']}: {ctx['jpText']}\n[Translation]: {ctx['enName']}: {ctx['enText']}")
            else:
                context_parts.append(f"{ctx['jpName']}: {ctx['jpText']}")

        return "\n\nPrevious dialogue for context:\n" + "\n".join(context_parts) + "\n\nNow translate:"

    def call_llm(self, text: str, context: str = "", retry_count: int = 0) -> Optional[str]:
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.llm_config['api_key']}"
        }

        user_message = context + "\n" + text if context else text

        payload = {
            "model": self.llm_config['model'],
            "messages": [
                {
                    "role": "system",
                    "content": self.llm_config['system_prompt']
                },
                {
                    "role": "user",
                    "content": f"Translate this to English: {user_message}"
                }
            ],
            "temperature": self.llm_config['temperature'],
            "max_tokens": self.llm_config['max_tokens'],
            "min_p": self.llm_config.get('min_p', 0.05)
        }

        optional_params = {
            "top_p": self.llm_config.get('top_p'),
            "top_k": self.llm_config.get('top_k')
        }
        for param, value in optional_params.items():
            if value is not None:
                payload[param] = value

        if retry_count == 0 and not hasattr(self, '_debug_shown'):
            print(f"    [DEBUG] Requesting model: {self.llm_config['model']}")
            self._debug_shown = True

        try:
            response = requests.post(
                self.llm_config['api_url'],
                headers=headers,
                json=payload,
                timeout=60
            )
            response.raise_for_status()

            result = response.json()

            if not hasattr(self, '_actual_model_shown'):
                if 'model' in result:
                    print(f"    [DEBUG] LM Studio using: {result['model']}")
                self._actual_model_shown = True

            translated = result['choices'][0]['message']['content'].strip()
            return translated

        except Exception as e:
            print(f"Error calling LLM: {e}")
            if retry_count < self.trans_config['retry_attempts']:
                print(f"Retrying... (attempt {retry_count + 1}/{self.trans_config['retry_attempts']})")
                time.sleep(self.trans_config['retry_delay'])
                return self.call_llm(text, context, retry_count + 1)
            return None

    def translate_text(self, text: str, is_name: bool = False, use_context: bool = True, retry_count: int = 0) -> str:
        preprocessed = self.preprocess_text(text)

        context = ""
        if use_context and not is_name and self.context_lines > 0:
            context = self.build_context_string()

        if is_name and preprocessed != text:
            return preprocessed

        translated = self.call_llm(preprocessed, context)
        if not translated:
            return preprocessed

        retry_on_japanese = self.trans_config.get('retry_on_japanese', True)
        max_retries = self.trans_config.get('retry_attempts', 3)

        if retry_on_japanese and retry_count < max_retries:
            if self.contains_japanese(translated):
                print(f"      [WARNING] Translation contains Japanese: {translated[:50]}...")
                print(f"      [RETRY] Retranslating (attempt {retry_count + 1}/{max_retries})...")
                time.sleep(self.trans_config.get('retry_delay', 2))
                return self.translate_text(text, is_name, use_context, retry_count + 1)

        return translated

    def translate_batch(self, texts: List[str], use_context: bool = True, retry_count: int = 0) -> List[str]:
        if not texts:
            return []

        preprocessed = [self.preprocess_text(text) for text in texts]

        context = ""
        if use_context and self.context_lines > 0:
            context = self.build_context_string() + "\n\n"

        batch_text = context + "Translate each line below:\n\n"
        for idx, text in enumerate(preprocessed, 1):
            batch_text += f"{idx}. {text}\n"

        batch_text += "\nProvide translations in the same numbered format, one per line."

        result = self.call_llm(batch_text, "")
        if not result:
            return preprocessed

        translations = []
        lines = result.strip().split('\n')

        for line in lines:
            line = line.strip()
            if not line:
                continue

            import re
            match = re.match(r'^\d+[\.\)\:]\s*(.+)$', line)
            if match:
                translations.append(match.group(1))
            else:
                translations.append(line)

        while len(translations) < len(texts):
            translations.append(preprocessed[len(translations)])

        translations = translations[:len(texts)]

        retry_on_japanese = self.trans_config.get('retry_on_japanese', True)
        max_retries = self.trans_config.get('retry_attempts', 3)

        if retry_on_japanese and retry_count < max_retries:
            has_japanese = False
            for idx, translation in enumerate(translations):
                if self.contains_japanese(translation):
                    has_japanese = True
                    print(f"      [WARNING] Translation {idx+1} contains Japanese: {translation[:50]}...")
                    break

            if has_japanese:
                print(f"      [RETRY] Retranslating batch (attempt {retry_count + 1}/{max_retries})...")
                time.sleep(self.trans_config.get('retry_delay', 2))
                return self.translate_batch(texts, use_context, retry_count + 1)

        return translations

    def reset_context(self):
        self.current_context = []

    def translate_json_file(self, input_path: str, output_path: str):
        print(f"\nProcessing: {input_path}")
        file_start_time = time.time()

        with open(input_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        self.reset_context()

        total_blocks = len(data.get('text', []))
        translated_count = 0
        use_batch = self.trans_config.get('use_batch_translation', True)
        batch_size = self.trans_config.get('batch_size', 10)

        if use_batch:
            print(f"  Using batch translation (batch_size={batch_size})")
            translated_count = self._translate_json_batched(data, total_blocks)
        else:
            print(f"  Using sequential translation")
            translated_count = self._translate_json_sequential(data, total_blocks)

        self._clean_monologue_names(data)

        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)

        file_elapsed = time.time() - file_start_time
        print(f"  Translated {translated_count} items")
        print(f"  Saved to: {output_path}")
        print(f"  ⏱ Time: {file_elapsed:.2f}s ({file_elapsed/60:.2f}m)")

    def _translate_json_sequential(self, data: Dict, total_blocks: int) -> int:
        translated_count = 0

        for idx, block in enumerate(data.get('text', []), 1):
            print(f"  Block {idx}/{total_blocks} (blockIdx: {block.get('blockIdx', '?')})")

            jp_name = block.get('jpName', '')
            jp_text = block.get('jpText', '')
            en_name = block.get('enName', '')
            en_text = block.get('enText', '')

            if en_name == '' and jp_name:
                print(f"    Translating name: {jp_name}")
                en_name = self.translate_text(jp_name, is_name=True, use_context=False)
                block['enName'] = en_name
                print(f"    -> {en_name}")
                translated_count += 1
                time.sleep(0.5)

            if en_text == '' and jp_text:
                print(f"    Translating text: {jp_text[:50]}...")
                en_text = self.translate_text(jp_text, is_name=False, use_context=True)
                block['enText'] = en_text
                print(f"    -> {en_text[:50]}...")
                translated_count += 1
                time.sleep(0.5)

            self.add_to_context(jp_name, jp_text, en_name, en_text)

            if 'choices' in block and block['choices']:
                for choice_idx, choice in enumerate(block['choices']):
                    if choice.get('enText', '') == '' and choice.get('jpText'):
                        jp_choice = choice['jpText']
                        print(f"    Translating choice {choice_idx + 1}: {jp_choice}")
                        en_choice = self.translate_text(jp_choice, is_name=False, use_context=True)
                        choice['enText'] = en_choice
                        print(f"    -> {en_choice}")
                        translated_count += 1
                        time.sleep(0.5)

        return translated_count

    def _translate_json_batched(self, data: Dict, total_blocks: int) -> int:
        translated_count = 0
        batch_size = self.trans_config.get('batch_size', 25)
        blocks = data.get('text', [])

        name_items = []
        text_items = []
        choice_items = []

        for idx, block in enumerate(blocks):
            jp_name = block.get('jpName', '')
            jp_text = block.get('jpText', '')
            en_name = block.get('enName', '')
            en_text = block.get('enText', '')

            if en_name == '' and jp_name and jp_name.strip():
                name_items.append(('name', block, jp_name, idx))

            if en_text == '' and jp_text:
                text_items.append(('text', block, jp_text, idx))

            if 'choices' in block and block['choices']:
                for choice in block['choices']:
                    if choice.get('enText', '') == '' and choice.get('jpText'):
                        choice_items.append(('choice', choice, choice['jpText'], idx))

        all_items = name_items + text_items + choice_items

        if not all_items:
            return 0

        print(f"  Collected {len(all_items)} items to translate")

        num_batches = (len(all_items) + batch_size - 1) // batch_size
        batch_delay = self.trans_config.get('batch_delay', 0)
        failed_items = []

        for batch_num in range(num_batches):
            start_idx = batch_num * batch_size
            end_idx = min(start_idx + batch_size, len(all_items))
            batch_items = all_items[start_idx:end_idx]

            print(f"  Batch {batch_num + 1}/{num_batches}: Translating items {start_idx + 1}-{end_idx}")

            batch_texts = [item[2] for item in batch_items]

            translations = self.translate_batch(batch_texts, use_context=False)

            for item, translation in zip(batch_items, translations):
                item_type, obj, original_text, block_idx = item

                if item_type == 'name':
                    obj['enName'] = translation
                    print(f"    [{block_idx}] Name: {translation[:40]}")
                elif item_type == 'text':
                    obj['enText'] = translation
                    print(f"    [{block_idx}] Text: {translation[:60]}...")
                elif item_type == 'choice':
                    obj['enText'] = translation

                if self.contains_japanese(translation):
                    failed_items.append((item, translation))

                translated_count += 1

            if batch_delay > 0 and batch_num < num_batches - 1:
                time.sleep(batch_delay)

        if failed_items and self.trans_config.get('enable_two_pass', False):
            translated_count += self._second_pass_translation(failed_items)

        return translated_count

    def _clean_monologue_names(self, data: Dict) -> int:
        cleaned_names = 0
        cleaned_texts = 0

        for block in data.get('text', []):
            en_name = block.get('enName', '')
            jp_text = block.get('jpText', '')
            en_text = block.get('enText', '')

            if en_name.lower() == 'monologue':
                block['enName'] = ''
                cleaned_names += 1

            if (not jp_text or not jp_text.strip()) and en_text.lower() == 'monologue':
                block['enText'] = ''
                cleaned_texts += 1

        if cleaned_names > 0 or cleaned_texts > 0:
            print(f"  [POST-PROCESS] Cleaned {cleaned_names} 'Monologue' from enName, {cleaned_texts} from enText")

        return cleaned_names + cleaned_texts

    def _second_pass_translation(self, failed_items: List) -> int:
        if not failed_items:
            return 0

        print(f"\n  === SECOND PASS ===")
        print(f"  Found {len(failed_items)} items with Japanese - retranslating with second model")

        original_model = self.llm_config['model']
        original_temp = self.llm_config['temperature']

        second_model = self.trans_config.get('second_pass_model', original_model)
        second_temp = self.trans_config.get('second_pass_temperature', 0.3)

        if second_model == original_model:
            print(f"  WARNING: Second pass model is same as primary model")
            print(f"  Tip: Set second_pass_model to a different/stronger model in config.toml")
            print(f"  Skipping second pass (would produce same results)\n")
            return 0

        self.llm_config['model'] = second_model
        self.llm_config['temperature'] = second_temp
        print(f"  Using model: {second_model} (temp={second_temp})")
        print(f"  NOTE: Make sure this model is loaded in LM Studio!")

        if hasattr(self, '_debug_shown'):
            delattr(self, '_debug_shown')
        if hasattr(self, '_actual_model_shown'):
            delattr(self, '_actual_model_shown')

        retranslated_count = 0
        batch_size = self.trans_config.get('batch_size', 25)
        model_not_loaded = False

        for i in range(0, len(failed_items), batch_size):
            batch = failed_items[i:i + batch_size]
            print(f"  Second pass batch: {i + 1}-{min(i + batch_size, len(failed_items))}")

            batch_texts = [item[0][2] for item in batch]

            try:
                translations = self.translate_batch(batch_texts, use_context=False)
            except Exception as e:
                print(f"    ✗ Second pass failed: {e}")
                print(f"    ✗ Model '{second_model}' may not be loaded in LM Studio")
                model_not_loaded = True
                break

            if not translations or all(not t for t in translations):
                print(f"    ✗ Second pass returned empty results")
                print(f"    ✗ Model '{second_model}' is not loaded in LM Studio")
                model_not_loaded = True
                break

            for (item, old_translation), new_translation in zip(batch, translations):
                item_type, obj, _, block_idx = item

                if not new_translation:
                    print(f"    ✗ [{block_idx}] Translation failed, keeping original")
                    continue

                if not self.contains_japanese(new_translation):
                    if item_type == 'name':
                        obj['enName'] = new_translation
                        print(f"    ✓ [{block_idx}] Name fixed: {new_translation[:40]}")
                    elif item_type == 'text':
                        obj['enText'] = new_translation
                        print(f"    ✓ [{block_idx}] Text fixed: {new_translation[:60]}...")
                    elif item_type == 'choice':
                        obj['enText'] = new_translation
                    retranslated_count += 1
                else:
                    print(f"    ✗ [{block_idx}] Still contains Japanese, keeping best attempt")

        self.llm_config['model'] = original_model
        self.llm_config['temperature'] = original_temp

        if model_not_loaded:
            print(f"\n  ⚠ Second pass incomplete: Model not available")
            print(f"  To use two-pass translation:")
            print(f"    1. Load '{second_model}' in LM Studio")
            print(f"    2. Or set second_pass_model to a loaded model")
            print(f"    3. Or disable two-pass: enable_two_pass = false\n")
        else:
            print(f"  Second pass complete: {retranslated_count}/{len(failed_items)} items fixed\n")

        return retranslated_count

    def translate_folder(self):
        workflow_start_time = time.time()

        input_folder = Path(self.trans_config['input_folder'])
        output_folder = Path(self.trans_config['output_folder'])

        if not input_folder.exists():
            print(f"Error: Input folder '{input_folder}' does not exist")
            return

        json_files = list(input_folder.rglob('*.json'))

        if not json_files:
            print(f"No JSON files found in '{input_folder}'")
            return

        print(f"Found {len(json_files)} JSON files to translate")
        if self.context_lines > 0:
            print(f"Using {self.context_lines} previous lines as context")

        concurrent_files = self.trans_config.get('concurrent_files', 1)

        if concurrent_files > 1 and len(json_files) > 1:
            print(f"Processing {concurrent_files} files concurrently")
            self._translate_folder_concurrent(json_files, input_folder, output_folder, concurrent_files)
        else:
            self._translate_folder_sequential(json_files, input_folder, output_folder)

        workflow_elapsed = time.time() - workflow_start_time
        print(f"\n✓ Translation complete! Output saved to '{output_folder}'")
        print(f"⏱ Total workflow time: {workflow_elapsed:.2f}s ({workflow_elapsed/60:.2f}m)")
        if len(json_files) > 0:
            print(f"   Average per file: {workflow_elapsed/len(json_files):.2f}s")

    def _translate_folder_sequential(self, json_files, input_folder, output_folder):
        for json_file in json_files:
            relative_path = json_file.relative_to(input_folder)
            output_path = output_folder / relative_path

            try:
                self.translate_json_file(str(json_file), str(output_path))
            except Exception as e:
                print(f"Error processing {json_file}: {e}")

    def _translate_folder_concurrent(self, json_files, input_folder, output_folder, max_workers):
        def process_file(json_file):
            relative_path = json_file.relative_to(input_folder)
            output_path = output_folder / relative_path

            try:
                pipeline = TranslationPipeline(self.trans_config.get('config_path', 'config.toml'))
                pipeline.translate_json_file(str(json_file), str(output_path))
                return (json_file, True, None)
            except Exception as e:
                return (json_file, False, str(e))

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(process_file, json_file): json_file for json_file in json_files}

            for future in as_completed(futures):
                json_file, success, error = future.result()
                if not success:
                    print(f"Error processing {json_file}: {error}")


def main():
    pipeline = TranslationPipeline()
    pipeline.translate_folder()


if __name__ == "__main__":
    main()
