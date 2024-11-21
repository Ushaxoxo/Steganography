import os
from flask import Flask, render_template, request, send_file
from pdf2image import convert_from_path
from PIL import Image
from cryptography.fernet import Fernet

app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
RESULT_FOLDER = 'results'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(RESULT_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'pdf'}

# Generate a symmetric key
key = Fernet.generate_key()
cipher = Fernet(key)

def allowed_file(filename):
    """Check if the uploaded file has an allowed extension."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def convert_pdf_to_image(pdf_path, output_folder, output_filename="output.png"):
    """Convert the first page of a PDF to an image."""
    images = convert_from_path(pdf_path, dpi=300)  # Convert PDF to images
    image_path = os.path.join(output_folder, output_filename)
    images[0].save(image_path, 'PNG')  # Save the first page as PNG
    return image_path

def encrypt_image(image_path):
    """Encrypt the image using the symmetric key."""
    with open(image_path, 'rb') as f:
        image_data = f.read()
    encrypted_data = cipher.encrypt(image_data)
    return encrypted_data

def decrypt_image(encrypted_data, output_path):
    """Decrypt the image using the symmetric key."""
    decrypted_data = cipher.decrypt(encrypted_data)
    with open(output_path, 'wb') as f:
        f.write(decrypted_data)

def hide_image(cover_image_path, encrypted_data, output_path):
    """Embed encrypted data into the cover image."""
    cover_image = Image.open(cover_image_path).convert("RGB")
    binary_data = ''.join(format(byte, '08b') for byte in encrypted_data) + '1111111111111110'
    binary_index = 0

    pixels = cover_image.load()

    for y in range(cover_image.height):
        for x in range(cover_image.width):
            if binary_index >= len(binary_data):
                break
            r, g, b = pixels[x, y]
            r = (r & ~1) | int(binary_data[binary_index])
            binary_index += 1
            if binary_index < len(binary_data):
                g = (g & ~1) | int(binary_data[binary_index])
                binary_index += 1
            if binary_index < len(binary_data):
                b = (b & ~1) | int(binary_data[binary_index])
                binary_index += 1
            pixels[x, y] = (r, g, b)
        else:
            continue
        break

    cover_image.save(output_path)

def extract_image(stego_image_path):
    """Extract encrypted data from the stego image."""
    stego_image = Image.open(stego_image_path).convert("RGB")
    binary_data = ''
    pixels = stego_image.load()

    for y in range(stego_image.height):
        for x in range(stego_image.width):
            r, g, b = pixels[x, y]
            binary_data += str(r & 1)
            binary_data += str(g & 1)
            binary_data += str(b & 1)
            if binary_data.endswith('1111111111111110'):
                binary_data = binary_data[:-16]  # Remove the end marker
                break
        else:
            continue
        break

    encrypted_data = bytearray()
    for i in range(0, len(binary_data), 8):
        encrypted_data.append(int(binary_data[i:i + 8], 2))

    return bytes(encrypted_data)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/encrypt", methods=["POST"])
def encrypt():
    cover_image = request.files.get("cover_image")
    secret_image = request.files.get("secret_image")

    if not cover_image or not secret_image:
        return "Missing files. Please upload both cover and secret images.", 400

    if not allowed_file(cover_image.filename) or not allowed_file(secret_image.filename):
        return "Unsupported file type. Allowed types are PNG, JPG, JPEG, and PDF.", 400

    cover_image_path = os.path.join(app.config["UPLOAD_FOLDER"], cover_image.filename)
    cover_image.save(cover_image_path)

    secret_image_path = os.path.join(app.config["UPLOAD_FOLDER"], secret_image.filename)
    secret_image.save(secret_image_path)

    if cover_image.filename.endswith('.pdf'):
        cover_image_path = convert_pdf_to_image(cover_image_path, app.config["UPLOAD_FOLDER"], "converted_cover_image.png")
    if secret_image.filename.endswith('.pdf'):
        secret_image_path = convert_pdf_to_image(secret_image_path, app.config["UPLOAD_FOLDER"], "converted_secret_image.png")

    encrypted_data = encrypt_image(secret_image_path)

    output_path = os.path.join(RESULT_FOLDER, "stego_image.png")
    hide_image(cover_image_path, encrypted_data, output_path)

    return send_file(output_path, as_attachment=True, download_name="stego_image.png")

@app.route("/decrypt", methods=["POST"])
def decrypt():
    stego_image = request.files.get("stego_image")

    if not stego_image or not allowed_file(stego_image.filename):
        return "Unsupported file type. Allowed types are PNG, JPG, and JPEG.", 400

    stego_image_path = os.path.join(app.config["UPLOAD_FOLDER"], stego_image.filename)
    stego_image.save(stego_image_path)

    encrypted_data = extract_image(stego_image_path)

    output_path = os.path.join(RESULT_FOLDER, "extracted_secret_image.png")
    decrypt_image(encrypted_data, output_path)

    return send_file(output_path, as_attachment=True, download_name="extracted_secret_image.png")

if __name__ == "__main__":
    app.run(debug=True)
