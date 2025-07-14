let html5QrcodeScanner;

function startScanner() {
  html5QrcodeScanner = new Html5QrcodeScanner("reader", {
    fps: 10,
    qrbox: 250,
  });
  html5QrcodeScanner.render(onScanSuccess, () => {});
}

function onScanSuccess(decodedText) {
  html5QrcodeScanner.clear();
  document.getElementById(
    "result"
  ).innerText = `Scanned: ${decodedText}\nChecking...`;

  fetch("/api/check-visitor", {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify({ qr_code: decodedText }),
  })
    .then((res) => res.json())
    .then((data) => {
      const result = document.getElementById("result");
      const log = document.getElementById("log");

      if (!data.exists) {
        result.innerText = "❌ Visitor not found.";
      } else if (!data.enough_visits) {
        result.innerText = `❌ Only ${data.total_visits} visits. Require 10.`;
      } else {
        result.innerText = `✅ Visitor completed ${data.total_visits} visits.`;
        let table = `<h3>Visit Log</h3><table><tr><th>Team</th><th>Time</th></tr>`;
        data.visits.forEach((v) => {
          table += `<tr><td>${v.team_name}</td><td>${new Date(
            v.visit_time
          ).toLocaleString()}</td></tr>`;
        });
        table += `</table>`;
        log.innerHTML = table;
      }

      const btn = document.createElement("button");
      btn.textContent = "Scan Another";
      btn.onclick = () => location.reload();
      log.appendChild(document.createElement("br"));
      log.appendChild(btn);
    })
    .catch(() => {
      document.getElementById("result").innerText = "Error checking visitor.";
    });
}

window.onload = startScanner;
