let html5QrcodeScanner;

function startScanner() {
  html5QrcodeScanner = new Html5QrcodeScanner("reader", {
    fps: 10,
    qrbox: 250,
  });
  html5QrcodeScanner.render(onScanSuccess, onScanFailure);
}

function onScanSuccess(decodedText, decodedResult) {
  html5QrcodeScanner.clear();

  const resultDiv = document.getElementById("result");
  resultDiv.innerText = `Scanned: ${decodedText}\nChecking...`;

  // Prepare payload
  const payload = {
    qr_code: decodedText,
    team_id: typeof TEAM_ID !== "undefined" ? TEAM_ID : null,
  };

  fetch("/api/check-qr", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  })
    .then((response) => response.json())
    .then((data) => {
      if (data.exists) {
        resultDiv.innerText = `QR Code Accepted ✅.\nThank You for Joining with Us!`;
      } else {
        resultDiv.innerText = `Invalid QR Code. ❌`;
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
  // Optional: log scan errors
}

window.onload = () => {
  startScanner();
};
