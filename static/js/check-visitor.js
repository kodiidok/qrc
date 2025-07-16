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
    "final-result"
  ).innerText = `Scanned: ${decodedText}\nChecking...`;

  fetch("/api/check-visitor", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ qr_code: decodedText }),
  })
    .then((res) => res.json())
    .then((data) => {
      const resultWrapper = document.getElementById("final-result");
      const log = document.getElementById("log");

      resultWrapper.innerHTML = ""; // Clear previous content
      log.innerHTML = ""; // Clear previous log

      // Create box that will be styled
      const resultBox = document.createElement("div");
      resultBox.classList.add("result-message");

      const gif = document.createElement("img");
      gif.classList.add("result-gif");

      const message = document.createElement("div");

      const gifSets = {
        success: [
          "/static/images/gifs/success/1.gif",
          "/static/images/gifs/success/2.gif",
          "/static/images/gifs/success/3.gif",
        ],
        encourage: [
          "/static/images/gifs/encourage/1.gif",
          "/static/images/gifs/encourage/2.gif",
          "/static/images/gifs/encourage/3.gif",
        ],
        notfound: [
          "/static/images/gifs/notfound/1.gif",
          "/static/images/gifs/notfound/2.gif",
          "/static/images/gifs/notfound/3.gif",
        ],
      };

      const pickRandom = (arr) => arr[Math.floor(Math.random() * arr.length)];

      if (!data.exists) {
        resultBox.classList.add("error");
        gif.src = pickRandom(gifSets.notfound);
        message.innerText = "❌ You have not visited any team presentations!";
      } else if (!data.enough_visits) {
        resultBox.classList.add("warning");
        gif.src = pickRandom(gifSets.encourage);
        message.innerText = `❌ Only ${data.total_visits} visits.\nPlease complete all 13.`;
      } else {
        resultBox.classList.add("success");
        gif.src = pickRandom(gifSets.success);
        message.innerText = `✅ Congratulations! You completed all ${data.total_visits} visits.`;

        let table = `<h3>Visit Log</h3><table><tr><th>Team</th><th>Time</th></tr>`;
        data.visits.forEach((v) => {
          table += `<tr><td>${v.team_name}</td><td>${new Date(
            v.visit_time
          ).toLocaleString()}</td></tr>`;
        });
        table += `</table>`;
        log.innerHTML = table;
      }

      resultBox.appendChild(gif);
      resultBox.appendChild(message);
      resultWrapper.appendChild(resultBox);

      const btn = document.createElement("button");
      btn.textContent = "Scan Another";
      btn.onclick = () => location.reload();
      log.appendChild(document.createElement("br"));
      log.appendChild(btn);
    })

    .catch(() => {
      document.getElementById("final-result").innerText = "Error checking visitor.";
    });
}

window.onload = startScanner;
