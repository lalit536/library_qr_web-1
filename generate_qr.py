import qrcode
import os

# Ensure folder exists
os.makedirs("static/qrcodes", exist_ok=True)

# Example QR for book_1
data = "book_1"
img = qrcode.make(data)
img.save("static/qrcodes/book_1.png")

print("QR code saved at static/qrcodes/book_1.png")
