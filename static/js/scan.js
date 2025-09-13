console.log("QR Scanner ready");
// Later you can use html5-qrcode library here
// Example QR scanner logic
function onScanSuccess(decodedText, decodedResult) {
    console.log(`Scan result: ${decodedText}`);

    // Assuming QR contains just the BOOK ID
    // Redirect student directly to book details page
    window.location.href = "/book/" + decodedText;
}

// Initialize QR scanner
var html5QrcodeScanner = new Html5QrcodeScanner(
    "reader", { fps: 10, qrbox: 250 });
html5QrcodeScanner.render(onScanSuccess);
