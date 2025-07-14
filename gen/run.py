import csv
import os
import sys
import qrcode


def generate_qr_images_from_csv(csv_filepath, output_dir='qr_images'):
    """
    Read CSV of QR codes and generate PNG images for each code.

    Args:
        csv_filepath (str): Path to the CSV file with at least 'qr_code' column.
        output_dir (str): Directory to save generated PNG images.

    Returns:
        None
    """
    if not os.path.exists(csv_filepath):
        print(f"Error: CSV file '{csv_filepath}' does not exist.")
        return

    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)

    with open(csv_filepath, newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        if 'qr_code' not in reader.fieldnames:
            print("Error: CSV file must have 'qr_code' column.")
            return

        for row in reader:
            qr_code_text = row['qr_code']
            if not qr_code_text:
                print("Skipping row with empty qr_code.")
                continue

            # Generate QR code image
            qr = qrcode.QRCode(
                version=1,
                box_size=10,
                border=4
            )
            qr.add_data(qr_code_text)
            qr.make(fit=True)
            img = qr.make_image(fill_color="black", back_color="white")

            # Save image as PNG
            filename = f"{qr_code_text}.png"
            filepath = os.path.join(output_dir, filename)
            img.save(filepath)

            print(f"Generated QR code image: {filepath}")


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print(
            "Usage: python generate_qr_images.py <csv_file_path> [output_dir]")
    else:
        csv_path = sys.argv[1]
        output_folder = sys.argv[2] if len(sys.argv) > 2 else 'qr_images'
        generate_qr_images_from_csv(csv_path, output_folder)
