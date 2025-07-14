let html5QrcodeScanner;

function startScanner() {
  html5QrcodeScanner = new Html5QrcodeScanner("reader", {
    fps: 10,
    qrbox: 250,
  });
  html5QrcodeScanner.render(onScanSuccess, onScanFailure);
}

function onScanSuccess(decodedText, decodedResult) {
  // Stop scanning once we get a result
  html5QrcodeScanner.clear();

  const resultDiv = document.getElementById("result");
  resultDiv.innerText = `Scanned: ${decodedText}\nChecking...`;

  fetch("/api/check-qr", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ qr_code: decodedText }),
  })
    .then((response) => response.json())
    .then((data) => {
      if (data.exists) {
        resultDiv.innerText = `QR Code exists in database. ✅`;
      } else {
        resultDiv.innerText = `QR Code NOT found in database. ❌`;
      }
      addRescanButton();
    })
    .catch(() => {
      resultDiv.innerText = "Error checking QR code.";
      addRescanButton();
    });
}

function addRescanButton() {
  const resultDiv = document.getElementById("result");

  // Avoid adding multiple buttons
  if (document.getElementById("rescan-btn")) return;

  const btn = document.createElement("button");
  btn.id = "rescan-btn";
  btn.textContent = "Scan Again";
  btn.style.marginTop = "15px";
  btn.onclick = () => {
    btn.remove();
    resultDiv.innerText = "";
    startScanner();
  };

  resultDiv.appendChild(document.createElement("br"));
  resultDiv.appendChild(btn);
}

function onScanFailure(error) {
  // optional: log errors here
}

// Initialize scanner on page load
window.onload = () => {
  startScanner();
};
