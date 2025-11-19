#!/usr/bin/env python3

import sys
import argparse
from translate import TranslationPipeline
from export_to_excel import ExcelExporter
from import_from_excel import ExcelImporter


def print_banner():
    banner = """
    ╔═══════════════════════════════════════════════════════════╗
    ║           MTL Translation Tools v1.0                      ║
    ║     Japanese to English Translation Pipeline              ║
    ╚═══════════════════════════════════════════════════════════╝
    """
    print(banner)


def translate_workflow():
    print("\n[1/2] Starting translation...")
    print("=" * 60)

    pipeline = TranslationPipeline()
    pipeline.translate_folder()

    print("\n[2/2] Exporting to Excel for QC...")
    print("=" * 60)

    exporter = ExcelExporter()
    exporter.export_translated_files()

    print("\n✓ Translation workflow complete!")
    print("\nNext steps:")
    print("  1. Open the Excel file to review translations")
    print("  2. Add corrected translations to the 'QC' column")
    print("  3. Run: python main.py --import-qc")


def import_qc_workflow():
    print("\nImporting QC updates from Excel...")
    print("=" * 60)

    importer = ExcelImporter()
    importer.import_qc_updates()

    print("\n✓ QC import complete!")
    print("  Your translations have been updated with QC corrections.")


def show_menu():
    print_banner()

    print("\nWhat would you like to do?\n")
    print("  1. Translate JSON files (raw_umatl → slop)")
    print("  2. Export translated files to Excel for QC")
    print("  3. Import QC updates from Excel")
    print("  4. Full workflow (translate + export to Excel)")
    print("  5. Exit")

    choice = input("\nEnter your choice (1-5): ").strip()

    if choice == '1':
        print("\nStarting translation...")
        pipeline = TranslationPipeline()
        pipeline.translate_folder()

    elif choice == '2':
        print("\nExporting to Excel...")
        exporter = ExcelExporter()
        exporter.export_translated_files()

    elif choice == '3':
        import_qc_workflow()

    elif choice == '4':
        translate_workflow()

    elif choice == '5':
        print("\nGoodbye!")
        sys.exit(0)

    else:
        print("\nInvalid choice. Please try again.")
        show_menu()


def main():
    parser = argparse.ArgumentParser(
        description='MTL Translation Tools - Translate JSON files using LLM',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Interactive mode
  python main.py

  # Translate files
  python main.py --translate

  # Export to Excel
  python main.py --export

  # Import QC updates
  python main.py --import-qc

  # Full workflow
  python main.py --workflow
        """
    )

    parser.add_argument('--translate', '-t', action='store_true',
                        help='Translate JSON files from input to output folder')
    parser.add_argument('--export', '-e', action='store_true',
                        help='Export translated JSON files to Excel')
    parser.add_argument('--import-qc', '-i', action='store_true',
                        help='Import QC updates from Excel back to JSON')
    parser.add_argument('--workflow', '-w', action='store_true',
                        help='Run full workflow (translate + export)')

    args = parser.parse_args()

    if args.translate:
        print_banner()
        pipeline = TranslationPipeline()
        pipeline.translate_folder()

    elif args.export:
        print_banner()
        exporter = ExcelExporter()
        exporter.export_translated_files()

    elif args.import_qc:
        print_banner()
        import_qc_workflow()

    elif args.workflow:
        print_banner()
        translate_workflow()

    else:
        show_menu()


if __name__ == "__main__":
    main()
